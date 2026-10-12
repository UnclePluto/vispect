# 多租户健康管理平台首版实施计划

> **执行代理须知：** 必须使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐任务执行本计划。执行方法由用户评审本计划后选择。步骤使用 `- [ ]` 跟踪，先验证失败，再实现并验证通过，每个任务形成独立提交。

**目标：** 交付基于 Django、React 和 PostgreSQL 的多租户健康管理后台，完成从建档、研究配置到入组、访视填写和答案导出的完整流程。

**架构：** 模块化单体后端与独立 Ant Design 前端，共用语言无关的表单协议和测试样例。数据库角色、RLS、事务上下文及服务端权限共同隔离数据；配额和状态转换在数据库事务内完成。各模块依赖同一身份、授权、表单版本与错误协议，按以下顺序实施。

**技术栈：** Python 3.12；Django `>=5.2,<5.3`；DRF `>=3.16,<3.17`；PostgreSQL 17；psycopg 3、jsonschema 4、openpyxl 3.1；Node.js `>=22.12`、pnpm 10；React 19、TypeScript 5.9、Vite 7、Ant Design 6、`@ant-design/icons` 6、React Router 7、TanStack Query 5、Ajv 8、dayjs 1；pytest/pytest-django、Vitest `>=3.2`、Testing Library、Playwright。实施时生成并提交 `uv.lock` 与 `pnpm-lock.yaml`，不以浮动最新版本部署。

**设计依据：** [已确认设计](/Users/nick/my_dev/workout/Vispect/docs/superpowers/specs/2026-10-12-health-management-platform-design.md)。本计划和设计需要一起阅读。

## 全局约束

- 前端采用 React、TypeScript、Vite 与真实 Ant Design 组件。
- 后端采用 Django 与 Django REST Framework（DRF），数据库采用 PostgreSQL。
- 共享数据库，使用 `tenant_id`、数据库行级安全（RLS）和服务端权限共同隔离数据。
- 租户管理员查看本租户全部数据；医生仅访问负责的患者及参与的研究。
- 暂不开发小程序、患者独立登录端、微信邀请和扫码填写。
- 首版不包含矩阵题、附件题、排序题、自动计分和研究流程分支。
- 停用账号或结束研究不释放额度；软删除释放额度，恢复操作重新检查额度。
- 下调上限不能低于当前使用量。
- 首版不恢复已停止的随访，也不重复入组。
- 未设置租户上下文时拒绝业务读写；应用运行账号不使用超级用户、表所有者或 `BYPASSRLS` 权限。
- 所有界面、错误说明和提交说明使用简体中文。患者、观察、入组编号按字符串保存，不能丢失前导零。
- 日期边界使用 `Asia/Shanghai`，时间戳使用带时区值；提交到服务端的日期为 `YYYY-MM-DD`。

## 评审重点

1. 中文名称、首尾空格与前导零编号：不破坏姓名内容、不把字符串编号转为数字，重复编号返回明确冲突。测试归属任务 4、5、10。
2. 上海时区的午夜、月末、闰日与超期访视：计划日期正确，越过窗口只改变提示，不自行推进流程。测试归属任务 6、10、13。
3. 网络重试、最后一个名额与旧修订号：重复操作不重复生成对象，不覆盖他人保存，额度不会被并发突破。测试归属任务 3、4、10、11。
4. 账号停用、负责关系或成员改变后的缓存与导出：权限立即生效，旧页面、旧会话和旧操作回执不能暴露已失去权限的数据。测试归属任务 2、5、10、12、13。
5. 空导出、重复长表单标题、公式样式文本：始终生成合法工作簿，表名唯一且不超过 31 字符，答案作为文本保存。测试归属任务 12。

## 文件边界与通用接口

以下新增路径相对仓库 `/Users/nick/my_dev/workout/Vispect`。每个后端业务包包含自己的模型、服务、序列化器、API 与迁移，不建立一个包含全部业务的模型或视图文件。

| 路径 | 职责 |
| --- | --- |
| `backend/config/` | Django 设置、路由、WSGI、数据库角色连接 |
| `backend/apps/core/` | Actor、错误、分页、事务上下文、RLS 迁移辅助、幂等回执、审计 |
| `backend/apps/accounts/` | 自定义账号、会话认证、密码修改 |
| `backend/apps/tenants/` | 租户、配额、控制面统计 |
| `backend/apps/doctors/`、`patients/` | 医生、患者及负责关系 |
| `backend/apps/forms/` | 表单协议解释、目录、发布版本 |
| `backend/apps/studies/` | 研究、成员、阶段及表单绑定 |
| `backend/apps/followups/` | 入组、访视、答案、修订和导出 |
| `backend/tests/` | PostgreSQL 角色验证、API 与业务测试 |
| `frontend/src/app/`、`api/` | 路由、布局、会话、请求、缓存 |
| `frontend/src/features/` | 按业务模块组织的页面、组件与测试 |
| `frontend/src/form-engine/` | 纯 TypeScript 表单解释器与共用渲染器 |
| `contracts/` | JSON Schema 和两种语言共用的规则样例 |
| `infra/`、`scripts/`、`frontend/e2e/` | 数据库角色初始化、启动和浏览器验收 |

固定协议：

- `Actor(account_id: UUID, tenant_id: UUID | None, role: str, doctor_id: UUID | None)`；角色值为 `platform_admin`、`tenant_admin`、`doctor`。
- `ApiError(code: str, message: str, fields: dict[str, list[str]], status: int)`；错误响应为 `{code, message, fields}`，列表响应为 `{count, results}`。无会话返回 401，角色禁止返回 403，对象不可用返回 404，配额、修订及状态冲突返回 409。
- 所有可编辑对象含整数 `revision`；更新携带 `expected_revision`，过期返回 `revision_conflict`。所有对象 ID 为 UUID，租户标识 `slug` 独立于 UUID。
- `FormDefinition = {schema_version: 1, title, description, fields}`。题目使用 `id/type/label/description/required`；选项为 `{id, label}`；约束名用 `min/max/step/max_length/decimal_places/min_selections/max_selections`。
- 条件为 `display: {mode: 'all' | 'any', rules: [{source_id, op, value?}]}`；操作符为 `eq/neq/contains/gt/gte/lt/lte/answered`。跳题为 `jumps: {option_id: target_field_id}`。
- `JSONValue = null | boolean | number | string | JSONValue[] | {[key: string]: JSONValue}`，Python 对应 JSON 原生值；由任务 6 的两端协议类型提供。
- `EvaluationResult = {visible_ids: string[], answers: Record<string, JSONValue>, errors: Record<string, string[]>}`；错误数组使用稳定代码，例如 `required`、`invalid_type`、`invalid_option`、`invalid_date`、`out_of_range`、`invalid_precision`，API 再映射为中文字段说明。
- 前端 `api<T>(path, {method?, body?, idempotencyKey?}): Promise<T>` 携带 Cookie，非安全方法携带 CSRF。幂等操作以 `Idempotency-Key` 标识，同一键不同请求内容返回 `idempotency_key_reused`。
- 后端命令默认在 `backend/` 执行，前端命令默认在 `frontend/` 执行；所有数据库测试使用真实 PostgreSQL。迁移和测试库建立可用所有者连接，API 与业务断言必须使用受限运行连接。

---

### 任务 1：可启动环境与 PostgreSQL 验证入口

**文件：** 新建 `.gitignore`、`.env.example`、`compose.yaml`、`backend/pyproject.toml`、`backend/manage.py`、`backend/config/{settings,urls,wsgi}.py`、`backend/apps/core/{types,errors,health}.py`、`backend/tests/{conftest,test_health}.py`、`frontend/{package.json,index.html,vite.config.ts,vitest.config.ts,tsconfig.json}`、`frontend/src/{main.tsx,app/App.tsx,test/setup.ts}`、`infra/postgres/init-roles.sql`、`scripts/bootstrap-test-db.py`；生成 `backend/uv.lock` 与 `frontend/pnpm-lock.yaml`。业务包同时建立 Python 包入口与 Django AppConfig；各任务迁移路径为其业务包的 `migrations/`。

**接口：** 提供 `GET /api/health/ -> {status: 'ok', database: 'postgresql'}`；`provision_test_database(owner_dsn, app_dsn, control_dsn) -> None`；提供上述 `ApiError`。创建 `vispect_owner`、`vispect_app`、`vispect_control` 三种连接角色，后两者无超级用户、所有者、绕过 RLS 或建库权限。任务 1 不启用默认 Django 用户表，任务 2 在首个认证迁移前确定自定义用户模型。

- [ ] 写 `test_health_reports_postgresql`：`assert response.status_code == 200; assert response.json() == {'status': 'ok', 'database': 'postgresql'}`；数据库断开时断言 503，不返回连接串。
- [ ] 安装本任务依赖并启动 PostgreSQL，运行 `uv run pytest tests/test_health.py -q`，确认因为健康路由缺失而失败，不能把环境安装失败当作测试红灯。
- [ ] 实现健康接口、数据库角色、测试库建立与设置；前端只搭建可运行应用入口。`DATABASE_URL`、`CONTROL_DATABASE_URL` 使用受限账号；`MIGRATION_DATABASE_URL` 只用于管理命令和测试库准备，Web 进程不读取或注册所有者连接。配置 `pnpm test/typecheck/build` 与 pytest 的真实数据库测试入口。
- [ ] 运行 `uv run pytest tests/test_health.py -q` 与 `pnpm build`，均通过；检查 `current_user`、`rolsuper`、`rolbypassrls` 与表所有者，确认运行身份符合约束。
- [ ] 提交本任务明确列出的运行环境文件，提交说明：`基础：建立前后端运行环境和数据库角色`。

### 任务 2：租户上下文、账号与会话隔离

**文件：** 新建 `backend/apps/core/{context,middleware,permissions,rls}.py`、`backend/apps/tenants/{models,lookup}.py`、`backend/apps/accounts/{models,services,authentication,serializers,api}.py` 及首批迁移；新建 `backend/tests/{world,test_auth,test_rls}.py`；修改设置与路由。

**接口：** 提供 `Actor`；`tenant_transaction(tenant_id: UUID) -> ContextManager[None]`；`current_actor(request) -> Actor`；`apply_tenant_rls(table_name: str) -> list[str]`。测试 `TestWorld` 提供 `actor(tenant, role) -> Actor`、`login(tenant, role, enforce_csrf=True) -> APIClient`、`runtime_rows(tenant, table) -> list[UUID]`、`account_ids(tenant) -> list[UUID]`，查询结果按 UUID 排序。API：`/api/auth/{csrf,tenant-login,platform-login,me,logout,change-password}/`。自定义 `Account` 使用 `AUTH_USER_MODEL`，租户账号内用户名唯一，平台账号单独唯一。

- [ ] 写 `test_cross_tenant_account_rows_are_invisible`：`assert world.runtime_rows(tenant='a', table='accounts_account') == world.account_ids('a')`；写 `test_missing_context_denies_rows` 断言无上下文无租户记录；参数化验证读、写、连接复用和回滚。认证测试断言无 CSRF 的登录失败、同名用户名分别登录、旧会话停用后失效、平台角色不能调用租户业务入口。
- [ ] 运行 `uv run pytest tests/test_auth.py tests/test_rls.py -q`，确认 RLS/认证未实现时失败。
- [ ] 实现独立控制面连接与租户事务中间件，在认证查询前设置合法上下文；通过服务端会话确定业务租户，不信任客户端租户字段。创建 `apply_tenant_rls(table_name: str) -> list[str]` 迁移辅助并将其应用于账号和以后各业务表，设置 FORCE RLS、同租户约束及角色授权。登录、密码修改和所有写接口检查 CSRF。
- [ ] 用实际受限账号运行以上测试，确认非表所有者；检查平台连接仅能读取允许的控制面数据；首次登录必须先改密码才能调用业务写接口。
- [ ] 提交认证、上下文与迁移文件，提交说明：`功能：实现租户隔离和账号会话权限`。

### 任务 3：租户控制面、配额与通用事务工具

**文件：** 新建 `backend/apps/tenants/{quota,services,serializers,api}.py`、配额迁移；新建 `backend/apps/core/{models,idempotency,audit}.py`、核心迁移；新建 `backend/tests/{test_tenants,test_quota,test_idempotency}.py`。

**接口：** 消费任务 2 的 `Actor` 和事务上下文。提供 `UsageCounts(doctors: int, patients: int, studies: int)`；`mutate_with_quota(actor, resource: 'doctors'|'patients'|'studies', mutation: Callable[[], T]) -> T`；`quota_trigger_sql(table_name: str, resource: str) -> list[str]`；`run_idempotent(actor, key: str, operation: str, payload: dict, mutation: Callable[[], dict]) -> dict`；`audit(actor, action: str, object_type: str, object_id: UUID, changes: dict) -> None`。提供 `/api/platform/tenants/`、租户启停、管理员设置、额度配置与 `/api/platform/usage/`。

- [ ] 写 `test_limit_cannot_be_lower_than_usage`：已使用 1 时更新上限 0，断言 409、原额度不变；写 `test_tenant_admin_cannot_call_platform_api` 断言 403；写 `test_reused_key_with_different_payload` 断言 `idempotency_key_reused`。平台创建租户后断言初始管理员与配额在同一事务存在，失败时均不存在。
- [ ] 运行 `uv run pytest tests/test_tenants.py tests/test_quota.py tests/test_idempotency.py -q`，确认对应接口或服务缺失导致失败。
- [ ] 实现锁定配额行的通用写入入口。用量字段由任务 4、5、9 消费 `quota_trigger_sql` 安装的数据库触发器随业务行插入、软删除和恢复更新；触发器锁定配额行并检查上限，回滚时计数也回滚。计数函数由所有者安装、固定搜索路径和资源映射，禁止运行角色直接编辑用量。平台统计函数只返回租户和三项计数，撤销普通租户角色的执行权；平台角色不获得医生、患者或研究表读取权。幂等回执检查内容摘要与当前授权，审计不可通过普通 API 编辑。
- [ ] 运行以上测试并检查平台用量响应不含业务内容；额度零拒绝写入，未实现的资源尚无记录时计数为零，不能用假数据替代统计。
- [ ] 提交本任务文件，提交说明：`功能：实现租户管理配额和事务工具`。

### 任务 4：管理布局、医生档案与并发配额

**文件：** 新建 `backend/apps/doctors/{models,services,serializers,api}.py`、医生/RLS/计数触发器迁移、`backend/tests/test_doctors.py`；新建 `frontend/src/{api/client.ts,api/types.ts,app/router.tsx,app/queryClient.ts,app/AdminLayout.tsx}`；新建 `frontend/src/features/auth/{api.ts,AuthProvider.tsx,LoginPage.tsx,ChangePasswordPage.tsx,auth.test.tsx}`、`features/tenants/{api.ts,TenantsPage.tsx,TenantEditor.tsx,tenants.test.tsx}`、`features/doctors/{api.ts,DoctorsPage.tsx,DoctorEditor.tsx,DoctorDetail.tsx,doctors.test.tsx}`，后两项同在 `frontend/src/`。

**接口：** 消费任务 2、3 的事务、RLS、配额和审计接口。提供 `create_doctor(actor, data: dict) -> Doctor`、`update_doctor(actor, doctor_id: UUID, data: dict, expected_revision: int) -> Doctor`、`delete_doctor(actor, doctor_id: UUID, expected_revision: int) -> Doctor`、`restore_doctor(actor, doctor_id: UUID, expected_revision: int) -> Doctor`、`set_doctor_enabled(actor, doctor_id: UUID, enabled: bool, expected_revision: int) -> Doctor`；`/api/doctors/` 及停用/恢复动作。提供通用 `api<T>`、`useActor() -> Actor | null`、权限路由与基础 CRUD 表格交互；`TestWorld.doctor(tenant, **data) -> Doctor`。

- [ ] 写 `test_last_doctor_slot_is_atomic`：已有 2 名医生，上限 3，两个独立连接并发创建，`assert successes == 1; assert usage.doctors == 3`；写直接 SQL 超额插入拒绝、事务失败不占额、停用仍占额、软删除释放、恢复超额、中文姓名保留和医生不能改角色测试。前端写 `test_logout_clears_private_cache`，`expect(queryClient.getQueryCache().getAll()).toHaveLength(0)`。
- [ ] 运行 `uv run pytest tests/test_doctors.py -q` 与 `pnpm test --run src/features/auth src/features/doctors`，确认功能缺失导致失败。
- [ ] 实现医生账号和档案的原子创建、额度触发器及修订校验；完善 `TestWorld.doctor()`。构建中文 Ant Design 布局、两种登录、密码修改、租户控制面页面及医生列表/编辑/详情；切换会话身份时清空 Query 缓存。
- [ ] 运行本任务测试、`pnpm typecheck` 和 `pnpm build`；实际 API 验证医生自编辑仅允许基础资料，账号角色或 tenant 字段不能由表单覆盖。
- [ ] 提交本任务文件，提交说明：`功能：实现医生管理和标准后台布局`。

### 任务 5：患者档案、负责关系与可见范围

**文件：** 新建 `backend/apps/patients/{models,selectors,services,serializers,api}.py`、关联/RLS/计数迁移、`backend/tests/test_patients.py`；修改医生删除服务；新建 `frontend/src/features/patients/{api.ts,PatientsPage.tsx,PatientDetail.tsx,PatientEditor.tsx,patients.test.tsx}`。

**接口：** 消费任务 2、3 的事务、RLS、配额、审计与任务 4 的医生服务。提供 `visible_patients(actor) -> QuerySet[Patient]`、`create_patient(actor, data: dict) -> Patient`、`update_patient(actor, patient_id: UUID, data: dict, expected_revision: int) -> Patient`、`delete_patient(actor, patient_id: UUID, expected_revision: int) -> Patient`、`restore_patient(actor, patient_id: UUID, expected_revision: int) -> Patient`、`assign_doctors(actor, patient_id: UUID, doctor_ids: list[UUID], expected_revision: int) -> Patient`；`/api/patients/` 与 `/assign-doctors/`。提供 `TestWorld.patient(tenant, **data) -> Patient`。

- [ ] 写 `test_doctor_sees_only_assigned_patients`：两医生各自建档，`assert set(visible_patients(actor_a)) == {patient_a}`，另一个患者详情返回 404；写 `test_responsibility_change_revokes_access`：移除负责关系后 `assert old_client.get(detail_url).status_code == 404`；编号 `000001` 保持字符串，同手机号可建两份档案，跨租户负责医生不能绑定，患者恢复要重新检查配额。
- [ ] 运行 `uv run pytest tests/test_patients.py -q` 和 `pnpm test --run src/features/patients/patients.test.tsx`，确认未过滤的列表或缺失接口导致失败。
- [ ] 实现患者与多负责医生、复合外键、配额触发器和权限过滤；只有管理员能分配负责关系，医生创建时自动负责。医生删除前保护尚未转交的患者关系。UI 完成搜索分页、编辑、详情和负责医生分配。
- [ ] 运行以上测试、类型检查和构建；管理员可查看本租户全部患者，医生搜索、分页数量与详情使用同一可见范围。
- [ ] 提交本任务文件，提交说明：`功能：实现患者档案和医生负责关系`。

### 任务 6：跨语言动态表单规则协议

**文件：** 新建 `contracts/{form-definition.schema.json,form-cases.json}`；新建 `backend/apps/forms/{definition,engine}.py`、`backend/tests/test_form_engine.py`；新建 `frontend/src/form-engine/{types,definition,engine,engine.test}.ts`。

**接口：** 消费通用 JSON 协议。Python 提供 `validate_definition(definition: dict, publish: bool = False) -> dict[str, list[str]]`、`evaluate_answers(definition: dict, answers: dict, mode: Literal['draft','submit']) -> EvaluationResult`；TypeScript 提供对应 `validateDefinition(definition: FormDefinition, publish?: boolean): Record<string, string[]>`、`evaluateAnswers(definition: FormDefinition, answers: Record<string, JSONValue>, mode: 'draft'|'submit'): EvaluationResult`，camelCase 只用于函数名，JSON 属性保持相同 snake_case。题型值固定为 `text/textarea/number/date/radio/checkbox/select/slider`，协议版本固定为 1。

- [ ] 写 `test_shared_form_cases` 和两端参数化测试：每个 case 断言 `assert result.visible_ids == case['expected']['visible_ids']; assert result.answers == case['expected']['answers']; assert result.errors == case['expected']['errors']`，TypeScript 使用同样预期。样例包括隐藏必填、向后跳题、目标隐藏、零值、非法选项、未知题目、回跳、重复 ID、非法数字、精度越界，以及 `2024-02-29` 有效、`2026-02-29` 无效；无穷数字不能写进 JSON，在两端测试中另外构造并断言拒绝。
- [ ] 运行 `uv run pytest tests/test_form_engine.py -q` 与 `pnpm test --run src/form-engine/engine.test.ts`，确认解释器缺失导致失败。
- [ ] 实现定义校验及从前到后的解释器，只以已经激活并校验的前置答案参与条件。隐藏与跳过值移除；无答案时除 `answered` 判定外条件不成立；禁止任意脚本。草稿不强制未填项，提交检查可见必填项，数字必须有限，日期严格按实际日历校验。
- [ ] 两端运行同一份 case 文件全部通过；新增规则先新增共用 case，不能各自维护两份预期。检查预览与正式填写将消费同一解释器。
- [ ] 提交协议及两端解释器，提交说明：`功能：建立跨语言动态表单协议和规则引擎`。

### 任务 7：表单目录、不可变发布版本与暂停

**文件：** 新建 `backend/apps/forms/{models,selectors,services,serializers,api}.py`、表单/RLS/版本保护迁移、`backend/tests/test_forms.py`；新建 `frontend/src/features/forms/{api.ts,FormsPage.tsx}`。

**接口：** 消费任务 2、3 的事务/RLS/幂等/审计及任务 6 的 `validate_definition`。提供 `create_form(actor, definition: dict) -> Form`、`save_draft(actor, form_id: UUID, definition: dict, expected_revision: int) -> Form`、`publish_form(actor, form_id: UUID, expected_revision: int, key: str) -> FormVersion`、`set_form_paused(actor, form_id: UUID, paused: bool, expected_revision: int) -> Form`、`delete_form(actor, form_id: UUID, expected_revision: int) -> Form`、`restore_form(actor, form_id: UUID, expected_revision: int) -> Form`；`/api/forms/`、`/{id}/versions/`、`/publish/`、`/pause/`、`/resume/`。`FormVersion` 提供不可变 `definition`、版本号和 UUID。

- [ ] 写 `test_new_version_preserves_old_definition`：发布 v1，改草稿并发布 v2，`assert v1.definition == original; assert v2.id != v1.id`；直接 SQL 修改 v1 定义失败。写医生不能改其他人草稿、已发布模板同租户可引用、跨租户不可读取、暂停不删除版本、旧 revision 返回 409 测试。
- [ ] 运行 `uv run pytest tests/test_forms.py -q`，确认版本服务和权限未实现时失败。
- [ ] 实现所有者/管理员编辑和公开的租户内发布目录、事务发布、数据库版本不可变保护及软删除。所有模型应用 RLS；发布使用任务 6 校验及任务 3 幂等工具。提供表单目录操作与版本信息。
- [ ] 运行以上测试及前端构建，确认目录查询不包含答案，发布响应包含明确版本 UUID。
- [ ] 提交本任务文件，提交说明：`功能：实现表单发布版本和目录管理`。

### 任务 8：Ant Design 表单设计器与共用填写组件

**文件：** 新建 `frontend/src/features/forms/{FormDesigner,FieldPalette,QuestionList,FieldProperties,FormPreview}.tsx`、`designerState.ts`、`FormDesigner.test.tsx`；新建 `frontend/src/form-engine/{DynamicForm,FieldControl}.tsx` 与测试；修改前端路由。

**接口：** 消费任务 6 的 `validateDefinition/evaluateAnswers` 与任务 7 API。提供 `DynamicForm(props: {definition: FormDefinition, initialAnswers: Record<string, JSONValue>, mode: 'preview'|'entry', readOnly: boolean, onSaveDraft?: (answers: Record<string, JSONValue>) => Promise<void>, onSubmit?: (answers: Record<string, JSONValue>) => Promise<void>}): ReactNode`；`cloneField(definition: FormDefinition, fieldId: string): FormDefinition` 和 `moveField(definition: FormDefinition, fieldId: string, position: number): FormDefinition`。

- [ ] 写 `test_designer_preview_uses_same_rules_as_entry`：`expect(previewVisibleIds).toEqual(entryVisibleIds)`；测试八种题型、批量选项、题目移动/复制 ID、必填、属性编辑，以及保存被 409 拒绝后保留未保存编辑内容。预览点击提交后 `expect(answerRequests).toHaveLength(0)`。
- [ ] 运行 `pnpm test --run src/features/forms/FormDesigner.test.tsx src/form-engine`，确认设计器和渲染器缺失导致失败。
- [ ] 实现左侧题型、中间题目、右侧属性的 Ant Design 布局；排序和复制修改 JSON，不依赖题目文案关联。属性变化走定义校验，提交与预览使用任务 6 引擎。接入任务 7 的草稿、发布、版本与暂停 API，不复制渲染逻辑。
- [ ] 运行相关测试、类型检查和构建；在浏览器实际检查属性面板、弹窗和长题目在正常桌面窗口中可使用。
- [ ] 提交本任务文件，提交说明：`功能：实现动态表单设计器和填写组件`。

### 任务 9：研究项目、成员与访视定义

**文件：** 新建 `backend/apps/studies/{models,selectors,services,serializers,api}.py`、研究/RLS/配额/复合外键迁移、`backend/tests/test_studies.py`；修改医生删除和表单删除服务；新建 `frontend/src/features/studies/{api.ts,StudiesPage.tsx,StudyDetail.tsx,StudyEditor.tsx,ProtocolEditor.tsx}`。

**接口：** 消费任务 2、3、5、7 的身份、配额、患者范围和表单版本。提供 `visible_studies(actor) -> QuerySet[Study]`、`create_study(actor, data: dict) -> Study`、`update_study(actor, study_id: UUID, data: dict, expected_revision: int) -> Study`、`set_study_state(actor, study_id: UUID, state: Literal['draft','active','paused','ended'], expected_revision: int) -> Study`、`delete_study/restore_study(actor, study_id: UUID, expected_revision: int) -> Study`、`set_study_members(actor, study_id: UUID, doctor_ids: list[UUID], expected_revision: int) -> Study`、`save_protocol(actor, study_id: UUID, stages: list[dict], expected_revision: int) -> Study`、`require_study_member(actor, study_id: UUID) -> Study`；API `/api/studies/`、`/{id}/members/`、`/protocol/`、`/start/`、`/pause/`、`/resume/`、`/end/`。阶段类型 `screening/baseline/followup/end`，绑定含 `form_version_id/respondent/required`，填写对象值为 `doctor/patient`。

- [ ] 写 `test_protocol_requires_one_baseline`：零或两次基线均 `assert response.status_code == 409`；筛选和结束各至多一次且分别首位、末位，基线偏移为 0，偏差非负、偏移非递减、至少一份必需表单，非法跨租户版本拒绝。研究成员只读流程、负责人和管理员可编辑；研究草稿和结束均占配额，跨租户 ID 不泄露内容。
- [ ] 运行 `uv run pytest tests/test_studies.py -q`，确认项目与流程接口缺失导致失败。
- [ ] 实现研究 CRUD、自动负责人成员关系、状态与阶段绑定，安装研究计数触发器。保护负责未结束研究的医生，保护被进行中/暂停研究引用的表单。前端用 Tabs、Table、Form 配置基本信息、成员和访视，表单选择固定版本 UUID。
- [ ] 运行以上测试和前端构建，验证未加入研究的医生不见项目，不因可读模板而获得研究权限。
- [ ] 提交本任务文件，提交说明：`功能：实现研究项目成员和访视配置`。

### 任务 10：受试者入组与访视实例

**文件：** 新建 `backend/apps/followups/{models,enrollments,schedule,selectors,serializers,api}.py`、入组/访视/RLS/复合约束迁移、`backend/tests/{test_enrollments,test_schedule}.py`；修改研究成员、患者负责关系、医生及患者删除服务。

**接口：** 消费任务 5 的 `visible_patients` 与任务 9 的 `require_study_member`，两者交集用于患者数据。提供 `add_subject(actor, study_id: UUID, patient_id: UUID, doctor_id: UUID, observation_code: str, key: str) -> Enrollment`、`confirm_enrollment(actor, enrollment_id: UUID, enrollment_code: str, enrolled_on: date, key: str) -> Enrollment`、`schedule_date(enrolled_on: date, offset_days: int) -> date`、`transfer_followup(actor, enrollment_id: UUID, doctor_id: UUID, expected_revision: int) -> Enrollment`、`visible_enrollments(actor) -> QuerySet[Enrollment]`、`visible_visits(actor) -> QuerySet[VisitInstance]`；API `/api/studies/{id}/subjects/`、`/api/enrollments/{id}/confirm/`、`/transfer/` 和 `/api/visits/`。访视状态为 `pending/completed/stopped`，`Enrollment.current_visit_id` 决定可填写阶段。

- [ ] 写 `test_confirmation_is_idempotent`：相同 key 两次确认 `assert first.id == second.id; assert visit_count == len(non_screening_stages)`；`assert enrollment.enrollment_code == '000001'`，研究内重复拒绝；同患者两研究不增加患者用量。写筛选未完成不能确认、没有筛选可直接确认、首条受试者锁定流程、成员不开放其他患者，以及跨月/闰日/上海午夜的日期测试。
- [ ] 运行 `uv run pytest tests/test_enrollments.py tests/test_schedule.py -q`，确认入组或生成逻辑缺失导致失败。
- [ ] 实现状态 `screening/awaiting_enrollment/following/completed/stopped`，同患者同研究始终唯一。加入及确认锁定研究/入组行，冻结流程，绑定旧版本，计算相对入组日期的时间窗口；筛选窗口相对加入日期。转移职责后才允许移除成员或负责关系，患者存在未停止随访时不能删除。
- [ ] 运行以上测试，使用独立连接验证并发确认不重复；校验研究/患者/医生/阶段关联都同租户，医生同时是成员与患者负责医生。
- [ ] 提交本任务文件，提交说明：`功能：实现患者入组和访视日程生成`。

### 任务 11：答案、修订、访视完成与停止

**文件：** 新建 `backend/apps/followups/{answers,transitions}.py`、答案与修订模型迁移、`backend/tests/{test_answers,test_transitions}.py`；修改跟随访 API 与序列化器。

**接口：** 消费任务 6 的 `evaluate_answers`、任务 10 的可见访视和当前阶段、任务 3 的幂等和审计。提供 `save_answer_draft(actor, visit_id: UUID, binding_id: UUID, answers: dict, expected_revision: int) -> Answer`、`submit_answer(actor, visit_id: UUID, binding_id: UUID, answers: dict, key: str) -> Answer`、`revise_answer(actor, answer_id: UUID, answers: dict, reason: str, expected_revision: int) -> Answer`、`complete_visit(actor, visit_id: UUID, key: str) -> VisitInstance`、`stop_followup(actor, enrollment_id: UUID, stop_type: str, reason: str, key: str) -> Enrollment`。尚无答案时草稿 `expected_revision=0`，首次保存产生 revision 1；状态为 `draft/submitted`。API `/api/visits/{id}/answers/`、`/complete/`、`/api/answers/{id}/revise/`、`/api/enrollments/{id}/stop/`。

- [ ] 写 `test_completed_visit_answers_are_read_only`：`assert revise_response.status_code == 409`；`test_submission_retry_does_not_overwrite_answer`：`assert retried.id == original.id; assert retried.answers == original.answers`；`test_required_hidden_field_does_not_block_completion`：`assert visit.status == 'completed'`。修订必须有原因且保留原答案，患者表单记录代录人；暂停研究/表单拒绝写入，停止后不恢复，最后阶段完成使受试者 completed。
- [ ] 运行 `uv run pytest tests/test_answers.py tests/test_transitions.py -q`，确认填写与转换服务缺失导致失败。
- [ ] 实现答案绑定的唯一性和同租户、同访视定义、同版本复合约束，正式提交调用任务 6 引擎。幂等回执在当前数据授权通过后使用；修订号避免覆盖。完成访视必须所有 required 绑定已提交，筛选完成后仍需手动确认入组；完成后开启下阶段，停止时冻结未完成访视和历史答案。
- [ ] 运行以上测试，补充独立连接的重复提交和并发完成；API 不能绕过当前阶段限制或编辑已完成/停止/结束数据。
- [ ] 提交本任务文件，提交说明：`功能：实现答案填写修订和访视状态流转`。

### 任务 12：授权 Excel 导出与修订查看

**文件：** 新建 `backend/apps/followups/{exports,history}.py`、`backend/tests/test_exports.py`；修改答案和研究 API。

**接口：** `export_answers(actor, study_id: UUID | None = None, answer_id: UUID | None = None) -> bytes`；`visible_answer_revisions(actor, answer_id) -> QuerySet[AnswerRevision]`；API `/api/studies/{id}/export/`、`/api/answers/{id}/export/`、`/revisions/`。导出只允许指定一份答案或一个研究，使用同一套可见范围。

- [ ] 写 `test_doctor_export_excludes_other_patients` 和职责撤销后旧回执/旧下载请求拒绝的测试；将 `=SUM(1,2)` 等值读回，断言 `cell.data_type == 's'`；空研究仍有合法工作表，重复长标题断言表名唯一且长度不超过 31；两个版本分表、零值与空值不混淆。
- [ ] 运行 `uv run pytest tests/test_exports.py -q`，确认导出和修订查看缺失导致失败。
- [ ] 用 openpyxl 生成按版本分表的工作簿，固定信息列为档案编号、入组编号、访视、填写对象、录入人、提交时间，再按版本题目顺序写答案。选项显示原版本文案，多选按原顺序合并。所有用户文本按字符串写入，查询和文件生成在授权事务内完成，记录导出审计，不返回持久公开链接。
- [ ] 运行以上测试，重新读取工作簿校验单元格类型、编号和表名；访问答案历史时仍执行当前医生数据权限。
- [ ] 提交本任务文件，提交说明：`功能：实现研究答案导出和修订记录查看`。

### 任务 13：研究操作、访视日历与后台填写页面

**文件：** 新建 `frontend/src/features/followups/{api.ts,SubjectsTab.tsx,EnrollmentDialog.tsx,VisitCalendar.tsx,VisitDetail.tsx,AnswerEntry.tsx,AnswerHistory.tsx,followups.test.tsx}`、`frontend/src/features/dashboard/{DashboardPage.tsx,api.ts}`；新建 `backend/apps/followups/calendar.py`、`backend/apps/core/dashboard.py`、`backend/tests/{test_calendar,test_dashboard}.py`；修改研究详情与路由。

**接口：** `GET /api/calendar/?study_id=&from=&to=`、`GET /api/dashboard/` 只聚合当前 Actor 可见数据；页面调用任务 10 至 12 API，填写使用任务 8 的 `DynamicForm`，不建立另一套表单引擎。

- [ ] 写 `test_calendar_uses_window_end_and_current_permissions`：`assert overdue['color'] == 'red'; assert pending['color'] == 'yellow'; assert completed['color'] == 'blue'`；上海午夜边界正确，窗口外仍可录入。写 UI 测试：筛选到入组、两种填写对象、必填不足阻止完成、暂停后禁写、保存冲突保留输入；失去权限时清除对应缓存并显示对象不可用。
- [ ] 运行 `uv run pytest tests/test_calendar.py tests/test_dashboard.py -q` 与 `pnpm test --run src/features/followups/followups.test.tsx`，确认日历、统计及页面缺失时失败。
- [ ] 实现受试者列表/加入/确认/职责转交、访视详情、完成/停止、日历、代录提示、答案历史与下载。日历支持研究、负责医生和日期筛选以及今天待办列表；研究内容与患者范围分别过滤，工作台不显示不可见患者的统计。前端在 mutation 后失效对应列表缓存，并显示后端字段错误和状态错误。研究答案 Tab 提供可见答案列表及导出，表单目录展示引用研究并在暂停前提示受影响任务。
- [ ] 运行 `uv run pytest tests/test_calendar.py tests/test_dashboard.py -q`、`pnpm test --run src/features/followups`、类型检查与构建；浏览器实际检查 Calendar、Steps、长表单和表格横向滚动。
- [ ] 提交本任务文件，提交说明：`功能：完成研究入组访视和后台填写界面`。

### 任务 14：回收记录、审计及虚构演示数据

**文件：** 新建 `backend/apps/core/{audit_api,recycle_api}.py`、`backend/apps/tenants/management/commands/seed_demo.py`、`backend/tests/{test_recycle,test_audit,test_seed_demo}.py`；新建 `frontend/src/features/governance/{AuditPage,RecycleBinPage}.tsx`、`api.ts`；修改路由和各资源的删除恢复服务。

**接口：** `/api/audit/` 和 `/api/recycle/` 仅租户管理员访问；平台审计走控制面入口；各资源 `/restore/`。`uv run python manage.py seed_demo` 接收环境变量中的演示密码，不写真实资料，重复执行不重复生成记录。

- [ ] 写 `test_restore_preserves_stopped_state_and_checks_quota`：`assert enrollment.status == 'stopped'; assert study.status == 'ended'; assert over_quota_response.status_code == 409`；审计不可被医生或其他租户查询。`test_seed_demo_is_repeatable` 连续运行两次，`assert counts_after_first == counts_after_second`，覆盖两租户、管理员、不同负责范围医生、发布表单和研究。
- [ ] 运行 `uv run pytest tests/test_recycle.py tests/test_audit.py tests/test_seed_demo.py -q`，确认相关入口与初始化缺失导致失败。
- [ ] 提供删除记录与受限恢复操作，复用原模块服务，不另写免配额的恢复路径。实现审计列表，只含有授权的租户事件。通过真实业务服务生成虚构演示流程；至少包含无筛选及有筛选两种研究，包含表单显示/跳题和两名医生数据范围演示。
- [ ] 运行以上测试与前端构建；对照设计逐项检查所有创建、修改、分配、发布、入组、答案修订、完成、停止、删除恢复和导出均留痕。
- [ ] 提交本任务文件，提交说明：`功能：实现回收审计和演示数据初始化`。

### 任务 15：浏览器闭环验收、部署材料与最终评审

**文件：** 新建 `frontend/{playwright.config.ts,e2e/health-platform.spec.ts,e2e/isolation.spec.ts}`、`backend/Dockerfile`、`frontend/Dockerfile`、`infra/nginx.conf`、`scripts/{dev.sh,verify.sh}`、`README.md`、`.github/workflows/ci.yml`；修改 `compose.yaml` 与 `.env.example`。

**接口：** 提供一个可重复的本地启动路径、数据库所有者迁移步骤、演示初始化步骤与完整验证命令；生产启动 Django 用 WSGI 服务，Nginx 同源代理 `/api/`，不部署开发服务器或嵌入密钥。

- [ ] 写 Playwright 测试 `管理员完成研究闭环` 与 `跨租户及非负责医生不能访问患者`：管理员建患者和研究、发布表单、配置访视、筛选/确认、医生代录、提交/完成、日历查看及导出；使用第二租户和另一医生直接访问已知 ID，`expect(response.status()).toBe(404); await expect(page.getByText(restrictedPatientName)).toHaveCount(0)`。下载工作簿可打开，完成访视后编辑被拒绝。
- [ ] 运行 `pnpm exec playwright test`，确认未完成集成或运行配置缺失时失败；区分环境未就绪与业务断言失败。
- [ ] 实现构建/启动/迁移配置及 README，配置 CI 使用 PostgreSQL 和同样的受限角色；完善健康检查和演示登录说明。记录使用实际 Docker/PostgreSQL 的要求；当前沙箱不能访问 Docker socket 时，执行阶段按授权流程解决运行权限，不用假数据库交付。
- [ ] 运行后端全套 `uv run pytest -q`、`uv run python manage.py makemigrations --check --dry-run`、`uv run python manage.py check`；前端 `pnpm test --run`、`pnpm typecheck`、`pnpm build`、`pnpm exec playwright test`。所有结果通过后，只因新修改或新问题重复相关测试。
- [ ] 在真实浏览器检查管理员、医生和超级管理员页面及标准 Ant Design 组件；最后进行一次独立代码评审，修复经验证的反馈并运行受影响检查。提交交付材料，提交说明：`交付：完成全流程验收和启动部署说明`，随后按用户选定的方式交付，不自行上线托管。

## 覆盖核对

| 设计章节 | 实施任务 |
| --- | --- |
| 1、2：目标、架构、完整交付 | 1 至 15 |
| 3、4：身份、登录、角色、RLS、事务与导出隔离 | 2、3、4、5、9、10、11、12 |
| 5、6：实体关系、配额、软删除恢复 | 3、4、5、7、9、10、11、14 |
| 7：医生患者资料与搜索权限 | 4、5 |
| 8：研究状态、阶段、冻结、入组、推进、日历 | 9、10、11、13 |
| 9：题型、条件跳题、设计器、版本与暂停 | 6、7、8、11 |
| 10：代录、草稿提交、修改留痕、只读与 Excel | 11、12、13 |
| 11、12：标准后台、API 错误、修订与幂等 | 2、3、4、5、8、9、10、11、13、14 |
| 13：真实数据库、各角色演示、全流程验证、启动材料 | 1、2、4、6、12、14、15 |

## 执行方法与评审

建议由当前代理在本会话连续实施（`superpowers:executing-plans`）：各任务共享租户上下文、配额、表单协议和状态接口，连续实现有利于保持一致；每个任务完成自己的测试，最后由独立评审者检查整个开发分支。

也可以选择子代理逐任务实施与逐任务评审（`superpowers:subagent-driven-development`），每个任务获得独立审查，代价是每次需要加载新上下文。

书面计划需由用户评审并选择执行方法后开始产品代码、安装产品依赖或创建执行工作区。工作区隔离在实施阶段按 `superpowers:using-git-worktrees` 执行，不能在计划阶段默认创建。

## 技术兼容性依据

- [Django 5.2 LTS 与 Python 支持](https://docs.djangoproject.com/en/5.2/releases/5.2/)。
- [DRF 3.16 对 Django 5.2 的支持](https://www.django-rest-framework.org/community/3.16-announcement/)。
- [Ant Design 6 的 React 和图标库要求](https://ant.design/docs/react/migration-v6/)。
- [Vite 7 的 Node.js 与 Vitest 要求](https://vite.dev/blog/announcing-vite7)。
