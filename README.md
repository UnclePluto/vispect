# 智观云健康管理平台

产品简称「智观云」，支持多机构独立空间。为兼容已有部署，数据库、角色、数据卷、环境变量和内部通信协议继续沿用 `vispect` 技术标识，不作为产品展示名称。

Django 5.2 / DRF、PostgreSQL 17、React / TypeScript / Ant Design 6。首版支持医生和患者档案、研究成员与访视配置、动态表单、筛选与入组、工作人员代录、答案修订、顺序访视、停止随访、Excel 导出、机构额度、回收记录和审计。

## 本地启动

准备 Docker Desktop、Python 3.12、uv、Node.js 24 和 pnpm 10.33。数据库使用真实 PostgreSQL，不支持 SQLite 替代。所有命令从仓库根目录执行。

```bash
python3 scripts/init-env.py
scripts/dev.sh
```

打开 http://127.0.0.1:5173 。脚本依次启动数据库、安装锁定依赖、用迁移账号执行迁移、初始化虚构演示数据，再启动前后端。按 Ctrl+C 结束开发服务；数据库卷保留。

首次创建 `.env` 会生成随机密码并设置文件权限 600。已有 `.env` 不会覆盖。已有配置的 `DEMO_PASSWORD` 为空时，请先设置不少于 12 位的密码，再运行初始化。

登录统一使用手机号和密码，无需填写机构标识。单个可用身份自动进入；多个机构先选择，进入后可在顶部下拉切换。同一手机号在各机构拥有独立角色。

| 测试手机号 | 身份 |
| --- | --- |
| `19900001000` | 平台管理员 |
| `19900001001` | 机构 A 管理员，同时是机构 B 医生 1 |
| `19900001002` | 机构 B 管理员 |
| `19900001003` | 机构 A 医生 1 |
| `19900001004` | 机构 A 医生 2 |
| `19900001005` | 机构 B 医生 2 |

这些号码仅是虚构演示标识，未验证、不发送短信。新环境初始密码来自 `.env` 的 `DEMO_PASSWORD`，首次登录须更换；升级现有环境沿用各主账号当前密码，不重置已修改密码。共享号码沿用原 A 管理员密码。重复初始化和升级不重复生成记录或覆盖密码。

机构管理员可直接把已有手机号加入本机构，保留全局密码；成员停用只影响本机构。只有本人和平台管理员能修改全局密码；平台重置或全局停用撤销既有会话。切换前有未保存内容会确认，取消保留输入；其他页面已切换时，本页旧操作会被拒绝并清理旧内容。

需要分别启动时：


```bash
docker compose up -d db
uv sync --project backend --frozen
pnpm --dir frontend install --frozen-lockfile
VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python backend/manage.py migrate --database migration --noinput
uv run --project backend --env-file .env --no-sync python backend/manage.py seed_demo
uv run --project backend --env-file .env --no-sync python scripts/runtime-server.py
# 另一个终端
pnpm --dir frontend dev
```

## 旧环境身份升级

先备份现有数据库，保留数据库卷。结构迁移后，旧 Account 保留原 ID 和历史引用，但旧用户名入口退役；需要显式绑定手机号才能登录。

```bash
# 先创建私有备份目录，切勿把数据库备份提交到仓库
umask 077
mkdir -p .local/backups
docker compose exec -T db pg_dump -U postgres -Fc vispect > .local/backups/vispect-before-identity.dump
VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python backend/manage.py migrate --database migration --noinput
# 默认预检，不写数据
VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python scripts/upgrade-demo-identities.py
# 确认只有预期演示成员、无冲突或未映射旧账号后显式应用
VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python scripts/upgrade-demo-identities.py --apply
```

演示升级只接受 `demo-a`、`demo-b` 的完整初始化标记、固定旧管理员／医生账号及平台账号。其他旧账号不会被分配虚构号码；应用前需人工提供明确映射。业务数据和审计操作者保持原 ID，已停用成员保持停用。

通用映射命令为 `migrate_login_identities --mapping /绝对路径/mapping.json`，默认只预检；加 `--apply` 才原子应用。文件格式为 `{"groups":[{"phone":"13800000001","account_ids":["旧成员UUID"],"primary_account_id":"本组旧成员UUID","enabled":true}]}`。同一手机号所有旧成员须在同一组，以主成员密码哈希为准；同机构重复身份或未知绑定冲突会拒绝整批迁移。备份恢复可使用 PostgreSQL `pg_restore`，应在维护环境验证后替换数据库。

## 权限和业务规则

- 平台管理员管理机构、机构管理员、医生/患者/研究额度及用量，只访问控制面元数据。
- 机构管理员查看本机构全部业务数据；医生查看负责患者和参与研究。受试者、访视、答案及导出同时检查两种关系。
- 业务表强制启用 PostgreSQL RLS；请求内设置事务级机构上下文。业务和控制面运行账号不是所有者、超级用户或 BYPASSRLS 账号；迁移凭据单独使用。
- 未删除医生、患者、研究占用额度；停用医生、暂停/结束研究仍占用额度。软删除释放，恢复重新检查；用量由数据库触发器维护。
- 发布表单版本不可修改。研究生成首位受试者后，访视结构及所用版本固定。时间窗口只用于提醒，窗口外允许补录。
- 已完成访视、已停止随访或已结束研究中的答案只读。修订须填写原因并保留历史；首版不提供解锁或恢复停止随访的入口。
- 表单支持文本、长文本、数字、日期、单选、多选、下拉、滑条，以及前置显示条件和前向跳题。前后端消费同一 JSON 协议与共享验证样例。
- 导出按表单版本分表，包含当前草稿与提交状态；字符串按文本写入，文件名不含患者姓名。超长单元格拆为相邻续列，XML 无法表达的字符显示为 Unicode 转义。

不包含小程序、患者独立登录、微信邀请、附件/矩阵/评分题及分支访视。

## 验证

```bash
pnpm --dir frontend exec playwright install chromium
scripts/verify.sh
```

验证包含后端单元/权限/并发/真实 SQL 测试、迁移一致性、Django 检查、前端测试与类型检查、构建、真实浏览器闭环。后端使用 `vispect_test`，浏览器使用 `vispect_e2e_test`；只清空指定的测试库，不修改业务库。浏览器验收自动初始化独立虚构数据，使用 8001/5174 端口和独立 Cookie 名称。失败截图和轨迹保存在 `frontend/test-results/`。

CI 使用 PostgreSQL 17 和同样的受限角色；配置见 `.github/workflows/ci.yml`。CI 中的密码仅用于临时测试服务。CI 没有 `.env` 时直接使用作业环境变量。

当前已知限制：正式提交成功后，如果访视已完成或表单已暂停，原幂等键重试会返回 409。不会重复或修改答案；请打开该访视查看已保存答案确认提交结果。

## 容器运行

```bash
python3 scripts/init-env.py
docker compose up --build -d
# 可选：初始化虚构演示机构
# 不将演示密码加入常驻 Web 进程
# 在当前终端设置与 .env 一致的 DEMO_PASSWORD 后执行：
docker compose run --rm -e DEMO_PASSWORD="$DEMO_PASSWORD" migrate python manage.py seed_demo
```

打开 http://127.0.0.1:8080 。Django 使用 Gunicorn，前端由 Nginx 提供并同源代理 `/api/`。迁移由独立的一次性容器执行；常驻 Web 容器不接收迁移账号密码。PostgreSQL 和 Web 端口默认只绑定本机。

容器默认关闭 Django 调试。本机 HTTP 演示使用 `DJANGO_COOKIE_SECURE=false`；对外部署应启用 HTTPS、设置真实 `ALLOWED_HOSTS` 和 `CSRF_TRUSTED_ORIGINS`，并将 `DJANGO_COOKIE_SECURE=true`。在 HTTPS 终止代理中正确转发协议，按部署环境调整 Nginx TLS 配置。不要删除已有数据库卷来解决配置问题；已有卷的数据库角色密码不会随 `.env` 改动自动重置。

## 代码位置

- `backend/apps/`：认证、机构、医生、患者、表单、研究、随访和治理模块。
- `frontend/src/features/`：标准 Ant Design 页面；`form-engine/` 为共用预览/填写组件及解释器。
- `contracts/`：表单 JSON Schema 与跨语言共享样例。
- `docs/superpowers/specs/`、`plans/`：确认后的设计和实施计划。
