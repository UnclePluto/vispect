# 手机号统一登录与多机构切换实施计划

> **执行代理须知：** 必须使用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` 逐任务实施。延续用户已选的当前会话连续实施方式，最后进行一次独立全分支评审。步骤使用 `- [ ]` 跟踪；本计划须经用户审阅确认后才开始产品代码、依赖或数据库操作。

**目标：** 将机构标识／用户名登录改为统一手机号密码登录，支持登录后选择机构、顶部切换机构和各机构独立角色，并保留历史归属及数据隔离。

**架构：** 新增控制面 LoginIdentity 与登录会话上下文，现有 Account 保留为机构／平台操作身份。临床业务继续使用原 Account ID 与 FORCE RLS；身份建立采用最小权限数据库函数，切换与业务请求通过稳定会话标识的数据库锁和版本令牌协调。

**技术栈：** 沿用已锁定的 Django 5.2／DRF、PostgreSQL 17、React／TypeScript／Ant Design 6、pytest、Vitest、Playwright；不为本功能升级依赖。

**设计依据：** [已确认书面设计](../specs/2026-10-15-phone-login-organization-switch-design.md)。用户于 2026-10-15 确认；实施时同时阅读设计与计划。

## 全局约束

- 一个手机号对应一个统一登录身份、一套密码，可以属于多个机构。
- 同一人在不同机构可以有不同角色；权限按当前机构独立配置。
- 机构管理员添加已经注册的手机号时，直接建立本机构成员关系，不需要邀请确认，也不改变原密码。
- 机构管理员只能管理本机构成员，不能重置统一登录密码或修改其他机构的成员关系。
- 统一密码由本人修改或超级管理员重置；切换机构不能绕过原有数据隔离和医生负责关系。
- 用户可见的“租户”文案统一改为“机构”；内部 `tenant_id` 和现有数据库表名继续使用。
- 登录手机号接受中国大陆 11 位号码及 `+86`／`0086` 等价输入，规范化为 `+86` 加 11 位号码；本地号码匹配 `1[3-9][0-9]{9}`。
- 保留现有至少 12 位密码规则、HttpOnly 会话 Cookie、CSRF、机构 RLS、复合外键、配额与审计；运行账号无 SUPERUSER／BYPASSRLS，也不是临床表所有者。
- 保留 Account、Doctor、业务记录和审计 ID；不清空业务库或删除数据库卷，不按姓名或未经确认的联系方式自动合并。
- 只有一个可用空间时直接进入；多个时先选择；首次改密先于空间选择；无可用空间时不进入业务。
- 所有业务查询、写入和下载携带发起时的空间令牌；令牌仅作一致性检查，授权机构来自服务端。
- 切换成功前等待已获准旧写入结束；等待中的旧操作重新检查令牌，不能在新机构落地。
- 所有界面、错误说明与提交说明使用简体中文；保留已交付的研究、表单及独立“＋”选项按钮。

## 评审重点

1. 两个机构同时新增同一规范化手机号：一个身份、两份合法成员关系，不能用第二份初始密码覆盖第一份。测试归属任务 1、5。
2. 控制面／业务面分别提交的假原子性：额度、成员、医生或审计失败后，不留下本次新建身份或半份成员。测试归属任务 5、6。
3. 旧标签页、等待锁的请求与迟到下载：切换后不能把 A 的操作写到 B，也不能显示或下载旧响应。测试归属任务 4、7、10。
4. 相同手机号对应不同旧密码／成员启用状态：主账号密码选择明确，成员停用不扩散，迁移冲突整体回滚并保留历史归属。测试归属任务 2、6。
5. 平台身份与机构身份共存、成员撤销及管理员更换：平台权限不叠加到机构，失去 A 不影响 B，换人不改写历史操作者。测试归属任务 3、6、9、10。

## 文件边界

路径相对仓库 `/Users/nick/my_dev/workout/Vispect`；任务中 accounts／core／doctors／tenants 前缀均位于 backend/apps/，frontend 路径以其根为准。新增模块按职责分开，避免继续把身份、切换和全局管理全部堆入现有 services.py／api.py。

| 路径 | 职责 |
| --- | --- |
| `backend/apps/accounts/{models.py,phone.py,identity_store.py,migrations/}` | 全局身份、手机号、受限身份函数与元数据投影 |
| `backend/apps/accounts/{migration_mapping.py,management/commands/migrate_login_identities.py}` | 显式旧账号映射的预检／原子应用 |
| `backend/apps/accounts/{principal.py,session_context.py,workspaces.py,auth_api.py}` | 统一认证、会话上下文、选择／切换、密码和响应协议 |
| `backend/apps/core/{middleware.py,workspace_lock.py,permissions.py}` | 每次请求的空间核验、锁和授权 |
| `backend/apps/accounts/{member_lookup.py,platform_services.py,platform_api.py}` | 受限手机号探测与平台全局账号管理 |
| `backend/apps/{doctors,tenants}/{services.py,serializers.py,api.py}` | 手机号成员创建及机构管理员配置 |
| `frontend/src/{api,features/auth,app}/` | 认证状态机、选择页、顶部选择器、请求／下载与广播 |
| `frontend/src/features/auth/WorkspaceChangesProvider.tsx` | 机构切换前未保存内容登记与确认 |
| `frontend/src/features/{doctors,tenants,accounts}/` | 手机号成员管理、机构及全局账号页面 |
| `backend/tests/`、`frontend/src/**/*.test.tsx`、`frontend/e2e/` | 数据库、权限、并发、组件和真实浏览器验收 |
| `scripts/`、`README.md`、`docs/delivery/` | 演示升级、启动、回归命令和验收记录 |

## 固定接口与实施衔接

- `LoginIdentityRef = {id: UUID, phone: str}`，仅含身份引用，不含密码或其他机构元数据。
- 保留 `Actor(account_id, tenant_id, role, doctor_id)`；account_id 始终指当前机构／平台 Account，不能改为 LoginIdentity ID。
- `AccountPayload = {id, login_phone, name, enabled, revision}` 用于管理员配置；`ActorPayload` 沿用业务操作身份字段 account_id／tenant_id／role／doctor_id／name／tenant，不用于保存密码。
- `MigrationReport = {valid, groups, conflicts, unmapped_account_ids, applied_groups, skipped_groups}`；conflicts 每项含 code、account_ids、message。无效映射应用前拒绝，预检命令退出码为 1，不打印密码。
- `Principal(user_id: UUID, context_id: UUID)` 表示统一登录身份；尚无活动空间时有 Principal、无 Actor。
- `WorkspaceOption = {account_id, tenant: {id, name, slug} | null, role, name}`。平台项 tenant 为 null、role 为 platform_admin；重名机构显示 name 加 slug。
- `AuthEnvelope = {user: {id, phone, name, must_change_password}, actor: ActorPayload | null, workspaces: WorkspaceOption[], workspace_token: string, next: 'change_password' | 'choose_workspace' | 'no_workspace' | 'ready'}`。未登录 `/me/` 返回 401，不伪造空的已登录响应。
- 新建 `LoginSessionContext` 作为 Django 服务端会话的扩展：id（稳定 UUID）、identity_id、active_account_id（可空）、workspace_token（随机 UUID）、revoked、expires_at。Django session 保存 identity ID、认证哈希及 context ID；活动空间和令牌以此表为唯一权威，避免 Django 响应末尾保存旧 session 时覆盖刚切换的新空间。该表只有控制面直接读写。
- `X-Workspace-Token` 是业务请求的必需一致性令牌，不能把任意 tenant_id 请求头作为授权依据。认证接口、健康检查豁免；平台业务 API 同样检查。过期令牌返回 `workspace_changed`（409），当前成员失效返回 `workspace_unavailable`（409），统一凭据失效返回 401。
- 新增 `/api/auth/login/`、`/workspaces/`、`/switch-workspace/`；保留 csrf、me、logout、change-password。me／workspaces／改密依赖 Principal，业务接口依赖 Actor。
- 开发过渡期间旧登录视图可保留用于尚未更新的测试与旧前端；任务 9 必须移除旧入口和旧 session 解析，最终版本不存在用户名或旧 Account 密码旁路。最终统一会话中间件不得回退旧格式。
- 每个任务先运行新增测试看到预期失败，再实施、运行列出的相关检查并中文提交；最终任务执行完整 `scripts/verify.sh`。不对中途尚未切换的旧 UI 声称新功能已交付。

### Task 1: 全局身份、手机号与最小数据库权限

**文件：** 新建 `backend/apps/accounts/{phone.py,identity_store.py}`、`backend/tests/test_login_identity.py`；修改 `accounts/models.py`，新增 `accounts/migrations/{0004_login_identity.py,0005_identity_security.py}`；在 `backend/tests/world.py` 增加 `bind_identity(account, phone, password=None) -> LoginIdentity` 测试辅助方法，不改变既有业务工厂的用途。

**接口：** `normalize_phone(raw: str) -> str`；`ensure_identity(actor: Actor, phone: str, initial_password: str | None, name: str, *, using: str) -> (LoginIdentityRef, bool)`；`probe_phone(actor, phone) -> {phone, registered}`；`member_phone(actor, account_id) -> str`；`identity_workspaces(identity_id: UUID) -> list[WorkspaceOption]`。后四者通过受限 SQL 函数访问，不使业务角色获得全局表 SELECT 权限。

- [x] 写 `test_phone_normalization`、`test_identity_database_privileges`、`test_member_projection_scope` 测试。关键断言：`normalize_phone(' 0086 138-0000-0001 ') == '+8613800000001'`；`+86` 等价输入得到同一身份；非法号码 400；app 直接 SELECT 密码列报 InsufficientPrivilege；投影不含 password；无当前机构／普通医生不能探测或建立全局身份。
- [x] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_login_identity.py -q`。预期：缺少模型／函数导致失败；环境连接失败不算预期红灯。
- [x] 新增 LoginIdentity（姓名、规范化 phone 唯一、密码、is_active、must_change_password、revision、created_at）、可空 Account.identity_id 及同身份同机构唯一约束、平台身份部分唯一约束；新增 LoginSessionContext。成员上下文中的 active_account 必须属于该 identity，以数据库触发器验证；历史空 identity 暂留，最终写入约束在任务 9 开启。
- [x] 实现限定函数：`vispect_ensure_identity(actor_id uuid, phone text, password_hash text, name text)` 返回 id／created；`vispect_probe_identity(actor_id uuid, phone text)` 仅返回 registered；`vispect_member_phone(actor_id uuid, account_id uuid)` 仅返回当前机构获准成员的手机号；`vispect_identity_workspaces(identity_id uuid)` 仅向 control 返回该身份成员元数据。固定 search_path、PUBLIC 无执行权限、app／control 分别最小授予；复用已有身份不更新任何凭据。注意 SECURITY DEFINER 本身不能绕过 FORCE RLS：为 owner 的成员投影增加仅限 accounts_account、identity_id 匹配事务身份变量的读取策略；成员投影函数和会话成员归属校验触发器临时设置该变量，并在正常／异常路径恢复原值。此策略不授予 app／control，也不扩展到临床表；投影函数仅 control 可执行，identity_id 只从已认证 Principal 取得。内部 username 为不承载登录意义的唯一生成值。
- [x] 同一手机号码并发插入通过唯一约束和冲突重读收敛；凭据加密在 Python 使用 Django，数据库不接收明文密码。函数由 caller 事务调用，不自行提交，也不通过另一个连接重试；避免“先查不存在，再插入”的竞争覆盖。
- [x] 重跑本任务测试并检查迁移漂移，预期全部通过。提交：`基础：增加统一手机号身份和受限成员查询`。

### Task 2: 可预检、原子及幂等的旧账号迁移

**文件：** 新建 `backend/apps/accounts/migration_mapping.py`、`backend/apps/accounts/management/commands/migrate_login_identities.py`、`backend/tests/test_identity_migration.py`。

**接口：** `preflight_mapping(groups: list[dict]) -> MigrationReport`；`apply_mapping(groups: list[dict]) -> MigrationReport`。命令 `migrate_login_identities --mapping PATH` 默认只预检，显式 `--apply` 应用。JSON 为 `{"groups":[{"phone":"13800000001","primary_account_id":"UUID","account_ids":["UUID"],"enabled":true}]}`；每组主账号必须出现在本组，同一账号只出现一次。

- [ ] 写 `test_mapping_preserves_history_and_primary_password`，断言不同机构的两个旧账号可合并为同一 identity，但 Account／Doctor／答案／审计 ID 不变；两个旧密码不同时只保留显式 primary 的哈希；`apply_mapping` 重跑不重置密码。旧成员 is_active 各自保留，不据此合成全局停用。
- [ ] 增加 `test_mapping_conflict_rolls_back_every_group` 和 `test_mapping_rerun_preserves_new_password`：第二组同机构重复身份、重复映射、显式 enabled 矛盾、主账号缺失、非法手机号，预检报具体冲突且 `identity_count_after == identity_count_before`。遗漏账号出现在 `unmapped_account_ids`；不自动按姓名／联系方式合并。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_identity_migration.py -q`。预期缺少命令／服务时失败。
- [ ] 使用 migration 连接、显式机构上下文和一个整体事务应用映射；复制主账号密码哈希，不打印哈希／明文；任一绑定前要求合法预检。绑定成功设置旧密码不可用；组内任一旧首次改密标记为 true 时，新身份要求改密。已迁移组验证映射一致后跳过，不覆盖现有身份状态或新密码。
- [ ] 运行本任务测试，预期全部通过。提交：`迁移：增加统一身份映射预检和原子升级`。此任务只验证独立测试数据，不对运行业务库执行真实映射。

### Task 3: 统一登录、密码与服务端会话状态

**文件：** 新建 `accounts/{principal.py,session_context.py,auth_api.py}`、`backend/tests/test_phone_auth.py`；修改 `accounts/{api.py,services.py,serializers.py}`、`core/{middleware.py,permissions.py}`、`config/urls.py`、`backend/tests/{world.py,test_auth.py}` 及调用 `/me/` 的既有测试。

**接口：** `authenticate_phone(phone, password) -> LoginIdentity`；`start_login(request, identity) -> AuthEnvelope`；`get_principal(request) -> Principal`；`auth_envelope(request) -> AuthEnvelope`；`change_identity_password(request, old_password, new_password) -> AuthEnvelope`。LoginSessionContext 的稳定 id 不随 Django session key 轮换改变；有效期沿用 Django SESSION_COOKIE_AGE。

- [ ] 写 `test_login_next_state`、`test_phone_login_requires_csrf` 和 `test_invalid_credentials_do_not_reveal_memberships`：正确手机号免机构登录；未知手机／错误密码统一 401 且消息为“手机号或密码不正确”；无 CSRF 登录 403；一个空间 next=ready，多个 next=choose_workspace，零个 next=no_workspace；首次改密优先 next=change_password、actor=null。
- [ ] 写 `test_identity_password_revokes_other_sessions`、`test_global_deactivation` 及 `test_workspace_roles_do_not_union`：A 管理员＋B 医生不产生权限并集；本人改密仅保留当前上下文登录，其他会话 401；重复初始密码不接受；全局停用与过期上下文拒绝。me 返回本人 AuthEnvelope，未选空间业务接口返回 workspace_required（403）。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_phone_auth.py -q`，预期新入口或新状态尚未实现而失败。
- [ ] 实现统一凭据读取、Django session 轮换、上下文建立和 PrincipalPermission；world 默认工厂改为先建立 identity 再保存绑定 Account，以满足最终新成员约束；历史空身份样例只通过受控 migration 测试工厂建立。不得对登录手机号存在性使用不同错误消息。修改现有 auth API 响应与测试，world 为默认账号绑定明确手机号，新增 `phone_for(tenant, role)`；旧测试仍检查原安全意图，不靠删除权限断言通过。尚未使用新前端的旧入口仅作过渡，登记任务 9 的移除点。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_phone_auth.py backend/tests/test_auth.py -q`，预期全部通过。提交：`认证：实现手机号登录和统一密码会话`。

### Task 4: 空间切换、请求令牌与数据库屏障

**文件：** 新建 `core/workspace_lock.py`、`accounts/workspaces.py`、`backend/tests/test_workspace_switch.py`；修改 `core/{middleware.py,context.py}`、`accounts/auth_api.py`、`core/idempotency.py`、`backend/tests/world.py`。

**接口：** `lock_workspace_context(context_id: UUID, *, using: str, exclusive: bool) -> None`（调用者已在事务内）；`switch_workspace(request, account_id: UUID, expected_token: str) -> AuthEnvelope`；`workspace_transaction(request, *, using: str) -> ContextManager[Actor]`；GET workspaces 返回本人列表，POST switch 接收 `{account_id, workspace_token}`。

- [ ] 写 `test_switch_requires_owned_active_workspace`、`test_stale_workspace_token_rejected`、`test_member_revocation_keeps_other_workspace`：本人 A→B 返回新 token、正确医生 Actor；切换到他人成员返回 404；平台身份不能伪造机构成员；缺失或过期业务令牌 409，伪造 X-Tenant-ID 不改变当前机构。停用 A 成员／机构后返回 workspace_unavailable，统一登录仍有效、B 可选择。
- [ ] 用两个独立连接和线程事件写 `test_switch_waits_for_authorized_write`、`test_waiting_old_write_revalidates_token`、`test_concurrent_switch_only_one_wins`：A 写入持共享锁时，B 切换未完成；释放后切换完成。另一个携带旧 token 的请求在切换锁后等待，得到 409，断言 B 中该对象数量不变。并发同旧 token 两次切换只能成功一次。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_workspace_switch.py -q`，预期缺少令牌核验／锁或切换入口时失败；不能用固定 sleep 推断竞争结果。
- [ ] 锁键固定为 `sha256(b'vispect.workspace:' + context_id.bytes)[:8]` 的有符号 64 位值；业务请求在其 default／control 事务内持共享事务锁，切换在 control 事务内持排他事务锁。获得锁后从控制面重新读取权威上下文和成员状态，再设置临床事务 RLS；不使用请求开始时缓存的旧活动成员。所有别名指向同一物理数据库的锁空间。
- [ ] 切换和成员撤销清空上下文需更新 token 并原子提交；事务之外不得延迟读取导出数据。Django session 中只引用稳定 context ID，避免响应末尾重存旧 Actor。幂等回执仍按当前 Account 和授权范围读取；旧 token 在读回执前拒绝。
- [ ] world.login 设置 APIClient 的 `HTTP_X_WORKSPACE_TOKEN`，业务测试仍可通过；增加显式 stale-token client，不让测试辅助方法自动刷新从而掩盖旧标签页问题。运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_workspace_switch.py backend/tests/test_rls.py backend/tests/test_idempotency.py -q`，预期通过。提交：`权限：增加机构切换令牌与会话事务屏障`。

### Task 5: 手机号医生成员管理与事务回滚

**文件：** 新建 `accounts/member_lookup.py`、`backend/tests/test_phone_members.py`；修改 `doctors/{services.py,serializers.py,api.py}`、`accounts/identity_store.py`、`backend/tests/{world.py,test_doctors.py,test_quota.py}`、`config/urls.py`。

**接口：** `probe_login_phone(actor, phone) -> {phone, registered}`；POST `/api/members/phone-status/` 只供机构／平台管理员精确探测；`create_doctor(actor, data)` 改用 `login_phone`、新身份的 `initial_password`、姓名及原资料字段。返回 payload 增加 login_phone；原 phone 是联系方式，不作为身份绑定输入。

- [ ] 写 `test_add_existing_phone_preserves_global_credentials` 及 `test_duplicate_or_deleted_member_not_recreated`：全局密码哈希、A 成员角色／状态和全局修订号不变；只增加 B 的医生档案与额度，医生不能调用探测接口，结果不含其他机构元数据。重复成员明确冲突；软删除档案提示使用恢复，不新建第二份。
- [ ] 写 `test_concurrent_phone_provisioning` 和 `test_member_failure_rolls_back_identity_and_doctor`：两机构同时创建相同手机、不同初始密码，只有一个身份，第二个调用不覆盖成功者密码；并发测试在 ensure_identity 执行前用线程事件同步，在固定顺序锁定号码后验证收敛，不用耗时推断。满额、Doctor 创建失败、审计失败后本次新身份／Account／Doctor 均不保留。测试使用真实数据库独立连接。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_phone_members.py -q`，预期用户名旧接口／缺少原子性导致失败。
- [ ] 保留 `mutate_with_quota`，在同一 default 事务里调用任务 1 ensure_identity、建立 Account、Doctor 和审计；现有手机号忽略而不应用 initial_password，未注册手机号缺密码返回 400。手机号归一与最终写入判断不能只依赖探测结果。账号 is_active 仅影响成员；删除／恢复仍遵守原保护和额度规则。
- [ ] 拒绝机构管理员在普通医生接口修改 identity_id、role、全局密码或登录手机号；普通医生的资料权限保持原状。更新 world.doctor 为新字段，新增手机使用唯一测试计数，不随机碰撞真实业务库。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_phone_members.py backend/tests/test_doctors.py backend/tests/test_quota.py backend/tests/test_recycle.py -q`，预期通过。提交：`成员：通过手机号建立独立机构医生身份`。

### Task 6: 机构管理员更换与平台全局账号管理

**文件：** 新建 `accounts/{platform_services.py,platform_api.py}`、`backend/tests/test_global_accounts.py`；修改 `tenants/{services.py,serializers.py,api.py}`、`config/urls.py`、`backend/tests/test_tenants.py`。

**接口：** 机构创建改用 `admin_phone` 与仅新身份需要的 `admin_initial_password`。`configure_administrator(actor, tenant_id, data)` 以 `expected_tenant_revision` 和 `expected_admin_id` 防并发，后者在没有启用管理员时为 null；手机号不同即更换操作者，不改绑旧 Account。管理员查询返回 `{tenant_revision, administrator: AccountPayload | null}`，每次配置都递增机构与所改成员的修订号，不把成员修订号与机构修订号混用。新增 GET `/api/platform/accounts/?phone=...` 精确查询，POST `/api/platform/accounts/{id}/enabled/`（enabled、expected_revision），POST `/api/platform/accounts/{id}/reset-password/`（new_password、expected_revision）；缺失或非法 phone 返回 400，不返回全局账号大全；前端首次进入不发查询，填写合法号码后才请求。

- [ ] 写 `test_global_account_admin_permissions`、`test_platform_reset_revokes_all_sessions` 和 `test_global_revision_conflict`：机构管理员／医生请求全局管理接口 403；平台重置撤销全部旧会话、首次改密为 true，临床请求仍 403；全局停用影响所有机构，成员停用只影响当前机构；旧 revision 返回 409。
- [ ] 写 `test_replace_admin_preserves_historical_actor`、`test_existing_doctor_not_promoted_implicitly` 和 `test_create_organization_rolls_back_identity`：新旧手机号不同，当前管理员 Account ID 改变，旧历史 AuditEvent.actor_id 不变且仍指旧 identity；旧关系停用，其他机构关系不变；目标已是本机构医生则冲突，不能隐式提权。创建机构中途失败时新身份／成员／机构／配额整体回滚。
- [ ] 运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_global_accounts.py -q`，预期新接口／旧管理员更新方式导致失败。
- [ ] 平台操作保持一个 control 事务，使用受限身份函数关联凭据；事务内锁定机构和当前管理员，唯一选择当前启用管理员，不能继续按最早历史管理员行决定当前人选。更换时创建或复用目标管理员关系，并停用旧关系；如果没有启用管理员，明确返回待配置状态，使用机构 revision 及 expected_admin_id=null 控制补配。
- [ ] 全局重置／启用审计使用当前平台 Account，隐藏密码和认证哈希，不把 LoginIdentity ID 当作临床审计 actor。运行 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_global_accounts.py backend/tests/test_tenants.py backend/tests/test_audit.py -q`，预期通过。提交：`平台：管理全局账号并保留管理员历史身份`。

### Task 7: 前端认证状态机、请求封装与机构选择

**文件：** 新建 `frontend/src/features/auth/{WorkspaceSelectPage.tsx,WorkspaceSwitcher.tsx}`；修改 `api/{types.ts,client.ts}`、`features/auth/{AuthProvider.tsx,api.ts,LoginPage.tsx,ChangePasswordPage.tsx,auth.test.tsx}`、`app/{router.tsx,AdminLayout.tsx}`。

**接口：** 前端使用固定 AuthEnvelope；AuthProvider 导出 user、actor、next、workspaces、workspaceToken、`login({phone,password})`、`switchWorkspace(accountId)`、logout、refreshIdentity。路由 `/select-workspace` 为 Principal 可访问，无 Actor 时不能进入业务路由。顶部和选择页调用同一切换方法。

- [ ] 写“手机号登录按 next 导航”“选择机构更新角色与菜单”组件测试：登录没有用户名／机构标识；三个 next 分别进入改密／选择／首页；单机构自动进入；多机构选项含角色和重名辅助编号。切换 A 管理员→B 医生后更新菜单，平台项不产生机构权限。
- [ ] 写“等待 CSRF 时切换取消旧写入”“迟到响应不能覆盖新空间”“空间撤销不退出统一身份”测试：API 与 download 捕获发起时 token；等待 CSRF 时发生切换则旧写入取消；旧 401／旧下载响应不能覆盖新身份；workspace_changed 刷新服务端上下文，workspace_unavailable 保留 user 并进入选择页；不能只改 localStorage 获得 Actor。
- [ ] 运行 `pnpm --dir frontend test --run src/features/auth/auth.test.tsx`，预期新页面／接口缺失或旧登录表单断言失败。
- [ ] 实现手机号登录、选择页和 Ant Design Select；登录成功后根据 next 导航。请求封装统一附加 `X-Workspace-Token`，认证恢复请求不附错误业务令牌；切换前增加请求代次并取消查询，成功后清空缓存、替换 Actor 并返回首页。失败先刷新权威上下文：未变则保留原空间，已变则应用新空间，不能对不确定网络结果盲目保留旧 Actor。
- [ ] BroadcastChannel 只发送“空间已变化”的事件，不在广播中传递密码或可信授权数据；接收时先阻止旧操作并从 me 重新加载。不依赖广播保证服务端安全。以 workspace_token 为业务 Outlet 的 key，使旧机构局部状态卸载。
- [ ] 运行上述测试、`pnpm --dir frontend typecheck`、`pnpm --dir frontend build`，预期通过。提交：`界面：统一手机号登录和顶部机构选择`。

### Task 8: 未保存内容登记及机构切换确认

**文件：** 新建 `features/auth/{WorkspaceChangesProvider.tsx,workspaceChanges.test.tsx}`；修改 `app/App.tsx`、AuthProvider、`features/forms/FormDesigner.tsx`、`features/patients/PatientEditor.tsx`、`features/doctors/DoctorEditor.tsx`、`features/studies/{StudyEditor.tsx,StudyDetail.tsx,ProtocolEditor.tsx}`、`features/followups/{EnrollmentDialog.tsx,AnswerEntry.tsx}`、`form-engine/DynamicForm.tsx`。

**接口：** `useWorkspaceDirty(key: string, dirty: boolean) -> void`；`useWorkspaceChanges() -> {confirmChange(): Promise<boolean>, clear(): void}`。Provider 在 Ant Design App 内、AuthProvider 外，使切换服务可请求确认；DynamicForm 新增可选 `onDirtyChange(dirty: boolean)`，只报告相对于当前已保存答案的修改，不改变题目规则或保存行为。

- [ ] 写“未保存时取消切换保留输入”“保存成功清除登记，冲突保留登记”测试：未保存表单／弹窗／答案时切换出现确认，取消时没有调用切换 API、输入和当前空间不变；确认后仅一次调用，成功后登记与旧输入消失；保存成功清 dirty，冲突和保存失败保留 dirty。
- [ ] 增加“其他标签页切换后清理旧编辑内容”测试：当前页立即清旧数据并提示“机构已在其他页面切换，未保存内容未提交”，不以本页未保存确认阻止服务端已发生的切换，不自动提交草稿。
- [ ] 运行 `pnpm --dir frontend test --run src/features/auth/workspaceChanges.test.tsx`，预期缺少登记／确认导致失败。
- [ ] 为列出的编辑器接入登记，登记 key 包含业务记录／题目或绑定 ID，组件卸载自动注销；弹窗未修改不误报，保存新 revision 后重设基准。研究成员／流程继续保留编辑起点 revision；新增提示不能重新引入并发覆盖问题。
- [ ] 运行前端全套 `pnpm --dir frontend test --run` 和 build，预期通过，动态表单条件、跳题及独立“＋”选项按钮回归不变。提交：`交互：切换机构前保护未保存内容`。

### Task 9: 手机号管理界面、机构文案与旧入口退役

**文件：** 新建 `frontend/src/features/accounts/{GlobalAccountsPage.tsx,api.ts,accounts.test.tsx}`；修改 `features/{doctors,tenants}/` 的编辑器／列表／API／测试，AdminLayout、router，后端 auth 路由／中间件及 `accounts/migrations/0006_identity_cutover.py`，`backend/tests/test_auth.py`、已有 fixture 和成员测试。

**接口：** 新增前端 `/accounts` 平台专属页面；机构创建和管理员弹窗使用手机号、新用户初始密码、现有手机号保留原密码提示。探测状态失效时以保存响应为准，不依赖初始输入状态。

- [ ] 写“已注册手机不展示密码”“迟到手机号探测不覆盖新输入”“全局管理仅平台可见”测试：探测未注册手机号时显示初始密码，已注册时隐藏并清除旧密码输入，只显示保留原密码提示；手机号改动取消旧探测响应，不能把前一个手机号的 registered 状态套用到新号；编辑成员不能提交全局密码或任意 role。
- [ ] 写 `test_legacy_login_routes_removed`、`test_legacy_session_and_password_rejected`、`test_runtime_member_insert_requires_identity`：旧 tenant-login／platform-login 返回 404，旧 session 格式不能认证，旧 Account 密码不可用；非平台用户直接打开 accounts 页面和请求接口都被拒绝。新增 Account 缺 identity 的直接 INSERT 由 app／control 执行时被数据库拒绝，已有历史 null 行仍保留引用且不能登录；迁移测试仅由 migration 角色构造旧记录样例，不向运行角色提供绕过开关。
- [ ] 运行对应前端成员／平台测试及 `uv run --project backend --env-file .env --no-sync pytest backend/tests/test_auth.py -q`，预期旧入口仍存在或新界面缺失时失败。
- [ ] 实现全局账号精确查询、停用／启用、重置密码；密码不回显。成员启用与全局状态分开呈现。退役旧入口与临时旧 session 解析；新增 INSERT／identity 变更约束，禁止把已绑定 Account 改绑另一人，禁止为新成员省略 identity；允许管理迁移对历史 null 首次绑定。
- [ ] 更新用户可见文案：租户登录／管理／上限／工作空间改为机构相应称呼；内部路径／tenant_id 不重命名。检索 `rg -n '租户|用户名|重置密码' frontend/src backend/apps`，逐项检查：仅历史兼容字段或平台明确授权重置保留，机构端不可残留旧登录含义。
- [ ] 运行前端全套测试、类型／build 和完整后端 `uv run --project backend --env-file .env --no-sync pytest backend/tests -q`，预期通过。提交：`管理：完成手机号成员界面并退役旧登录`。

### Task 10: 演示升级、真实浏览器闭环与最终交付

**文件：** 修改 `backend/apps/tenants/management/commands/seed_demo.py`、`backend/tests/test_seed_demo.py`、`frontend/e2e/{helpers.ts,health-platform.spec.ts,isolation.spec.ts}`、`scripts/{e2e-server.py,verify.sh,dev.sh}`、README；新建 `frontend/e2e/workspace-switch.spec.ts`、`scripts/upgrade-demo-identities.py`、`docs/delivery/2026-10-15-手机号机构切换验收.md`。

**接口：** 纯虚构测试手机号固定：平台 `19900001000`；A 管理员兼 B doctor1 `19900001001`；B 管理员 `19900001002`；A doctor1 `19900001003`；A doctor2 `19900001004`；B doctor2 `19900001005`。仅本地演示使用，不声称号码已验证、不发送短信。密码来自 DEMO_PASSWORD；旧演示迁移同组选择 A 管理员为主账号并保留其当前密码。

- [ ] 写 `test_seed_phone_identities_is_repeatable`、`test_upgrade_existing_demo_keeps_password_and_ids`，以及 Playwright“跨机构不同角色切换”“旧标签页不能向新机构写入”用例，先运行并确认因用户名旧辅助或手机号种子未更新失败。保留原闭环的建患者、发布表单、筛选／确认、医生代录、完成只读、日历和合法 Excel 下载断言。
- [ ] 演示升级脚本只处理 seed_demo_complete 标记覆盖且用户名和机构符合明确映射的虚构账号；非匹配账号列为未映射，不自动绑定。默认预检，显式 --apply 才在业务库应用；脚本调用任务 2 原子命令，不重写临床数据或已迁移密码。已有演示标记不得使身份升级被整体跳过。
- [ ] 更新浏览器登录辅助：phone／password、首次改密、可选目标空间选择；API 调用及导出必须使用页面当时令牌，不偷偷刷新 stale-token 场景。E2E 固定清空 vispect_e2e_test，后端仅使用 vispect_test；新增全局表沿用 accounts_ 前缀，使隔离清理包含新表。
- [ ] 真实两标签页验收：同账号 A 管理员→B 医生，列表／菜单／导出改变；旧 A 标签页在无广播情况下提交／导出也被服务器拒绝；等待锁写入与切换顺序正确；用户不所属机构的已知 ID 仍不可访问。另测平台＋机构共存、成员停用仍能进入另一机构、取消未保存切换、旧响应不恢复旧数据。
- [ ] 运行 `scripts/verify.sh`，预期真实 PostgreSQL 后端全套、迁移无漂移、Django 检查、前端全套、typecheck／build、全部 Chromium 用例通过；失败日志保存本计划工作目录。只因新增变更或未解决问题重跑，不以旧结果声称新代码通过。
- [ ] 按 executing-plans 进行一次新上下文全分支只读评审，重点为本文五项评审重点；不复用此前首版的评审结论。对经验证的重要发现先补失败测试，再修复并完成绿色回归，记录取舍和暂缓项。
- [ ] 更新 README 的新登录方式、测试账号、迁移预检／应用步骤；实际业务库升级前保留可恢复的备份，先运行预检并确认只改预期演示身份。按用户已授权的本地平台更新容器；若预检发现真实未知账号或冲突，保留数据并报告，不用清空数据库解决。
- [ ] 用构建后的本地容器真实登录、切换机构和下载，确认常驻后端仍无迁移凭据；保存最终验收记录与实施决策。提交：`交付：完成手机号登录和多机构切换验收`。不自行推送、合并或上线托管。

## 覆盖核对与执行交接

| 设计章节 | 实施任务 |
| --- | --- |
| 1、2：目标、统一身份、保留机构操作身份 | 1、2、3、5、6 |
| 3：号码、密码、首次改密、会话撤销 | 1、3、6、7、9 |
| 4：登录、选择、切换、未保存提示 | 3、4、7、8、10 |
| 5：成员、机构管理员、全局账号管理 | 5、6、9、10 |
| 6：RLS、限定函数、原子性、成员与全局停用 | 1、3、4、5、6 |
| 7：令牌、数据库屏障、多标签页 | 3、4、7、8、10 |
| 8：API、前端边界、旧入口退役 | 3、4、5、6、7、8、9 |
| 9：旧数据映射、演示升级、历史归属 | 2、6、10 |
| 10、11：全量验收与评审重点 | 各任务回归及 10 |

本计划沿用当前会话连续实施（Native），不在每个任务重新派实现者；最后由一次独立评审提供第二视角。任务 1—6 形成认证与数据基础，7—9 完成前端和旧入口切换，10 完成真实数据库／浏览器／容器交付。书面计划确认前，仅保存并审阅文档，不创建新执行工作区或改变运行中的数据库。
