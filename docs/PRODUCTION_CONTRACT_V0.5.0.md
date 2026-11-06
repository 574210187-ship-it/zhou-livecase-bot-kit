# v0.5.0 云端生产入口合同

## 为什么旧链路会“有线程、无结果”

旧链路把四件不同的事混在一起：云端对话有更新时间、保存的自动化存在、环境显示 ready、
以及生产入口实际启动。它没有强制把这四件事绑定到同一个 `execution_id`，也没有强制把
来源快照、每条记录的四阶段读回和独立审计绑定到同一回执。因此会出现“线程动过了，但源表
仍有新稿，写入和回执为空”的假进展。

## 唯一正确链路

1. **启动**：私有运行时现场生成 `RuntimePreflight`，验证环境、固定发布提交、发布包 SHA、
   规则 SHA、模型/强度和四个写入适配器 readiness。任何一项不可读即停止，不能进入写入。
2. **取数**：完整分页读取源表，生成不可变 `SourceSnapshot`。候选记录集合和快照 SHA 写入
   同一执行台账；重启只能复用原快照，不能换批或回放历史。
3. **逐条执行**：每条记录按存储→案例库→Q50→源表顺序执行，单条失败隔离，继续后续记录。
   每次写入必须返回目标系统 readback_id、时间、身份和哈希；请求成功不算通过。
4. **独立审计**：生产写入结束后由只读 auditor 全量读取目标系统，提交同一执行编号、同一
   快照 SHA、完整通过 ID 集合和失败 ID 集合。
5. **收口**：只有所有候选进入合法终态、所有 complete 记录四方读回、独立审计通过，
   `ExecutionLedger` 才能生成 `status=success`。否则只能是 `partial`、`failed` 或
   `no_candidate`，且必须逐条带错误码和下一步。

## 生产入口

```bash
PYTHONPATH=src python3 -m zhou_livecase.production_entrypoint \
  --ledger "$RUN_LEDGER" start \
  --preflight "$PREFLIGHT_JSON" \
  --snapshot "$SOURCE_SNAPSHOT_JSON" \
  --run-id "$EXECUTION_ID"
```

每条完成记录必须通过 `record` 写入四个阶段回执；最后只允许用独立 auditor 的 JSON 调用
`finish --audit-report`。没有 `execution_id`、入口启动事件、来源快照、四方读回或审计报告，
都不得对外报告完成。

## 当前 2026-11-06 接管范围

实时源表中新增 60 条记录尚未进入终态。v0.5.0 已在本地完成合同回归，但云端连接器当前
无法读回既有 worker 的运行入口和执行回执；因此当前生产状态仍为“已部署待验收”，不能
把这 60 条标为已处理。连接器恢复后，必须在同一私有环境先做版本/适配器 readiness 和
零写 shadow audit，再用一条实时新记录金丝雀，成功后才续办剩余记录。
