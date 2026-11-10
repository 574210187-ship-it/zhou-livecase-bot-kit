# START_WORKBUDDY.md

先读取同目录 `04_SECURE_CONNECTIONS_AND_UPLOAD.md`，再完整执行以下执行令。

# 网页版 WorkBuddy｜周意晨直播稿单窗口全流程接管令

## 0. 唯一目标

项目：**对标录屏05对标案例库 周意晨直播系统**。

你是唯一候选生产执行器。你的最终结果不是报告、ZIP、队列或接口成功，而是：

- 每个本轮候选源记录均进入真实终态；
- 可入库案例逐 ID 完成 **存储→案例库→Q50→源表** 四方写后读回；
- 无可入库内容也写入真实原因和源表终态；
- 独立 auditor 直接读取目标系统复核；
- 通过一条真实金丝雀后，继续处理所有可自动处理的历史欠稿和最新稿；
- 最后才创建一个每日 03:00（Asia/Shanghai）任务。

不得以模型回复、压缩包、队列、单表写入、请求返回、测试、日报或聊天总结替代完成。

## 1. 本次启动方式与绝对边界

- 首先使用本包 `02_RUNTIME_PROFILE.template.json` 创建你自己的私有 runtime profile；凭据只通过 WorkBuddy 的受控连接/环境密钥库配置，绝不出现在聊天、提示词、日志、JSON、Git 或交付物。
- 固定公开程序包：
  - 下载地址：`https://raw.githubusercontent.com/574210187-ship-it/zhou-livecase-bot-kit/release-v0.6.0/dist/zhou-livecase-bot-kit-v0.6.0.zip`
  - SHA256：`b315b53abd7b7db9244d2ec6425e8be1c121014feb5a9f6919a4df52cac26f02`
  - 字节数：`93850`
  - 固定分支：`release-v0.6.0`
- `app/src`、`app/tests`、`app/rules`、`app/docs` 只读。私有适配器、状态、日志、回执只能放在 `runtime/`，不得改公开包来绕过门禁。
- 本包给的是生产合同；你必须先以实际运行时证据填能力矩阵。未实测一律是 `false`。
- 不创建或启用旧 ChatGPT Space Page worker，不使用旧 v0.4.2 prompt；不要重放历史已完成/已关闭记录。
- 首次运行可自动继续，但只有所有零写预检通过、没有有效生产租约、且当前 SourceSnapshot 中存在真实候选时，才可进入金丝雀。

## 2. 目标系统（标识不是密钥）

- 生产 Base：`YVDlbBcSCaJOYos30qPcOpADnMf`
- 源表「对标完整直播稿」：`tblNuLU3X29HGU2o`
- 案例库「对标案例库」：`tblfb6WgPk3Eo9LS`
- Q50「麦手Q50对标匹配库」：`tbldGsx7xJYDtMLk`
- 汇报 Base：`MOJZbR6jTaq7HKsqsbXcvCYQnRf`
- 汇报表「汇报项目」：`tbldUi7L7rpRVYTe`

必须用真实的受控飞书连接读取并写回；不得用页面截图、旧 CSV、猜测字段或本地假数据代替。

## 3. 先做零写预检，不得停在“准备完成”

execution_id：`zhou-workbuddy-web-preflight-20261110-01`。

依次完成，所有调用均不得写生产：

1. 下载固定包，校验 SHA、字节数、CRC；运行 `52/52` 单测和 `verify_release`。
2. 读取 `START.md`、`GROK_MUSE_START.md`、`HUMAN_READABLE_FIELDS.md`、`FAILURE_PLAYBOOK.md`、`AUTHORIZATION_CHECKLIST.md`、`PATH_A_SINGLE_WINDOW.md`。
3. 实测以下能力并逐项记录：
   - 飞书源表/案例库/Q50 的全分页只读；
   - runner 的 `status` 和严格无副作用 `dry_run`；
   - 与 runner 身份、进程、凭据分离的 auditor 的 `status` 和一条已完成样本只读 audit；
   - COS writer/auditor 的既有对象 `HEAD + 下载 + SHA256`；
   - 模型实际名称、推理强度、结构化 JSON 输出能力；
   - 文件下载、源稿附件读取、私有 runtime 持久化、原子锁/租约。
4. 生成本轮不可变 `SourceSnapshot`：全分页源表，保存页摘要、record_id 集合、总数、revision、SHA256。不得依赖旧队列决定范围。
5. 读取案例库和 Q50，按真实业务键复核；候选只来自本次 SourceSnapshot 中**最终状态为空**且源稿附件可读的记录。已完成、合法关闭、已作废、重复记录不得重新开启。
6. 产生：`PREFLIGHT_RESULT.json`、`SOURCE_SNAPSHOT.json`、`CAPABILITY_EVIDENCE.json`、`ZERO_WRITE_LIST.json`、`PRECHECK_AUDIT.json`。

### 预检的硬判断

- 若 runner、独立 auditor、存储读回、飞书读写授权、模型/文件读取、租约任一项缺失：远端写入保持 0，输出唯一 `USER_ACTION_REQUIRED.json`。
- `USER_ACTION_REQUIRED.json` 每项只写：error_code、缺失能力、最小需要谁在何处配置、验证命令；不得要求聊天粘贴 token/Secret/Webhook。
- 如果所有能力为 true，**不要停在 READY**，立即执行第 4 节金丝雀。

## 4. 生产事务：先一条金丝雀，再自动追平

### 4.1 唯一写入者与租约

- 生产前查询共享租约。存在另一个有效 holder 时，零写退出并记录 holder/expires_at/fencing_token，不得换 execution_id 绕过。
- 金丝雀 execution_id：`zhou-workbuddy-web-canary-<当前上海时间>`。
- 租约键：`source_record_id + execution_id`；所有 commit 前执行 CAS/fencing 校验。
- 幂等键：`run_id:record_id:generation:stage`。同键同内容返回原回执；同键不同内容拒绝；阶段顺序固定：`storage → case_write → q50_write → source_closeout`。

### 4.2 候选选择

从最新 SourceSnapshot 的最终状态为空记录中，选**提交时间最新、源稿可读、案例库/Q50无已验证完成链、无有效租约**的一条。保存选择理由。找不到候选时输出 `no_realtime_candidate`，不重开历史终态。

### 4.3 逐记录处理

1. 下载源稿，记录原始 SHA256 与来源身份。
2. 用当前实际模型生成严格 JSON，不得产生自由散文作为写入载荷。
3. 写入前质量门禁：
   - 业务字段必须是具体自然中文；禁止内部码、JSON、URL、占位词、空泛模板；
   - 标题、概要、主方向、看事索引、单麦作用、禁借元素等展示字段须人能读懂；
   - evidence quote 必须是原稿逐字连续子串；claim 的数字与关键事实须在对应 quote 内；
   - 说话人无法确证时收窄结论，不强行归属；
   - Q50 必须有真实案例引用、目标麦手、匹配理由、分值/等级和必要业务字段；禁止最小关联壳。
4. `accept=0` 或无合法可入库案例时，runner 只写源表真实关闭原因并读回；不能把它留为笼统 pending。
5. 有可入库案例时，runner 按四阶段写入，每阶段都返回读回回执。任一阶段失败只隔离该 record_id，生成精确 `ReworkOrder`，继续下一条可自动处理记录。
6. auditor 从目标系统独立复核：存储对象重新下载 SHA、案例库按业务键、Q50按全表案例引用、源表终态和阶段回执。审计失败即局部返工，不得写 complete。

### 4.4 金丝雀成功后

金丝雀四方读回 + auditor PASS 后，立刻在**同一控制面**中处理本次 SourceSnapshot 内所有仍可自动处理记录；中断恢复时重读 ledger 与目标系统，不重复写。

每处理 5 条，重新计算案例库↔Q50全量缺口、核对存储/案例/Q50/源表读回；发现半成品优先修复，再继续。

## 5. 汇报、通知和每日任务

### 飞书汇报表

每次开始、实质进度变化或30分钟、首次真实故障、恢复、最终结果都在「汇报项目」新增独立行，并写后读回 `record_id`。

- 先读取字段 schema；**字段名以 `/` 开头的一律不填写、不改动**。
- 每条内容中文自然表达；每个小项目之间空一行；时间信息放正文底部。
- 不覆盖旧行，不把多次事件塞进同一执行记录单元格。

### 企业微信

- 正常开始、实质进度、最终结果：群01。
- 首次真实故障、错误码变化、需要人工、恢复：群05。
- 同一错误重试只记日志/飞书事件，不重复群发；只有 HTTP 200 且 errcode=0 才记“机器人接口已接受”，不得写“群已收到”。
- Webhook 必须来自 WorkBuddy 私有密钥设置；未配置时记录 `notification_unconfigured`，不把它伪装成已送达。

### 每日任务

只有金丝雀、独立审计和全量追平通过后，才建立**一个**每日 03:00 Asia/Shanghai 的官方任务。每日任务启动时重新做快照，范围为最新稿 + 所有实时未终态；不得靠旧队列或昨日结果跳过。

## 6. 禁止与停止条件

- 不并发写生产；不把旧 Page、旧 WorkBuddy、DSH/Grok/Muse 的历史回执当成本轮能力。
- 不用聊天、截图、模拟表、测试数据或临时直写脚本冒充 runner/auditor。
- 不创建测试业务行，不补发历史汇报，不把旧自然运行当作当前进度。
- 不得因一个记录失败停止整批；仅用户权限、人工事实裁定、来源证据真正缺失时隔离对应 ID。
- 所有可自动处理记录完成后，输出 `WORKBUDDY_WEB_TAKEOVER_RESULT.json`：本轮快照、处理数、每阶段写入数、逐 ID 四方读回、独立审计、剩余精确阻塞、租约、每日任务配置和汇报 record_id。

## 7. 首屏返回格式

先返回以下结构，不写长篇过程：

```text
版本与SHA：
预检：ready=<true|false>；路线=inline_single_window
SourceSnapshot：记录数/候选数/SHA
能力矩阵：runner / auditor / COS读回 / 飞书三表 / 模型 / 租约
远端写入：COS=0；案例库=0；Q50=0；源表=0（预检阶段）
下一动作：<自动进入金丝雀 或 精确USER_ACTION_REQUIRED>
回执文件：
```

如果预检通过，此首屏回执后继续自动跑金丝雀；不得等用户再次说“继续”。
