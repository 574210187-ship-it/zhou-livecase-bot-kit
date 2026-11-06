# 架构

```text
AI（ChatGPT Work / DSH）
  -> AnalysisBundle
  -> runner（唯一写入）
  -> COS -> 案例库 -> Q50 -> 源表
  -> auditor（独立只读）
  -> AuditReport 或 ReworkOrder
```

## 三条不可突破的边界

1. AI 没有 COS、飞书写权限；它只提交带来源证据和 SHA 的分析包。
2. runner 只接受经合同校验的写入计划，并固定按存储、案例库、Q50、源表顺序写后读回。
3. auditor 不导入 runner、不读 runner 状态、不写外部系统；它重新从目标系统读取并在失败时生成最小返工单。

`COMPLETED` 需要存储、案例库、Q50、源表逐 ID 读回和 auditor 通过。任何单表成功、HTTP 200、队列、报告、模型回复或 ZIP 都不构成完成。

## 发布阶段

- 草案：合同/代码存在。
- 已构建：离线合同和反例回归通过。
- 已部署待验收：私有 runner、只读 auditor、AI 适配器已安装。
- 已由真实业务验证：新的真实记录完成四方读回并由 auditor 独立通过。

## 迁移边界

本项目的首个生产部署采用兼容迁移：新合同层调用既有 v0.4.2 的实际 COS 与飞书适配器，不创建第二个写入环境，不复制密钥，不为验证重跑历史业务。`runner` 与 `auditor` 的职责边界不变；变化仅是适配器外层增加版本锚定、统一回执和独立审计。具体步骤与验收见 [`COMPATIBILITY_MIGRATION.md`](COMPATIBILITY_MIGRATION.md)。

