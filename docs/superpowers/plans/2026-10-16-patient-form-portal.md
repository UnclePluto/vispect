# 患者扫码填写与医生修订实施计划

> **面向执行代理：** 必须使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 逐任务实施本计划；按用户选择保留执行方式。步骤用复选框跟踪，先观察新增行为测试失败，再实现并验证。开始实施前使用 `superpowers:using-git-worktrees` 检查隔离工作区。

**目标：** 提供患者手机号登录、首次改密、研究访视表单共用二维码、响应式填写，以及保留原始提交信息的医生修订。

**架构：** 新增独立 `patient_portal` 模块、患者 Cookie 和前端认证边界，复用现有表单解释器及 `Answer`／`AnswerRevision`。患者身份按机构和手机号唯一，通过明确档案绑定获得任务权限；工作人员接口继续使用现有 Account 和机构切换机制。

**技术栈：** Django 5.2／DRF、PostgreSQL 17、React 19／TypeScript、Ant Design 6、TanStack Query、pytest、Vitest、Playwright。

**设计依据：** `docs/superpowers/specs/2026-10-16-patient-form-portal-design.md`（用户已于 2026-10-16 确认）。

## 全局约束

- 所有文件路径相对于 `/Users/nick/my_dev/workout/Vispect`；开始前读取适用的 AGENTS.md，所有沟通、操作说明及提交说明使用简体中文。
- 新患者账号默认密码为 `888888`，首次改密前不能获取临床数据；正常新密码沿用不少于 12 位、常见密码及纯数字校验。
- 同一机构与规范化手机号唯一；患者认证独立于工作人员。已有患者不按联系方式自动开通；已有患者密码不因新增绑定或生成二维码而重置。
- 入口固定非筛选访视的患者 `FormBinding`；只有进行中研究、正常表单及已有正式入组患者时允许创建或重新生成。
- 入口与会话随机数均至少 32 字节；患者 Cookie 名称默认 `vispect_patient_session`、路径 `/api/patient/`、HttpOnly、SameSite=Lax，Secure 沿用部署配置。
- 手机从 320 像素宽支持单列布局；桌面内容最大宽度约 960 像素。二维码使用实际站点源地址；真实手机验收单独记录。
- 业务表继续 FORCE RLS，运行账号没有超级用户、所有者或 BYPASSRLS 权限。不得给控制面开放临床表全局读取权限。
- 草稿与正式提交使用修订号；正式提交使用幂等键；患者提交后只读且不自动完成访视。
- 研究进行中允许修订已完成访视的患者答案，包括全部访视已完成的受试者；不改变访视进度。医生表单保留原锁定范围，停止随访、研究暂停／结束、表单暂停或对象删除后只读。
- 保留旧答案、历史、审计 ID；保留最初提交主体、来源和时间；历史不允许修改或删除。
- 所有测试仅使用 `vispect_test` 或 `vispect_e2e_test`；不清空业务库、不删除数据卷，不覆盖工作区已有改动。测试清理必须包含 `patient_portal_` 表。

## 评审重点

1. 家庭账号关联两个同名患者：选择项须带档案编号，提交结果必须归到明确选择的患者（任务 6、11）。
2. 退出或改密后使用浏览器后退、其他标签页或迟到响应：旧患者内容必须被清理，旧请求不得落到新患者或新机构（任务 5、10）。
3. 共用入口已失效但页面仍有草稿或提交回执：不能继续读取或提交；有效入口中的成功提交重试仍返回原结果（任务 7）。
4. 非必需患者表单在访视完成前没有提交：完成后不能让患者补填，医生只能修订已经提交的答案（任务 6、8）。
5. 新表未加入测试清理、跨连接失败或旧历史回填遗漏：重复执行测试无残留，事务失败无半份数据，旧历史能准确恢复修改后内容和原始提交人（任务 1、2、3）。

## 文件与接口划分

后端新增 `backend/apps/patient_portal/`：`types.py` 定义公共 Principal 与 TypedDict；`models.py` 定义患者身份、档案绑定、共用入口、会话、回执和活动记录；`scope_store.py` 只封装摘要解析及旧会话撤销函数；`access.py` 管理后台开通；`entries.py` 管理共用入口；`session_locks.py`、`sessions.py` 管理会话屏障；`authentication.py`、`permissions.py`、`middleware.py` 负责患者请求边界；`tasks.py` 负责只读任务解析；`answers.py` 负责患者写入；`activity.py` 负责追加记录；`staff_api.py`、`auth_api.py`、`task_api.py` 分别承接三类 HTTP 请求，序列化放入 `serializers.py`。

扩展 `followups/{models.py,answers.py,serializers.py,history.py,exports.py}` 的来源及修订能力，不复制一套答案模型。前端新增 `features/patient-portal/` 和 `features/patient-access/`；患者请求封装与工作人员 `api/client.ts` 分开，动态表单继续共享。

固定公共数据形状：

- `PatientPrincipal`：不可变结构 `{tenant_id: UUID, identity_id: UUID, session_id: UUID, session_token: UUID}`。
- `PatientAuthEnvelope`：`{user: {id, phone, must_change_password}, next: 'change_password'|'ready', session_token: string}`；未登录为 401。
- `PatientAccessPayload`：`{id, patient_id, login_phone, must_change_password, enabled, revision}`；未开通为 null。
- `PatientEntryPayload`：`{id, binding_id, token, enabled, revision, url_path, created_at}`；只对获授权工作人员返回 token。
- `PatientTaskChoice`：`{patient_id, patient_name, patient_code, task_state}`。
- `PatientTaskPayload`：`{patient_id, patient_name, patient_code, study_name, stage_name, form_version_id, definition, answer, task_state, writable, read_only_reason}`。
- `task_state` 固定为 `writable`、`submitted`、`not_open`、`visit_completed`、`study_paused`、`form_paused`、`followup_stopped`、`followup_completed`、`study_ended`。已提交答案仍提供独立的状态原因，页面不能据 `task_state` 自行推断写权限。
- `AnswerPayload` 保留既有键，增加 `recorded_by_kind`、可空 `recorded_by_patient_id`、`submission_source`、原始提交主体标识及名称、`can_revise`、`revise_block_reason`；原 `recorded_by_id` 允许 null。提交来源固定为 `doctor`、`proxy`、`patient`，草稿未提交时为 null。

---

### 任务 1：患者数据模型、最小范围解析与测试隔离

**文件：** 新建 `backend/apps/patient_portal/{__init__.py,types.py,models.py,scope_store.py,activity.py,migrations/__init__.py,migrations/0001_initial.py,migrations/0002_security.py}`、`backend/tests/test_patient_portal_schema.py`；修改 `backend/config/settings.py`、`backend/tests/conftest.py`、`scripts/e2e-server.py`。

**接口：** `resolve_entry_scope(token: str) -> tuple[UUID, UUID]`；`resolve_session_scope(raw_cookie: str) -> tuple[UUID, UUID, UUID] | None`；`revoke_session_digest(digest: str) -> bool`。这些函数只返回机构／记录／身份 ID，不返回临床字段。

- [x] **步骤 1：编写失败测试。** `test_patient_identity_unique_per_tenant` 断言同机构等价号码只有一个身份、不同机构可分别存在；`test_patient_access_rejects_cross_tenant_identity`、`test_scope_functions_return_metadata_only`、`test_patient_tables_are_cleaned_between_worlds` 断言跨机构复合外键拒绝、解析投影只有指定 UUID、重复测试清理后没有旧患者账号。

  核心断言：`assert same_tenant_identity_count == 1`；`assert other_tenant_identity.id != identity.id`；`assert resolve_entry_scope(entry.token) == (entry.tenant_id, entry.id)`。跨机构写入使用 `pytest.raises(IntegrityError)`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_portal_schema.py -q`，预期因模型／范围解析能力缺失而失败；修正测试自身错误后再实施。
- [x] **步骤 3：实现模型与数据库权限。** 六实体使用设计中的名称。`PatientAccess.patient` 唯一；身份 `(tenant, phone)` 唯一；入口 `token_digest` 和会话 `credential_digest` 唯一；入口绑定部分唯一约束限定有效行；回执 `(identity, key)` 唯一。会话记录 `credential_version`、`context_token`、`expires_at`、`revoked`。活动及回执追加写入并撤销运行角色的更新／删除权限；临床关联带同机构复合外键。
- [x] **步骤 4：实现受限数据库函数及自检。** `vispect_patient_entry_scope(text)`、`vispect_patient_session_scope(text)` 及仅能按摘要撤销该会话的 `vispect_revoke_patient_session(text)`；固定 search_path、PUBLIC 无执行权限、只授予必要角色。owner 摘要策略只覆盖入口与会话表，正常和异常路径恢复事务查找变量。扩展测试／浏览器清理前缀及独立 `PATIENT_SESSION_COOKIE_NAME=vispect_e2e_patient_session`；不安装额外依赖。重跑步骤 2，并运行 `VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python backend/manage.py makemigrations --check --dry-run`，预期通过。
- [x] **步骤 5：提交。** 仅暂存本任务文件，提交说明：`基础：增加患者身份与受限入口会话模型`。

### 任务 2：答案主体、原始提交来源及历史增量迁移

**文件：** 修改 `backend/apps/followups/{models.py,answers.py}`；新建 `backend/apps/followups/authorship.py`、`backend/apps/followups/migrations/0005_patient_answer_authorship.py`、`0006_patient_answer_security.py`、`backend/tests/test_patient_answer_migration.py`；更新必要的现有模型测试工厂。

**接口：** `Answer.recorded_by` 可空，新增 `recorded_by_patient`；原始提交字段 `submitted_by`、`submitted_by_patient`、`submission_source` 在草稿时为空，正式提交后不可覆盖。`AnswerRevision` 新增 `new_answers` 与可空 `previous_recorded_by_patient`，原 `previous_recorded_by` 可空，修订 actor 保留工作人员外键。`set_answer_recorder(answer: Answer, *, staff_id: UUID | None = None, patient_identity_id: UUID | None = None) -> None` 设置当前互斥主体；`stamp_answer_submission(answer: Answer) -> None` 仅在首次提交时从当前主体保存原始主体与来源，后续不得改写；两者位于 `followups/authorship.py`，供任务 7／8 复用。

- [x] **步骤 1：编写失败测试。** `test_migration_restores_first_submitter_from_oldest_revision` 构造甲提交、乙修订、丙修订，断言原始提交人仍为甲、历史前后快照依次正确、所有旧 ID 与提交时间不变；`test_answer_recorder_exactly_one` 断言双主体／无主体拒绝；`test_history_is_immutable_after_migration` 断言真实 SQL 更新与删除失败。

  核心断言：`assert migrated.submitted_by_id == first_staff.id`；`assert migrated.submitted_at == original_submitted_at`；`assert history[0].new_answers == history[1].previous_answers`；非法 SQL 使用 `pytest.raises(DatabaseError)` 并回滚失败事务。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_answer_migration.py -q`，预期新字段和迁移缺失导致失败。
- [x] **步骤 3：实现迁移及原工作人员路径兼容。** `patient_portal.0001_initial` 依赖现有 `followups.0004_answer_security`；本任务迁移再依赖患者初始表，避免循环。先增可空字段，由 migration 账号受控回填旧提交来源、原始主体及历史 `new_answers`，再加 XOR、同机构外键、来源与代录一致性约束和不可变保护。旧代录记录保留 `is_proxy=true`；医生表单为 false；患者自填允许 false。历史回填暂停／重建触发器须在同一迁移事务内，结束后保护恢复。将既有工作人员保存／提交接入两个主体帮助函数，并在既有修订写入处补齐 `new_answers`，使本任务落地后原功能即符合新约束，不依赖后续任务才能运行。
- [x] **步骤 4：验证。** 重跑迁移测试及 `backend/tests/test_answers.py`、`backend/tests/test_rls.py`，检查迁移漂移；预期现有工作人员录入仍通过且旧历史不可变。
- [x] **步骤 5：提交。** 提交说明：`迁移：保留患者答案来源和完整修订主体`。

### 任务 3：患者填写账号开通及事务回滚

**文件：** 新建 `patient_portal/{access.py,staff_api.py,serializers.py}`、`backend/tests/test_patient_access.py`；修改 `patients/{services.py,serializers.py,api.py}`、`backend/config/urls.py`。

**接口：** `open_patient_access(actor: Actor, patient_id: UUID, phone: str, expected_revision: int) -> PatientAccess`；内部 `bind_patient_login(actor: Actor, patient: Patient, phone: str) -> PatientAccess` 在调用方业务事务中执行。新增 `POST /api/patients/<patient_id>/portal-access/`；新增患者接受 `enable_patient_portal: bool=false`、`login_phone: str`，普通 PATCH 不接受这些字段。

- [x] **步骤 1：编写失败测试。** `test_new_patient_login_uses_888888_and_requires_change` 断言哈希校验 `888888` 成功、数据库不是明文且 must_change_password=true；`test_rebind_existing_phone_does_not_reset_password` 断言共用手机号增加患者绑定但哈希和密码版本不变；`test_access_failure_rolls_back_identity_patient_and_quota` 注入审计失败，断言本次患者、账号、绑定、额度均回滚。

  核心断言：`assert identity.check_password('888888')`；`assert identity.password != '888888'`；`assert identity.must_change_password is True`；`assert saved_password_hash == original_password_hash`；`assert counts_after_failure == counts_before`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_access.py -q`，预期开通接口或原子性缺失而失败。
- [x] **步骤 3：实现开通。** 规范化手机号、验证患者修订号和既有负责关系；并发新号码使用唯一约束、事务级号码锁和冲突重读，不能覆盖已有密码。同步建档接入现有 `mutate_with_quota`；补开通保持 delta=0。普通联系方式不改变登录绑定，不提供换绑／重置入口。患者详情只返回获授权患者的 `portal_access`。
- [x] **步骤 4：验证。** 增加 `test_concurrent_open_creates_one_identity`、`test_contact_phone_does_not_grant_access`、`test_other_doctor_cannot_open_access`；运行本文件及 `backend/tests/test_patients.py backend/tests/test_quota.py`，预期全部通过。号码竞争用线程事件同步，不靠固定 sleep。
- [x] **步骤 5：提交。** 提交说明：`患者：支持明确开通手机号填写账号`。

### 任务 4：共用入口管理、候选查询与撤销

**文件：** 新建 `patient_portal/entries.py`、`backend/tests/test_patient_entries.py`；修改 `patient_portal/{staff_api.py,serializers.py}`、`backend/config/urls.py`。

**接口：** `entry_candidates(actor: Actor, form_id: UUID) -> QuerySet[FormBinding]`；`get_or_create_entry(actor: Actor, binding_id: UUID) -> PatientFormEntry`（已有记录含停用记录时返回该记录，不隐式重新开放）；`change_entry(actor: Actor, entry_id: UUID, action: Literal['disable','regenerate'], expected_revision: int) -> PatientFormEntry`。后台路径为 `/api/forms/<form_id>/patient-entry-options/`、`/api/patient-form-bindings/<binding_id>/entry/`、`/api/patient-form-entries/<entry_id>/<action>/`。

- [x] **步骤 1：编写失败测试。** `test_one_shared_entry_per_binding` 断言重复生成返回同一令牌；`test_entry_requires_member_non_screening_and_enrolled_patient` 断言仅表单作者、筛选绑定、未正式入组均不能创建；`test_regeneration_revokes_old_token_atomically` 断言旧令牌解析失效、新令牌仍指向原版本。

  核心断言：`assert first.id == repeated.id`；`assert first.token == repeated.token`；`assert enabled_entry_count == 1`；`assert resolve_entry_scope(new.token) == (new.tenant_id, new.id)`；旧令牌解析必须抛出 `ApiError` 且 `status == 404`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_entries.py -q`，预期管理接口缺失而失败。
- [x] **步骤 3：实现入口。** 在现有机构上下文中校验研究成员和绑定，事务中锁研究、表单、绑定与最新入口，随机令牌至少 32 字节。停用／重新生成要求当前入口 ID 与修订号，拒绝对已替换旧入口的迟到操作。暂停／结束状态允许查看或停用，禁止生成；审计不含 token。候选返回研究、访视、版本、最新入口和可创建原因，使用标准分页。
- [x] **步骤 4：验证。** 增加 `test_concurrent_generation_has_one_enabled_entry`、`test_unrelated_study_does_not_appear_in_candidates`、`test_entry_metadata_is_not_clinical_access`；运行本文件及表单、研究权限测试，预期通过。
- [x] **步骤 5：提交。** 提交说明：`表单：增加研究访视共用填写链接管理`。

### 任务 5：独立患者认证、首次改密及会话屏障

**文件：** 新建 `patient_portal/{session_locks.py,sessions.py,authentication.py,permissions.py,middleware.py,auth_api.py}`、`backend/tests/test_patient_auth.py`、`backend/tests/test_patient_session_concurrency.py`；修改 `core/middleware.py`、`config/{settings.py,urls.py}`。

**接口：** `authenticate_patient(entry_token: str, phone: str, password: str) -> PatientLoginIdentity`；`start_patient_login(request, identity: PatientLoginIdentity) -> PatientAuthEnvelope`；`patient_transaction(request, *, require_changed_password: bool = True) -> ContextManager[PatientPrincipal]`；`change_patient_password(request, old_password: str, new_password: str) -> PatientAuthEnvelope`；`logout_patient(request) -> None`。

- [x] **步骤 1：编写失败测试。** `test_first_login_blocks_all_clinical_endpoints` 断言默认密码登录 next=change_password，表单定义／候选／草稿／提交均 403；`test_patient_password_does_not_change_staff_identity` 断言同号码患者改密后工作人员密码与会话不变；`test_patient_login_requires_csrf` 断言缺令牌登录 403。

  核心断言：`assert login.json()['next'] == 'change_password'`；`assert clinical_response.status_code == 403`；`assert staff_identity.password == previous_staff_hash`；`assert staff_me.status_code == 200`；`assert login_without_csrf.status_code == 403`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_auth.py -q`，预期独立认证缺失而失败。
- [x] **步骤 3：实现认证。** 注册设计中的 csrf、resolve、login、me、change-password、logout 路径，临床接口只接受患者 Cookie 与 `X-Patient-Session-Token`。中间件在工作人员路径之前分流患者请求，绝不设置工作人员 `request.actor`。会话 Cookie 只存原始随机凭据，数据库只存摘要；所有副作用请求强制 CSRF。改密校验沿用现有 validators，轮换当前凭据／context_token、递增 credential_version、撤销其他会话；退出清除患者 Cookie，保持工作人员登录。
- [x] **步骤 4：实现并验证屏障。** 患者身份锁键固定 `sha256(b'vispect.patient.identity:' + identity_id.bytes)[:8]` 的有符号 64 位数；普通请求共享锁，改密、退出、重新登录使用排他锁。跨机构重新登录时旧身份与目标身份按 UUID 排序加锁，在同一 default 事务中校验目标凭据、按旧 Cookie 摘要撤销旧会话并建立新会话；持锁后重查密码版本与 token。`test_login_waits_for_old_write_and_revokes_waiter`、`test_password_change_revokes_other_sessions`、`test_expired_or_wrong_tenant_session_rejected` 使用独立连接和事件验证；旧 token 409、已撤销 Cookie 401。运行两个新测试文件及原认证／机构切换测试，预期通过。
- [x] **步骤 5：提交。** 提交说明：`认证：实现患者独立登录和首次强制改密`。

### 任务 6：患者档案选择、任务解析与只读状态

**文件：** 新建 `patient_portal/{tasks.py,task_api.py}`、`backend/tests/test_patient_tasks.py`；修改 `patient_portal/serializers.py`、`config/urls.py`。

**接口：** `resolve_patient_tasks(principal: PatientPrincipal, entry_token: str) -> list[PatientTaskChoice]`；`get_patient_task(principal: PatientPrincipal, entry_token: str, patient_id: UUID) -> PatientTaskPayload`；`locked_patient_task(principal: PatientPrincipal, entry_token: str, patient_id: UUID) -> tuple[PatientFormEntry, VisitInstance, FormBinding]` 供任务 7 在事务中使用。

- [x] **步骤 1：编写失败测试。** `test_shared_qr_returns_only_explicitly_bound_enrolled_patients` 断言号码相同但未绑定者不出现，其他研究入组者不出现；`test_same_name_choices_include_patient_code` 断言同名患者仍有不同 ID 与档案编号；`test_completed_optional_unsubmitted_form_is_read_only` 断言已完成访视无答案时 writable=false。

  核心断言：`assert {c['patient_id'] for c in choices} == explicitly_bound_enrolled_ids`；`assert len({c['patient_code'] for c in choices}) == 2`；`assert task['writable'] is False`；`assert task['task_state'] == 'visit_completed'`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_tasks.py -q`，预期任务匹配缺失而失败。
- [x] **步骤 3：实现任务解析。** 按已认证身份、明确绑定、正式入组、本入口访视实例逐级限制；仅返回该患者表单版本及其答案。优先服务端确定 writable/read_only_reason，不接受客户端提交访视或绑定 ID 决定授权。只读状态覆盖未来访视、已提交、已完成、停止、暂停及结束；删除对象或无授权 404，不泄露临床档案备注。
- [x] **步骤 4：验证。** 增加 `test_patient_cannot_request_other_patient_or_doctor_form`、`test_completed_followup_can_view_existing_answer_only`、`test_overdue_current_visit_remains_writable`；运行本文件及 `backend/tests/test_schedule.py backend/tests/test_enrollments.py`，预期通过。
- [x] **步骤 5：提交。** 提交说明：`患者：按明确档案绑定解析本人填写任务`。

### 任务 7：患者草稿、正式提交、幂等及竞争验证

**文件：** 新建 `patient_portal/answers.py`、`backend/tests/test_patient_answers.py`、`backend/tests/test_patient_answer_concurrency.py`；修改 `patient_portal/{task_api.py,activity.py}`、`followups/{answers.py,serializers.py}` 的工作人员／患者混合草稿主体赋值及可空主体序列化；复用任务 2 的 `followups/authorship.py`。

**接口：** `save_patient_answer(principal: PatientPrincipal, entry_token: str, patient_id: UUID, answers: dict, expected_revision: int) -> Answer`；`submit_patient_answer(principal: PatientPrincipal, entry_token: str, patient_id: UUID, answers: dict, expected_revision: int, key: str) -> Answer`。写入路径只接收 action、answers、expected_revision；正式提交键来自 `Idempotency-Key`。

- [x] **步骤 1：编写失败测试。** `test_patient_submit_records_real_origin` 断言单份 Answer、is_proxy=false、原始患者主体和提交时间正确；`test_retry_after_completed_visit_returns_existing_receipt` 断言同键同内容不新增答案、不改时间；`test_revoked_entry_cannot_read_submission_receipt` 断言入口撤销后重试拒绝；`test_proxy_and_patient_share_revision_checked_draft` 断言工作人员保存后患者旧修订号返回 409。

  核心断言：`assert answer.submission_source == 'patient'`；`assert answer.is_proxy is False`；`assert answer.submitted_by_patient_id == principal.identity_id`；`assert retry.id == first.id`；`assert retry.submitted_at == first.submitted_at`；`assert stale_write.status_code == 409`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_answers.py -q`，预期患者写入和幂等能力缺失而失败。
- [x] **步骤 3：实现保存和提交。** `evaluate_answers` 统一后端校验，保留当前 Answer 唯一约束。先验证会话、入口和当前对象授权，再查回执；命中合法回执可绕过已完成／暂停造成的“新写入”状态限制。新写入检查当前访视、患者填写对象和表单状态；使用修订号，通过任务 2 的 `set_answer_recorder`／`stamp_answer_submission` 记录当前主体及最终正式提交来源，工作人员接手患者草稿时也清除互斥的患者主体字段。同步让共享 `answer_payload` 安全序列化可空工作人员主体，确保新患者 API 和后台查询不因 `.recorded_by.name` 报错。回执摘要绑定 action、患者、入口、访视、绑定、答案及 expected_revision；同键不同内容 409；答案、活动与回执同事务。
- [x] **步骤 4：锁顺序与验证。** 在任务 5 身份屏障之后，患者写入沿用现有顺序：机构配额行 → 研究 → 患者 → 入组 → 访视 → 表单 → 绑定 → 入口 → 答案 → 回执；同层多行按 UUID 排序。入口管理采用研究 → 表单 → 绑定 → 入口，不逆向请求入组／配额锁；表单暂停只锁表单。回执并发使用身份＋键的事务 advisory lock，在临床行锁之前获取且所有患者写入一致。`test_submit_races_with_complete_stop_pause_and_revoke`、`test_same_key_concurrent_submit_has_one_answer`、`test_hidden_answers_are_cleaned_by_shared_engine` 用真实连接和事件核验，运行两个新文件及原答案／幂等测试，预期通过。
- [x] **步骤 5：提交。** 提交说明：`填写：保存患者草稿并保证提交幂等与隔离`。

### 任务 8：医生修订范围、来源序列化与导出

**文件：** 修改 `followups/{answers.py,serializers.py,history.py,exports.py,api.py}`；新建 `followups/revision_policy.py`、`backend/tests/test_patient_answer_revisions.py`；扩展 `backend/tests/test_exports.py`。

**接口：** `revision_policy(actor: Actor, answer: Answer) -> tuple[bool, str | None]`；原 `revise_answer(actor, answer_id, answers, reason, expected_revision)` 签名保持。`answer_payload`、`revision_payload` 增加来源／前后快照，固定版本 definition 由获授权历史接口返回，不向患者提供工作人员修订接口。

- [x] **步骤 1：编写失败测试。** `test_revise_completed_patient_answer_preserves_origin_and_progress` 断言原因必填、前后快照正确、submitted_by／submitted_at／来源／当前访视／入组状态不变；`test_completed_optional_unsubmitted_answer_cannot_be_created_by_revision` 断言无答案或草稿不能借修订创建正式提交；`test_completed_doctor_answer_remains_locked` 断言医生表单原规则不变。

  核心断言：`assert revised.answers == replacement`；`assert revised.submitted_by_patient_id == original_patient_identity_id`；`assert revised.submitted_at == original_submitted_at`；`assert enrollment.current_visit_id == previous_current_visit_id`；`assert history.reason == reason`；`assert history.new_answers == replacement`。
- [x] **步骤 2：运行失败验证。** `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_patient_answer_revisions.py -q`，预期已完成访视的患者答案仍被旧锁定逻辑拒绝。
- [x] **步骤 3：实现修订与展示数据。** 将“允许新填”与“允许修订”的业务判断分开，严格使用设计状态表；完成全部访视的受试者可修订患者答案，stopped 不可以。写历史、当前答案及工作人员审计同事务；历史 actor 仍为实际工作人员，患者提交身份不被覆盖。
- [x] **步骤 4：验证。** 增加 `test_revise_stopped_paused_ended_or_unowned_patient_denied`、`test_patient_origin_export_has_no_null_staff_crash`、`test_multiple_revisions_preserve_first_patient_submission`；导出区分三类来源与原始／最近主体。运行新文件及 `backend/tests/test_answers.py backend/tests/test_exports.py backend/tests/test_transitions.py`，预期通过。
- [x] **步骤 5：提交。** 提交说明：`修订：允许完成访视患者答案留痕修改`。

### 任务 9：后台患者账号与共用二维码界面

**文件：** 新建 `frontend/src/features/patient-access/{api.ts,PatientAccessPanel.tsx,PatientEntryDialog.tsx,patient-access.test.tsx}`；修改 `features/patients/{api.ts,PatientEditor.tsx,PatientDetail.tsx}`、`features/forms/{FormsPage.tsx,FormDesigner.tsx}`、`features/studies/ProtocolEditor.tsx`。

**接口：** `openPatientAccess(patient: Patient, login_phone: string): Promise<PatientAccessPayload>`；`PatientEntryDialog({formId?: string, bindingId?: string, open: boolean, onClose: () => void})`，两个入口复用同一组件。候选加载使用现有工作人员 api 和机构切换取消机制。

- [x] **步骤 1：编写失败测试。** `test_create_patient_can_open_default_login_without_password_field` 断言勾选后传 enable_patient_portal/login_phone，无自定义初始密码框；`test_entry_dialog_selects_study_stage_and_fixed_version` 断言选择研究和访视后显示固定版本；`test_existing_entry_is_reused_and_regeneration_uses_revision` 断言界面操作发送正确入口 ID／修订号。

  核心断言：`expect(requestBody.enable_patient_portal).toBe(true)`；`expect(screen.queryByLabelText('初始密码')).not.toBeInTheDocument()`；`expect(screen.getByText('v1')).toBeVisible()`；`expect(regenerateBody.expected_revision).toBe(entry.revision)`。
- [x] **步骤 2：运行失败验证。** `pnpm --dir frontend test --run src/features/patient-access/patient-access.test.tsx`，预期入口／账号组件尚不存在而失败。
- [x] **步骤 3：实现页面。** 使用现有 Checkbox、Input、Drawer／Modal、Select、QRCode。生成 URL 使用 `new URL(url_path, window.location.origin)`；二维码下载使用 Ant Design 已安装组件公开 DOM 输出能力，在浏览器本地导出，不上传外部服务。已有绑定显示号码和首次改密状态；未保存账号／入口操作纳入 `useWorkspaceDirty`，切换机构不残留弹窗和链接。
- [x] **步骤 4：验证。** 增加 `test_workspace_switch_clears_patient_entry_dialog`，运行本任务测试及已有患者、表单设计器、机构切换相关前端测试，预期通过。
- [x] **步骤 5：提交。** 提交说明：`后台：提供患者账号开通与共用二维码`。

### 任务 10：患者请求封装、独立路由与首次登录界面

**文件：** 新建 `features/patient-portal/{types.ts,client.ts,api.ts,PatientAuthProvider.tsx,PatientPortalLayout.tsx,PatientLoginPage.tsx,PatientPasswordPage.tsx,patient-auth.test.tsx}`；修改 `app/{App.tsx,router.tsx}`。

**接口：** `patientApi<T>(path: string, options?: {method?: string, body?: unknown, idempotencyKey?: string, signal?: AbortSignal}): Promise<T>`；`usePatientAuth()` 返回 envelope、loading、login、changePassword、logout、refresh；`/patient/fill/:token` 始终保留原目标。患者查询使用独立 QueryClient，只在患者布局挂载 PatientAuthProvider；后台 AuthProvider 移至后台路由边界。

- [x] **步骤 1：编写失败测试。** `test_patient_login_returns_to_original_qr_after_password_change` 断言 next=change_password 优先且成功回原令牌；`test_patient_request_does_not_send_workspace_token_or_staff_events` 断言患者请求无 X-Workspace-Token、401 不触发工作人员退出；`test_back_navigation_after_logout_revalidates_and_clears_cache` 断言后退不恢复旧患者内容。

  核心断言：`expect(screen.getByRole('heading', {name:'修改初始密码'})).toBeVisible()`；`expect(location.pathname).toBe('/patient/fill/' + token)`；`expect(patientRequest.headers.has('X-Workspace-Token')).toBe(false)`；`expect(screen.queryByText(previousPatientName)).not.toBeInTheDocument()`。
- [x] **步骤 2：运行失败验证。** `pnpm --dir frontend test --run src/features/patient-portal/patient-auth.test.tsx`，预期患者认证边界缺失而失败。
- [x] **步骤 3：实现患者认证。** client 使用患者 csrf 路径、X-Patient-Session-Token、独立请求代次与事件命名；认证变化取消患者查询并清缓存，不修改工作人员 client 状态。广播仅发到独立患者频道；pageshow（含 bfcache）及重新聚焦时重新校验。为防止已返回但正文迟到的数据复活，业务响应落入缓存前核验当前会话 token；失配丢弃。登录／改密输入支持 password autocomplete，不持久化密码和答案。
- [x] **步骤 4：验证。** 增加 `test_late_response_after_new_patient_login_is_discarded`、`test_patient_layout_never_mounts_staff_auth_provider`，运行本任务与既有认证／机构切换测试，预期后台原行为保持。
- [x] **步骤 5：提交。** 提交说明：`患者端：增加独立登录改密与会话隔离`。

### 任务 11：患者选择、响应式填写及提交恢复

**文件：** 新建 `features/patient-portal/{PatientFillPage.tsx,PatientChoice.tsx,PatientTaskForm.tsx,patient-fill.test.tsx,patient-portal.css}`；必要时修改共享 `form-engine/{DynamicForm.tsx,FieldControl.tsx}` 以支持可配置提交确认，保留后台默认行为。

**接口：** `PatientTaskForm({task: PatientTaskPayload, entryToken: string, onSaved: () => Promise<void>})`；`PatientChoice` 用 patient_id 选择，显示 patient_name＋patient_code。任务表单 key 包含入口＋患者＋版本，患者选择切换前检查未保存内容。

- [x] **步骤 1：编写失败测试。** `test_same_name_patient_choice_submits_selected_patient_only` 断言同名第二人提交路由为其 ID；`test_network_error_preserves_answers_and_same_idempotency_key` 断言失败后输入和提交键保留；`test_submitted_patient_form_is_read_only` 断言成功后无编辑／再次提交动作。

  核心断言：`expect(submitUrl).toContain('/patients/' + secondPatient.id + '/answers/')`；`expect(screen.getByLabelText(question.title)).toHaveValue(typedAnswer)`；`expect(secondKey).toBe(firstKey)`；`expect(screen.queryByRole('button', {name:'提交答案'})).not.toBeInTheDocument()`。
- [x] **步骤 2：运行失败验证。** `pnpm --dir frontend test --run src/features/patient-portal/patient-fill.test.tsx`，预期填写页缺失而失败。
- [x] **步骤 3：实现填写。** 复用 DynamicForm，引入提交确认后才发起写入；新任务才生成新幂等键，网络重试继续原键，成功后读取服务器状态。409 保留本地内容和明确冲突提示，用户确认重新加载才替换；切换患者有未保存确认。手机 320 像素起单列、选项换行、输入满宽，桌面最大 960 像素，键盘不遮挡操作。readonly 原因使用服务端文案，超窗仅提醒；卸载／退出清理本地状态。
- [x] **步骤 4：验证。** 增加 `test_failed_draft_does_not_carry_to_other_patient`、`test_future_or_completed_optional_form_has_no_submit`；运行本文件及 DynamicForm／engine 测试，预期所有题型及原后台表单不回归。
- [x] **步骤 5：提交。** 提交说明：`患者端：完成移动与电脑表单填写闭环`。

### 任务 12：后台来源、完成访视修订与历史差异展示

**文件：** 修改 `features/followups/{api.ts,AnswerEntry.tsx,AnswerHistory.tsx,StudyAnswersTab.tsx,VisitDetail.tsx,followups.test.tsx}`；新建 `features/followups/answerOrigins.ts`（统一来源与主体文案）及其行为测试。

**接口：** 前端 Answer／History 对齐全局形状；历史响应提供 new_answers 与固定版本 definition。`AnswerEntry` 的修订按钮使用 answer.can_revise，草稿保存仍使用 visit.writable，不能将完成后修订当作开放访视。

- [x] **步骤 1：编写失败测试。** `test_completed_visit_patient_answer_can_revise_with_reason` 断言完成访视仍有修订按钮、原因必填、提交带现有修订号；`test_revision_preserves_patient_submitter_display` 断言患者提交人和医生最近修改人分开展示；`test_history_renders_question_labels_and_before_after_values` 断言题目及选项用固定版本中文文案展示。

  核心断言：`expect(screen.getByRole('button', {name:'修订答案'})).toBeEnabled()`；`expect(screen.getByText('请填写修订原因')).toBeVisible()`；`expect(reviseBody.expected_revision).toBe(answer.revision)`；`expect(screen.getByText(question.title)).toBeVisible()`；同时核对患者原始主体与医生修订主体文案。
- [x] **步骤 2：运行失败验证。** `pnpm --dir frontend test --run src/features/followups/followups.test.tsx`，预期旧 writable 判断或来源文案导致新断言失败。
- [x] **步骤 3：实现后台显示。** 患者自填、工作人员代录、医生填写文案集中处理；原始提交信息与最近修改信息独立展示。修订历史提供前后差异及完整快照；表单暂停／研究只读仍正确禁止。更新完成访视确认提示，说明患者答案后续可在获授权时留痕修订，不能继续笼统宣称全部答案只读。
- [x] **步骤 4：验证。** 运行随访及患者相关前端测试、`pnpm --dir frontend typecheck`，预期通过，无可空工作人员主体解引用。
- [x] **步骤 5：提交。** 提交说明：`后台：展示患者提交来源与完整修订差异`。

### 任务 13：真实浏览器闭环、完整回归及交付记录

**文件：** 新建 `frontend/e2e/patient-portal.spec.ts`、`docs/delivery/2026-10-16-患者扫码填写验收.md`；修改 `frontend/e2e/helpers.ts`、`README.md`、设计／计划状态；如演示数据需要新场景，仅扩展独立虚构数据初始化，不给旧真实患者自动开通账号。

**接口：** 浏览器使用既有 8001／5174 端口、`vispect_e2e_test` 和独立患者 Cookie；`scripts/verify.sh` 为最终统一验证入口。

- [x] **步骤 1：编写失败浏览器测试。** `patient-portal.spec.ts` 覆盖后台建档开通、正式入组、从表单生成共用码、两名患者各自首次登录改密、草稿恢复和提交、后台查看、完成访视后修订与历史、同浏览器工作人员会话保留、入口撤销。增加 320／390／1280 像素宽度，断言 document.scrollWidth 不大于 viewport、长题目和全部现有题型可操作。

  核心断言：`await expect(patientPage.getByText('答案已提交')).toBeVisible()`；`await expect(staffPage.getByText('患者自填')).toBeVisible()`；`expect(await patientPage.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewportWidth)`；工作人员页继续展示原活动机构，修订前后提交时间一致。
- [x] **步骤 2：运行浏览器验证。** `pnpm --dir frontend exec playwright test e2e/patient-portal.spec.ts`；若新断言失败，按根因修复对应任务，不能用固定等待掩盖会话或数据问题。额外验证两个标签页重新登录／退出后，旧表单不能写入新患者或新机构。
- [x] **步骤 3：运行完整检查。** 执行 `scripts/verify.sh`，预期后端全部测试、迁移一致性、Django 检查、前端测试、类型检查、构建及浏览器闭环全部通过；对本次新增数据迁移使用独立测试库完成从旧结构到新结构的迁移演练。不对业务数据库自动执行迁移。
- [x] **步骤 4：独立评审及交付。** 按执行方式调用 `superpowers:requesting-code-review` 检查整条改动，优先审查患者越权、跨机构会话、事务回滚、历史不可变和迁移；修复有证据的问题并重跑受影响检查。README 记录初始密码、首次改密规则、患者开通、二维码及可达站点要求；验收记录区分自动化浏览器、部署验证和真实手机扫码。没有真实设备证据时明确设备验收待完成，不声称已经通过。
- [x] **步骤 5：提交并整理分支。** 更新设计／计划状态和验收记录，提交说明：`交付：验证患者扫码填写与医生修订闭环`；用 `superpowers:finishing-a-development-branch` 整理交付，未经用户授权不合并或部署。

## 执行交接与自检

本计划是同一端到端流程的 13 个顺序交付任务；前后端共享主体和任务接口，数据库迁移、会话屏障和答案写入存在明确依赖，不拆为独立产品。每个任务都包含失败测试、最小实现、通过验证及单独提交。

自检映射：设计第 3 节→任务 1／3／5／9／10；第 4 节→任务 4／6／9／11；第 5 节→任务 1／2／8／12；第 6 节→任务 7／8；第 7 节→任务 1／5／6／7／10；第 8 节→任务 3 至 12；第 9 节→任务 13。五项评审重点均有具名测试归属。公共数据形状、函数签名、接口路径、锁顺序和历史回填有明确决定，无待定实施项。

已按用户确认在本会话顺序实施 13 项任务，并完成一次独立评审。3 项重要问题经失败复现、修复和完整回归验证；最终后端 262 项、前端 105 项及浏览器 10 项通过。代码保留在原生隔离工作区，未合并、推送或部署。
