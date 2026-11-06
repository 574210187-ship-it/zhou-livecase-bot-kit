# 路径 B：委托普通 ChatGPT 网页逐稿处理

## 适用条件

Bot 缺少足够的内联分析能力，或小样证明普通 ChatGPT 在相同质量门槛下更快、更省真实 token。Bot 必须有受支持的可见浏览器自动化；禁止调用 ChatGPT 未公开内部接口。

## 每条记录的闭环

1. 建立唯一 `conversation_id`，记录输入文件 SHA；
2. 通过可见界面新开普通 ChatGPT 会话，上传当前记录及固定规则；
3. 等待完整结果，不以停止按钮消失、页面在线或出现部分文本作为完成；
4. 下载结果并比较页面输出 SHA 与下载文件 SHA；
5. 在 Bot 本地运行来源身份、人看字段、逐字引文和数字事实门禁；
6. 门禁失败时在同一记录内局部返工，不把坏结果传给 runner；
7. 结果已下载、SHA 一致且门禁通过后，通过左侧会话列表的可见“三点→删除→确认”逐条删除该会话；
8. 刷新主页并确认该 `conversation_id`/标题不再出现；禁止只关标签页、只归档、只关浏览器空间；
9. 生成 delegated chat receipt 并运行：

```bash
PYTHONPATH=src python3 -m zhou_livecase.external_bot_entrypoint \
  validate-delegated --receipt delegated_receipt.json
```

10. receipt 与人看门禁均通过后，才生成 WritePlan 并交私有 runner 写入；独立 auditor 负责最终验收。

## 强制停止条件

- 登录失效、页面不可访问或无法通过可见界面删除会话：仅隔离本条并继续其他可做记录；
- 输出未下载或 SHA 不一致：不得写入；
- 会话未删除或刷新后仍存在：该条不能宣称完整收尾，但其已验收业务写入不得重复；
- 不得用隐藏接口删除会话，不得猜测页面状态。
