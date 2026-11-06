# Grok / Muse 独立生产启动协议

## 公开入口

- 仓库：<https://github.com/574210187-ship-it/zhou-livecase-bot-kit>
- 本协议原文：<https://raw.githubusercontent.com/574210187-ship-it/zhou-livecase-bot-kit/main/docs/GROK_MUSE_START.md>
- 发布 ZIP：<https://raw.githubusercontent.com/574210187-ship-it/zhou-livecase-bot-kit/main/dist/zhou-livecase-bot-kit-v0.6.0.zip>
- ZIP SHA：以仓库根目录 `PUBLIC_RELEASE.json` 的 `zip_sha256` 为准；不得相信聊天里手抄的 SHA。

## 用户给 Bot 的完整首次指令

把下面整段发给 Grok 或 Muse，只替换第一行 `BOT_NAME`：

```text
BOT_NAME=<grok 或 muse>

你负责独立执行“周意晨对标直播稿→案例→存储→案例库→案例匹配→源表收口”的完整生产流程。你的唯一结果不是报告、ZIP、队列或模型回复，而是每个可入库记录都取得存储、案例库、案例匹配和源表四方逐 ID 写后读回；无 accept、重复、需人工或权限阻塞的记录也必须写入真实终态和下一动作。

一、取得并锁定公开程序
1. 从 https://github.com/574210187-ship-it/zhou-livecase-bot-kit 下载 main，或下载 https://raw.githubusercontent.com/574210187-ship-it/zhou-livecase-bot-kit/main/dist/zhou-livecase-bot-kit-v0.6.0.zip 。
2. 读取 PUBLIC_RELEASE.json，核对 ZIP SHA 和逐文件清单；运行 release/verify_release.py 与全部 unittest。失败时停止写入并报告准确错误。
3. 完整读取 START.md、docs/GROK_MUSE_START.md、docs/HUMAN_READABLE_FIELDS.md、docs/FAILURE_PLAYBOOK.md、docs/AUTHORIZATION_CHECKLIST.md、docs/PATH_A_SINGLE_WINDOW.md、docs/PATH_B_DELEGATED_CHATGPT.md。

二、能力和权限预检
1. 复制 config/<BOT_NAME>.example.json 为私有 runtime profile，只把已经实测可用的能力改成 true，不在文件或聊天中写任何 token、cookie、webhook、表 ID 或 COS 密钥。
2. 运行：PYTHONPATH=src python3 -m zhou_livecase.external_bot_entrypoint preflight --profile <profile> --preferred auto。
3. 如果缺来源表、私有 runner、独立 auditor、目标读回或可见浏览器能力，只向用户列出最小授权名称、用途和配置位置；不要索取密钥值。未通过 preflight 不得制造测试业务行。

三、先各测两条，两条路径都必须测试
路径 A：当前 Bot 单窗口直接完成结构化分析，写入仍只能调用私有 runner。
路径 B：当前 Bot 通过受支持的可见浏览器自动化，为每条稿新开普通 ChatGPT 网页会话，上传当前输入和固定规则，下载结果、核 SHA、跑本地门禁；业务验收后从左侧历史的三点菜单逐条删除本轮会话，刷新主页确认消失。禁止使用未公开内部接口，禁止只关标签页或只归档。
两条路径各取两条相同难度、尚未终态的真实记录做 shadow/canary：未经用户授权前保持远端写入 0；获授权后每条最多写一次且使用不同幂等键。记录 wall_seconds、宿主真实提供的 token（没有则 null）、重试、人工动作、质量失败、清理失败和四方读回。
分别生成 route_metrics JSON，再运行 compare-routes。只有质量门禁和独立审计都通过的路线才可参与速度/token 比较；先正确，再快，再省 token。不得因为速度快选择错误路线。

四、全量执行
1. 从来源表全分页实时读取：今日新增、最新批次、全部历史未终态。不能用旧队列或旧报告代替实时快照。
2. execution_id 必须绑定来源快照 SHA、规则 SHA、发布提交/ZIP SHA；同一执行编号不可换候选集合。
3. 每条先核来源身份、附件 SHA、账号和录屏名称；跨表按业务合同关联，录屏分片必须保留 P001/P002 等后缀。
4. 生成 accept/review/reject 和人看字段。飞书业务字段必须是具体自然中文；禁止内部状态码、JSON、占位词、存储 URI、空壳标题和模型猜测。引文必须是源稿逐字子串，claim 的数字事实必须由同条展示引文覆盖。
5. 运行 validate-visible。失败只返工对应边界，不得改词表或删除校验制造绿灯。
6. review 不代签；reject/无 accept 不反复生成；单条失败只隔离本条，继续其他可做记录。
7. 所有远端写入只能由私有 runner 按存储→案例库→案例匹配→源表顺序执行。每一步必须写后读回；Q50/案例匹配缺口先补齐再关闭源表。
8. 独立 auditor 用不同的只读身份全分页核验来源身份、对象 SHA、案例内容、案例匹配完整字段、关联关系和源表终态。只按 ReworkOrder 局部返工，直到所有候选进入合法终态。

五、停止与汇报
只有 execution receipt 显示 remaining_count=0、所有 complete 四方读回通过、所有非 complete 有真实终态及 source readback、独立 audit passed，才能报成功。HTTP 200、机器人接口接受、线程更新、环境存在、模型回复、ZIP、计划、队列、测试、单表写入都不能报完成。
遇到权限或需要真人处理时，只阻断对应 record_id；继续完成其他记录。最终交回：execution_id、固定版本/SHA、实时候选数、四类逐 ID 结果、四方读回记录 ID、独立审计回执、两条路线指标与最终选择、所有未完成 ID 的准确原因和下一动作。不要给长篇过程旁白，先给真实结果。
```

## 后续最短口令

首次完成环境授权、两路径测试和生产金丝雀后，用户每天只需说：

```text
执行周意晨对标直播稿全量生产：处理今天新增、最新批次和全部历史未终态；按已验收路线运行，逐 ID 四方读回，独立审计后收口。
```

Bot 仍必须重新生成实时来源快照和 preflight，不能因为口令短而跳过门禁。
