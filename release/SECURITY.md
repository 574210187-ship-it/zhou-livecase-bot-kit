# 发布安全边界

- Git 永不保存真实 webhook、token、cookie、密码、COS 密钥、飞书 app token、真实表 ID、真实 bucket/prefix 或业务快照。
- runner 使用最小写权限身份；auditor 使用独立只读身份。
- 真实配置只存在于私有运行环境，且以环境变量名称而非值进入版本化文件。
- 发布前执行密钥扫描、绝对路径扫描、夹具匿名化检查和离线测试。
- 发布 ZIP 必须由 `release/build_release.py` 构建；它在扫描通过后写入逐文件 SHA256 清单，安装侧必须重新验 SHA。不得手工打包、上传未扫描目录或把本机 `dist/` 当作源码提交。
- 首次真实写入只能是受控金丝雀；没有四方读回与 auditor 通过不得切换每日生产。

