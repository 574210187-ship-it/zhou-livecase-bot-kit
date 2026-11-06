# 周意晨对标直播稿生产系统

这是一个无密、可移植、合同优先的生产内核，供 Codex、Grok、Muse 或其他执行器在**用户授权的私有运行环境**中处理直播稿、生成案例并写入存储、案例库、案例匹配与源表。

## 唯一完成定义

AI 只产生结构化分析；私有 `runner` 是唯一写入口；独立 `auditor` 只读复核。单条可入库记录只有取得以下四项逐 ID 写后读回才能标记 `complete`：

1. 存储对象下载后 SHA 一致；
2. 案例库行存在且人看字段正确；
3. 案例匹配行完整并正确关联案例；
4. 源表终态、批次和结果附件回读一致。

模型回复、ZIP、计划、队列、HTTP 200、线程更新时间、群消息、单表写入和测试通过都不是业务完成。

## v0.6.0 新增

- Grok/Muse 能力预检和最小授权清单；
- 路径 A“Bot 单窗口全流程”和路径 B“Bot 委托普通 ChatGPT 逐稿处理”；
- 表内自然中文、来源身份、逐字引文和数字事实硬门禁；
- 路径 B 的可见界面会话删除与刷新后缺席证明；
- 两条路径的正确性→耗时→真实 token→重试对比器；
- 16 类历史返工错误的匿名回归合同；
- 更严格的公开发布扫描：密钥、本机路径、真实飞书链接、表 ID 和记录 ID 均阻断发布。

## 快速验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 release/verify_release.py --root .
```

## 外部 Bot 入口

- [Grok / Muse 完整启动协议](docs/GROK_MUSE_START.md)
- [人看字段与证据门禁](docs/HUMAN_READABLE_FIELDS.md)
- [历史返工坑位](docs/FAILURE_PLAYBOOK.md)
- [私有权限清单](docs/AUTHORIZATION_CHECKLIST.md)
- [路径 A](docs/PATH_A_SINGLE_WINDOW.md)
- [路径 B](docs/PATH_B_DELEGATED_CHATGPT.md)

能力预检示例：

```bash
cp config/grok.example.json runtime-profile.json
PYTHONPATH=src python3 -m zhou_livecase.external_bot_entrypoint \
  preflight --profile runtime-profile.json --preferred auto
```

公开仓库不含任何真实凭据、表标识、业务稿件、运行回执或私有适配器。公开程序就绪不等于生产已接通；首次真实业务仍须由用户授权私有 runner/auditor，并用一条实时新记录取得四方读回。
