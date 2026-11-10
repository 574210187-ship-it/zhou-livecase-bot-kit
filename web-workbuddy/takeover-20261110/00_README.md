# WorkBuddy 网页版接管包（2026-11-10）

- 用途：让网页版 WorkBuddy 以 `inline_single_window` 路线接管周意晨直播稿处理。
- 状态：**待用户发送给 WorkBuddy；尚未产生任何生产写入。**
- 先上传本 ZIP，再把 `01_WORKBUDDY_WEB_SINGLE_WINDOW_TAKEOVER.md` 全文作为第一条任务发给 WorkBuddy。
- 它必须先完成零写预检；预检成功后会自行继续金丝雀和欠稿追平，不需要再等第二条“继续”。
- 当前本机基线（仅作交叉核对）：2026-11-10 源表762条，最终状态空白140条；实际范围须由 WorkBuddy 启动时重建的 SourceSnapshot 决定。
- 不含任何 token、secret、cookie、webhook 或私有凭据。
