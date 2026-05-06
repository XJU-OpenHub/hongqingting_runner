# docs/ — 教程页源码

这是 GitHub Pages 发布的教程内容。**纯静态、无 JS 业务逻辑**。

## 内容

- `index.html` — 教程正文，分八节：项目说明、为什么必须本地运行（Mixed Content / CORS 讲解）、本地环境、Mock 服务器示例、三类请求结构剖析、轨迹文件格式、服务端反作弊视角、思考题
- `styles.css` — 长文阅读式排版（自适应明/暗主题）
- `assets/location_*km` — 原始轨迹文件，作为第六节的样本数据

## 部署方式

仓库使用 **GitHub Actions** 部署 Pages（见 `.github/workflows/pages.yml`）。
推到 `main` 后工作流自动把 `docs/` 上传为 Pages artifact 并发布。

> **首次启用**：仓库 Settings → Pages → Build and deployment → Source 选 **GitHub Actions**（如果之前是 *Deploy from a branch* 需要切换一次）。

## 本地预览

```bash
cd docs
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000
```

## 关于实际跑 Python 脚本

教程只是讲解协议结构。要实际跑 `hongqingting.py` 看请求行为，参考教程 第三节（环境准备）和第四节（Mock 服务器示例）。**只把目标 URL 指向你自己授权、自己控制的服务器**，不要碰生产系统。
