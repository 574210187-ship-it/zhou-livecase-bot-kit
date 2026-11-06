# 历史返工坑位与固定处理

本清单把长期运行中反复发生的错误转成可执行约束。发生同类问题时先按本表处理，不再重新发明口径。

| 历史坑位 | 固定处理 | 完成证据 |
|---|---|---|
| 只看队列或旧报告，漏掉活表新增 | 每次启动全分页实时快照，快照 SHA 绑定 execution_id | snapshot + 候选 record_id 集合 |
| 跨表拿 record_id 直接关联 | 使用合同规定的业务键；录屏名须保留 P001/P002 分片 | 唯一关联、缺失/冲突清单 |
| 同场分片被判重名冲突 | 精确文件名含分片后缀；base 名只作场次聚合 | exact key 唯一 |
| 结果 ZIP 配对成功但内容是 gap/错稿 | 打开内层 manifest、核来源身份、逐字稿 SHA 和有效内容 | 内容门禁回执 |
| 来源包挂到错误账号/场次 | source identity 必须与实时快照一致 | SOURCE_IDENTITY_MISMATCH 时隔离本条 |
| 模型回复中的引文不是逐字原文 | 引文必须是 source_text 连续子串 | EVIDENCE_NOT_VERBATIM=0 |
| claim 数字落在截断引文之外 | 延长同一 turn 的真实引文或收窄 claim，不拼造 | CLAIM_FACT_UNSUPPORTED=0 |
| 主播/来访者混编轮次被强行归属 | 不能确证就标弱旁证/不确定，换干净 turn 或收窄 | 人工审计说明 |
| 带货、寒暄、广告被当案情证据 | 逐角色做语义相关性审查，不能只看字数与逐字命中 | 语义审计通过 |
| 表格写入内部码、JSON 或“普通案例麦” | 写前 human-readable gate；业务字段只写自然中文 | 目标表逐字段回读 |
| 标题带标点触发结构失败 | 标题 6–60 字、无标点 | TITLE 门禁通过 |
| 只写案例库，漏案例匹配 | runner 固定 storage→case→Q50→source；任一步失败不关源表 | 四阶段 receipt |
| Q50 用本记录局部 receipt 判断，误报缺失 | auditor 对活表全量业务键做关联核验 | 全局 Q50 linkage |
| Q50 最小骨架行冒充完整 | 目标、分数、等级、理由、证据均非空且业务可读 | Q50 合同通过 |
| 飞书附件 URI 被当 COS key | 按 scheme 选择下载通道，实下载后比 SHA | fresh_download_sha256 |
| 请求成功/HTTP 200 被当业务完成 | 只认目标系统读回与独立 audit | 四方 readback + audit |
| 单条失败阻断全批 | 记录级隔离，继续后续可自动记录 | remaining 逐 ID 有原因 |
| review 被机器代签或一律当 reject | 保留 review_pending，输出人工清单 | reviewer 真实、未代签 |
| 费用/权限缺失时绕过闸门 | 只请求最小授权；未授权记录单条阻断 | capability report |
| 旧会话未删除，左侧历史堆积 | 路径 B 每条下载验收后可见删除并刷新确认 | delegated receipt |
| 新会话重置模式/强度 | 每次发送前读回模式/模型/强度；不满足则隔离本条 | 页面可见状态证据 |
| 生成脚本误读历史回执 | 回执必须绑定 execution_id、generation、mtime 之后的新文件 | receipt identity |
| 自动化/文档更新被当生产发布 | 入口日志、启动配置、首条真实四方读回三项齐全才算发布 | production evidence |
| 故障修复后重复补发历史事件 | 只处理当前 execution_id，不补发测试/历史/暂停期事件 | 事件去重键 |

任何未覆盖的新错误都应先生成匿名最小回归用例，再修改生产入口；不能通过删校验、改词表或手工改最终表制造成功。
