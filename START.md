# 启动入口

## Grok / Muse

首次使用请完整读取 [`docs/GROK_MUSE_START.md`](docs/GROK_MUSE_START.md)。它包含可直接复制的首次生产指令、两条路线小样测试、权限请求方式、全量执行顺序和唯一完成口径。

已经通过能力预检、两路径试验和首次金丝雀后，日常最短口令是：

```text
执行周意晨对标直播稿全量生产：处理今天新增、最新批次和全部历史未终态；按已验收路线运行，逐 ID 四方读回，独立审计后收口。
```

短口令不允许跳过实时来源快照、规则/发布 SHA、写入门禁或独立审计。

## 本地离线验收

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 release/verify_release.py --root .
python3 release/build_release.py --output dist/zhou-livecase-bot-kit-v0.6.0.zip
```

## 私有生产入口

自然语言指令只表达启动意图。私有宿主必须构造实时 `preflight.json`、全分页 `source_snapshot.json`，再调用：

```bash
PYTHONPATH=src python3 -m zhou_livecase.production_entrypoint \
  --ledger "$RUN_LEDGER" start \
  --preflight "$PREFLIGHT_JSON" \
  --snapshot "$SOURCE_SNAPSHOT_JSON" \
  --run-id "$EXECUTION_ID"
```

每条记录写入后提交存储、案例库、案例匹配、源表四阶段回执。全部候选进入合法终态后，由独立只读 auditor 生成同一 execution_id 和 snapshot SHA 的审计结果，再调用 `finish`。只有 `remaining_count=0`、四方读回和审计同时通过才能报成功。
