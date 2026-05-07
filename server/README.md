# server/ — 教学代理（FastAPI + cloudflared）

把 Python `requests` 能做、浏览器 `fetch` 做不了的活（gzip 压缩、修改 User-Agent、跨源、
HTTPS → HTTP 直接调）放在一台代理服务器上。前端通过 cloudflared HTTPS 快速隧道调用本服务。

## 架构

```
浏览器 (GitHub Pages, HTTPS)
   │  fetch JSON → POST /proxy/auth | /proxy/summary | /proxy/upload
   ▼
cloudflared quick tunnel (https://xxx-xxx.trycloudflare.com)
   │
   ▼
FastAPI uvicorn @ 127.0.0.1:8000      ← 本目录代码
   │  组装 form-urlencoded / gzip / MD5 / 轨迹时间戳重写
   ▼
你授权的教学 mock (HTTP, 内网或公网都行)
```

## 三个端点

| 端点 | 等价于原 Python 函数 | 备注 |
| --- | --- | --- |
| `POST /proxy/auth` | `GetStuInfo()` | form-urlencoded，密码 = `passwordPrefix + studentNo` 取 MD5 |
| `POST /proxy/summary` | `GetRunMeter()` | gzip JSON，需要 `queryUid` |
| `POST /proxy/upload` | `PostRunData_*km()` | gzip JSON，重写每帧轨迹时间戳到 `[begintime, begintime+usetime]` 区间 |
| `GET  /tunnel-info` | — | 读 cloudflared journal，返回当前 trycloudflare URL |

每个 POST 响应都附带 `debug` 字段：组装出来的明文 body、MD5、headers、gzip 长度——前端
教学面板直接展示给学生看。

## 部署（Ubuntu 22.04 已实测）

```bash
# 1) 安装系统包
apt-get install -y python3-venv

# 2) 安装 cloudflared（如 GitHub 直连慢，本地下完 scp 上去）
dpkg -i cloudflared-linux-amd64.deb

# 3) 安装 Python 依赖
mkdir -p /opt/hongqingting_runner && cd /opt/hongqingting_runner
python3 -m venv venv
./venv/bin/pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    fastapi "uvicorn[standard]" httpx

# 4) 把 app.py 放到 /opt/hongqingting_runner/

# 5) systemd
systemctl daemon-reload
systemctl enable --now hongqingting-api.service
systemctl enable --now cloudflared-tunnel.service
```

systemd unit 文件示例见 `unit-files/`。

## 拿当前 cloudflared URL

```bash
journalctl -u cloudflared-tunnel -n 50 | grep trycloudflare
# 或
curl http://127.0.0.1:8000/tunnel-info
```

## 排错

- `502 upstream error` — 代理能转发，但目标 mock 不可达。检查 mock 是否开着、IP/端口对不对。
- 前端 fetch 报 CORS — 已配 `allow_origins=["*"]`，如果还报，看是不是 cloudflared URL 拼错了
  （URL 重启会变）。
- `usetime <= 0` — `baseUseTime` 太短，或 `useTimeJitter` 被 `random.randint` 减得太多。
  调大 `baseUseTime`。
