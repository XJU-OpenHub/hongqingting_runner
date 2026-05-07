# server/ — 教学代理（FastAPI + cloudflared + sk-token vault）

把 Python `requests` 能做、浏览器 `fetch` 做不了的活（gzip / 修改 UA / HTTPS→HTTP）放在
代理服务器上。所有敏感配置（authUrl / summaryUrl / uploadUrl / queryUid / uidList）通过
sk-xxx token 加密存放在服务器 vault 里，**不进仓库、不进前端、前端只需 sk**。

## 架构

```
浏览器 (GitHub Pages, HTTPS)
   │  fetch docs/proxy.json → 拿到 cloudflared URL
   │  POST /v1/summary | /v1/upload | /v1/check  +  {token: "sk-xxx", ...}
   ▼
cloudflared quick tunnel (https://xxx-xxx.trycloudflare.com)
   │
   ▼
FastAPI uvicorn @ 127.0.0.1:8000
   │  vault.decrypt(token) → 拿出 authUrl / summaryUrl / queryUid …
   │  做 gzip / MD5 / 轨迹时间戳重写 / 上游 POST
   ▼
你授权的教学 mock (HTTP)
```

## 文件结构

```
/opt/hongqingting_runner/
├── app.py
├── vault.py
├── venv/
├── trajectories/          # location_*km，被后端读取
│   ├── location_1km
│   ├── location_1_16km
│   ├── location_1_6km
│   └── location_12km
└── secrets/
    └── vault.json         # 0600，sk → ciphertext，绝不要 commit
```

## 端点

| 端点 | 入参 | 用途 |
| --- | --- | --- |
| `POST /v1/check`   | `{token}`                           | 验证 sk 是否有效，回显 schoolNo / uid 数 |
| `POST /v1/summary` | `{token, studentNo}`                | 查询累计里程 |
| `POST /v1/upload`  | `{token, studentNo, track, dayOffset, uidIdx?}` | 上传一次跑步数据 |
| `GET  /tunnel-info`| —                                   | 读 cloudflared journal，返回当前 trycloudflare URL |
| `GET  /`           | —                                   | 健康检查 |

## vault CLI

```bash
cd /opt/hongqingting_runner

# 加密一份配置 → 输出 sk-xxx
cat config.json | ./venv/bin/python -m vault add "label-here"
# → sk-jtYKD2A-...

# 列出所有 token（只显示 hash 索引 + label + 创建时间）
./venv/bin/python -m vault list

# 删除某个 sk
./venv/bin/python -m vault delete sk-xxx

# 解密验证（应输出原始 JSON）
./venv/bin/python -m vault decrypt sk-xxx
```

`config.json` 必填字段（不再需要 `proxyUrl`，由 `docs/proxy.json` 单独管理）：

```json
{
  "authUrl": "http://your-mock/.../DflyServer",
  "summaryUrl": "http://your-mock/.../getRunDataSummary",
  "uploadUrl": "http://your-mock/.../uploadRunData",
  "schoolNo": "10755",
  "passwordPrefix": "Stu",
  "queryUid": "...",
  "uidList": "uid_a\nuid_b\nuid_c"
}
```

## 加密设计

- 每个 sk-xxx 的 Fernet 密钥 = `urlsafe_b64(SHA-256(sk))`
- 索引到 vault.json 的 key = `SHA-256("idx::" + sk)[:32]`（用不同前缀避免与加密密钥共用 hash）
- 对手即便拿到 `vault.json` 也解不出明文，因为没有 sk
- sk 丢了 → 数据无法找回，重新加密一份新的
- vault 文件强制 0600，目录 0700

## 部署变更

```bash
# 安装新依赖
/opt/hongqingting_runner/venv/bin/pip install cryptography

# 部署 / 升级代码
scp app.py vault.py root@server:/opt/hongqingting_runner/
systemctl restart hongqingting-api
```

## cloudflared URL 变化处理

URL 重启会变。两步恢复：

```bash
# 1) 服务器上拿当前 URL
ssh root@server 'curl -s http://127.0.0.1:8000/tunnel-info'

# 2) 本地改 docs/proxy.json 里的 proxyUrl，commit + push
```

GitHub Actions 1–2 分钟内自动部署，前端 `fetch('proxy.json')` 拿到新 URL。
