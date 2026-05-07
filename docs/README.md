# docs/ — 教学演示页源码

GitHub Pages 部署的内容。这一版从"纯讲义"改成了**可在浏览器里点的运行器**——后端代理 +
JSON 配置驱动，配合服务器侧的 `cloudflared` 隧道，把 Python `requests` 能做的事在浏览器里
原样复现一遍，方便课堂演示。

## 内容

- `index.html` — 运行器 UI：配置导入 + 登录 / 查里程 / 上传 / 批量上传 / 教学说明
- `styles.css` — 主题（自适应明/暗）+ 表单/Tab/调试面板样式
- `config.example.json` — 配置 JSON 样板，按这个 shape 填你的课堂 mock URL 即可
- `assets/location_*km` — 预录轨迹文件，前端 `fetch` 后发给代理

## 后端代理

代码在仓库根目录 `server/app.py`，部署文档见 `server/README.md`。  
浏览器 → cloudflared HTTPS 隧道 → FastAPI 代理（127.0.0.1:8000）→ 你授权的 mock。

## 部署方式

`.github/workflows/pages.yml` 监听 `docs/**`，推到 `main` 自动部署。

## 关于 `proxyUrl` 易变性

cloudflared **quick tunnel** 每次进程重启 URL 会变（`xxx-xxx.trycloudflare.com` 部分）。
拿当前 URL：

```bash
ssh root@your-server
journalctl -u cloudflared-tunnel -n 50 | grep trycloudflare
# 或直接 curl 代理自己的 /tunnel-info
```

把新 URL 写到你的 JSON 配置里重新导入即可，不需要改代码。

## 使用流程

1. 老师 SSH 上代理服务器，确认 `hongqingting-api` 和 `cloudflared-tunnel` 两个 systemd 服务是 active。
2. 拿当前 cloudflared URL，填进 `config.example.json` 中的 `proxyUrl`。
3. 把 `authUrl/summaryUrl/uploadUrl` 换成课堂 mock 的地址，`queryUid/uidList` 换成 mock 里设的样本数据。
4. 学生打开 GitHub Pages → 配置导入栏粘贴 JSON → 各 Tab 操作。
5. 每次操作都能在"请求构造细节（教学）"折叠面板里看到组装出来的明文 body / MD5 / gzip 长度 / 轨迹时间戳序列，给学生讲反作弊检测点。

## 课程定位（务必看）

把 `authUrl/summaryUrl/uploadUrl` **只指向自己授权、自己控制的教学 mock**。
指向真实生产系统提交伪造数据违反学术诚信和大多数地方法律法规，本课程材料明确不为此提供帮助。
