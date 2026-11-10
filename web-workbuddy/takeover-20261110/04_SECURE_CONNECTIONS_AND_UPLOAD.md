# 网页版 WorkBuddy 私有连接配置：飞书与腾讯云 COS

本文件是公开接管包的一部分，只写**变量名、职责和验收方法**；不含 AccessKey、SecretKey、飞书 app_secret、OAuth token、Cookie、Webhook 或签名 URL。

## 1. 为什么公开指令本身不能直接上传

GitHub 下载包负责固定流程、质量门禁与验收口径；它不携带任何写入凭据。网页版 WorkBuddy 只有同时具备下列受控私有连接时，才可进入生产：

1. `zhou_feishu_runner`：生产写身份；读取来源表、创建/更新案例库与 Q50、回填源表及汇报表。
2. `zhou_feishu_auditor`：与 runner 分离的只读身份；独立读回案例库、Q50、来源表。
3. `zhou_cos_writer`：指定 bucket/prefix 的 PutObject、GetObject、HeadObject；不授予 DeleteObject。
4. `zhou_cos_auditor`：独立只读身份；仅 GetObject、HeadObject。
5. `zhou_livecase_runner`：唯一生产写入口；接受结构化分析和阶段提交，执行存储→案例库→Q50→源表，并逐阶段读回。
6. `zhou_livecase_auditor`：独立只读审计入口；直接读取 COS/飞书目标系统，不采信 runner 自述。

如果当前 WorkBuddy 平台没有“私有连接/密钥库/受控 MCP/受认证 HTTPS 服务”中的任一种，不能把 API 密钥粘到聊天框或公开文件里；应输出 `USER_ACTION_REQUIRED.json`，准确写出缺的连接类型。

## 2. 飞书配置（每个 WorkBuddy 账号一次）

在该账号的 WorkBuddy 私有连接或企业密钥库中新建/绑定以下连接，不把真实值放入本包：

| 连接 | 用途 | 最小能力 | 验收 |
|---|---|---|---|
| `zhou_feishu_runner` | 生产写入 | 目标 Base 的读写、附件读取、汇报表新增行 | `status` + `dry_run` 为零写；金丝雀写后逐 ID 读回 |
| `zhou_feishu_auditor` | 独立验收 | 同一 Base 的只读 | 直接全分页读取，验证对 runner 写入结果可见；代码/权限均无写方法 |

目标 Base 与表标识由 `02_RUNTIME_PROFILE.template.json` 载入。API App ID/App Secret/Access Token 只在 WorkBuddy 的私有连接设置中输入；不得在聊天、回执、Git 或日志打印。

## 3. 腾讯云 COS 配置（每个 WorkBuddy 账号一次）

在私有连接中建立：

| 连接 | 用途 | 权限 |
|---|---|---|
| `zhou_cos_writer` | 上传分析 ZIP、详情和阶段回执 | 仅目标 bucket/prefix 的 PutObject、GetObject、HeadObject；禁止 DeleteObject |
| `zhou_cos_auditor` | 独立下载并复算 SHA256 | 仅目标 bucket/prefix 的 GetObject、HeadObject；禁止 PutObject/DeleteObject |

COS writer 的正确生产流程为：计算本地原始 SHA256 → `PutObject` → `HeadObject` 核对大小/元数据 → `GetObject` 下载 → 重新计算 SHA256 → 仅一致时返回 `storage_verified=true`。随后 runner 才能写案例库。

COS auditor 必须重新下载同一对象并复算 SHA256；它不得使用 runner 的成功状态代替实测。

## 4. 连接自检顺序

1. runner `status` 与严格无副作用 `dry_run`；预期远端写入均为 0。
2. auditor 对一条既有完成案例运行只读 audit；它须直接读取 COS、案例库、Q50、源表。
3. COS writer/auditor 对一条已有对象分别执行 `HEAD + 下载 + SHA256`；二者结果一致。
4. 飞书全分页读取来源表、案例库、Q50，并生成本轮 SHA 快照。
5. 全项通过后才允许金丝雀；任一项不通过，生产写入 0。

## 5. 账号轮换规则

- 每个新网页版 WorkBuddy 账号都先下载同一 GitHub 指令并执行上述零写预检。
- 共享的生产写入服务/租约必须仍是同一个；新账号不能绕过已有 lease。
- 新账号的模型额度变化不会改变数据验收口径；能力不满足就停在 `USER_ACTION_REQUIRED.json`。
- 新账号从 GitHub 获取规则，不从旧聊天复制历史结论。
