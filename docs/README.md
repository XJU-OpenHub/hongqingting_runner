# docs/ — 教学演示页（GitHub Pages）

## 本目录文件

- `index.html` — 运行器 UI：sk-API Key 输入 + 查询里程 + 批量上传
- `styles.css` — 主题（毛玻璃 / 二次元背景 / Apple 风按钮）+ 进度条
- `proxy.json` — **唯一一个会变的文件**：当前 cloudflared 隧道 URL
- `assets/` — 二次元背景 SVG、轨迹文件副本

## 运行流程

1. 学生打开 GitHub Pages 链接
2. 在 "API Key" 输入框粘贴老师下发的 `sk-xxx`，点"保存并验证"
3. 验证通过后下面两张卡片可用：
   - **查询跑步里程**：输入学号 → 显示当前累计公里数
   - **批量上传跑步数据**：学号 + 轨迹 + 往前推几天 + 每天偏移 → 进度条 → 完成后自动显示新里程

## sk-xxx 的工作机制

- 学生看到的只有 sk-xxx，没有 URL / queryUid / uidList。
- sk-xxx 在浏览器仅存 localStorage，`POST` 时作为 body 字段发给代理。
- 代理在服务器解密 vault 拿到真实 URL/uid，再发上游请求。
- 仓库里没有任何敏感字段。

## 当 cloudflared URL 变化

cloudflared quick tunnel 每次重启换 URL。维护流程：

```bash
# 1) 服务器上看当前 URL
ssh root@server 'curl -s http://127.0.0.1:8000/tunnel-info'
# → {"latestUrl":"https://xxx-xxx.trycloudflare.com",...}

# 2) 编辑 docs/proxy.json，把 proxyUrl 改成最新值，commit + push
```

GitHub Actions 1–2 分钟内自动部署。学生页面下次刷新自动用新 URL，sk-xxx 不变。

## 部署

`.github/workflows/pages.yml` 监听 `docs/**`，推到 `main` 自动部署到
`https://xju-openhub.github.io/hongqingting_runner/`。

## 教学定位

把 vault 里加密的 `authUrl/summaryUrl/uploadUrl` 只指向你授权、自己控制的教学 mock。
指向真实生产系统提交伪造数据违反学术诚信和大多数地方法律法规，本课程材料明确不为此提供帮助。
