# 私有权限接入清单

公开仓库不包含任何真实 app token、表标识、COS 桶、密钥、cookie、机器人地址或业务数据。Grok/Muse 只能在用户指定的私有运行环境中请求下列最小授权。

## 必需授权

1. 来源表全分页只读：读取新增及所有历史未终态记录；
2. 私有 runner 调用权：机器人提交结构化分析和写入计划，runner 独占实际写权限；
3. 独立 auditor 调用权：只读 COS、案例库、案例匹配和源表；
4. COS/附件写权限：仅赋给 runner，机器人本身不读取密钥；
5. 飞书案例库、案例匹配、源表写权限：仅赋给 runner；
6. 两条路径试验若选择委托普通 ChatGPT：可见浏览器自动化、上传、下载、逐条删除会话及刷新确认。

## 请求方式

- 只报告缺少的能力名称、用途、最小 scope 和应由谁配置；
- 让用户在平台或私有密钥库完成授权，不要求用户把 token、webhook、cookie 或密码粘贴进聊天；
- preflight 没通过时，不调用写入口、不制造测试业务行、不用旧快照冒充实时数据；
- 表权限到位后重新生成同一格式的 capability profile，再运行 preflight。

## 能力预检

```bash
cp config/grok.example.json runtime/grok.json
# 只把已实测能力从 false 改为 true，不填任何密钥值
PYTHONPATH=src python3 -m zhou_livecase.external_bot_entrypoint \
  preflight --profile runtime/grok.json --preferred auto
```

只有 `ready=true` 且 `selected_route` 非空，才可进入路线小样测试。
