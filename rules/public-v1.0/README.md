# 无密规则包 public-v1.0

本目录是从既有生产规则中抽取并去除真实 Base/table/record 标识、本机路径、私有适配器和历史业务数据后的公开规则。它保留分麦、深度解析、人看字段、证据和输出合同，并叠加 v0.6.0 的来源身份与可读性门禁。

执行器必须在私有环境中把来源身份注入输入 manifest；规则包本身不固定任何真实目标表。Bot 只能输出结构化分析，不能直接写远端。

- `prompts/01_transcript.md`：原始直播稿→完整连麦边界和逐字 turn；
- `prompts/02_deep.md`：逐麦→accept/review/reject、八个人看字段、四类证据和深度事件卡；
- `contracts/*.json`：机器可校验的最小合同；
- `build_rule_packs.py`：构建两个确定性 ZIP 和 SHA 清单。
