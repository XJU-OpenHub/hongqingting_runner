# 红蜻蜓接口实验台 · 教学页

把 `hongqingting.py` 的发包逻辑搬到浏览器，纯静态前端，所有目标地址、学校代码、密码盐都在 UI 上配置。可部署到 GitHub Pages。

仅用于教学。请把目标 URL 指向你自己授权的服务器。

## 目录结构

```
docs/
├── index.html         主页面（配置面板 + 三个接口操作区 + 日志）
├── app.js             浏览器端业务逻辑：MD5 → URL 编码 → 轨迹改写 → gzip → fetch
├── styles.css
├── README.md          本文件
└── assets/
    ├── location_1km
    ├── location_1_6km
    ├── location_1_16km
    └── location_12km
```

## 本地预览

```bash
cd docs
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000
```

本地预览不会受 HTTPS 混合内容限制，可以直接打到任意 HTTP 后端，调试 CORS / 服务器逻辑都很方便。

## 部署到 GitHub Pages

1. 把这个仓库推到 GitHub。
2. 仓库 **Settings → Pages**：
   - Source: `Deploy from a branch`
   - Branch: `main` / `master`，文件夹选 **`/docs`**
3. 几十秒后访问 `https://<你的用户名>.github.io/<仓库名>/`。

## 学生侧使用流程

1. 在 **① 服务器配置** 里填好接口 URL、学校代码、UID 列表，点 *保存到本地*（写入 localStorage）。
2. 在 **② 登录验证** 输入学号 → *构造请求* 看 body / MD5 / URL 编码细节，再 *构造并发送*。
3. **③ 查询里程**：演示 gzip 压缩 body 后 POST 的流程；返回 JSON 会被解析展示。
4. **④ 上传跑步数据**：选预设、设置日期偏移和 UID 索引，先 *生成预览* 看时间 / 距离 / 配速 / 轨迹改写细节，再 *生成并发送*；可设循环次数批量跑多天。
5. **⑤ 实时日志** 同步显示每一步的状态。

## 后端要满足什么

为了让浏览器能成功打你的服务器：

| 需求 | 原因 | 怎么配 |
|------|------|--------|
| **HTTPS** | GitHub Pages 是 HTTPS，浏览器拒绝 HTTPS→HTTP 的混合内容 | Caddy 自动签 / Cloudflare Tunnel / Let's Encrypt |
| **CORS 允许来源** | 跨源 fetch 默认被拒 | 响应头 `Access-Control-Allow-Origin: https://<你>.github.io`（或 `*`） |
| **CORS 允许方法/头** | POST + Content-Type 触发预检 | `Access-Control-Allow-Methods: POST, OPTIONS`<br>`Access-Control-Allow-Headers: Content-Type` |
| **OPTIONS 预检处理** | 浏览器先发 OPTIONS | 让 OPTIONS 返回 204 + 上述 CORS 头 |
| **接受 gzip 字节** | 上传/查询接口的 body 是 gzip 压缩后的字节 | 服务器解析时检测 magic bytes (`1f 8b`) 自动 gunzip，或显式声明用 `Content-Encoding: gzip`（注意：显式声明会让浏览器把 `Content-Encoding` 当成自定义头触发预检） |

最小可用的 Flask 后端示例：

```python
from flask import Flask, request, jsonify
from flask_cors import CORS  # pip install flask-cors
import gzip

app = Flask(__name__)
CORS(app)  # 教学环境放开所有来源

def maybe_gunzip(raw: bytes) -> str:
    if len(raw) >= 2 and raw[0] == 0x1f and raw[1] == 0x8b:
        return gzip.decompress(raw).decode('utf-8', errors='replace')
    return raw.decode('utf-8', errors='replace')

@app.route('/cloud/DflyServer', methods=['POST'])
def auth():
    return jsonify({"status": "ok", "received": request.get_data(as_text=True)})

@app.route('/Api/webserver/getRunDataSummary', methods=['POST'])
def summary():
    body = maybe_gunzip(request.get_data())
    import time
    return jsonify({"m": 12345, "lasttime": int(time.time()), "received": body})

@app.route('/Api/webserver/uploadRunData', methods=['POST'])
def upload():
    body = maybe_gunzip(request.get_data())
    print("[UPLOAD]", body[:300])
    return jsonify({"status": "ok", "size": len(body)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 已知差异 / 注意点

- **User-Agent**：浏览器禁止 JS 改 UA。原 Python 里设置的 `okhttp/...` / `Dalvik/...` 都不会生效，发出去的就是浏览器自己的 UA。如果你的服务器要按 UA 鉴别，请放宽规则或改在后端测。
- **Content-Encoding 声明**：当前实现和原 Python 一样，body 是 gzip 字节但**不**显式声明 `Content-Encoding`，由服务器按 magic bytes 自检。这样可以避开 CORS 预检里对自定义头的额外配置。
- **轨迹改写逻辑**：和 `hongqingting.py` 中正则等价 —— 切 `@`、抓首段坐标、重写第二段时间戳；最末 `@` 去掉。可在 `docs/app.js` 中 `rewriteTrajectory()` 内对照阅读。
- **MD5 库**：通过 jsDelivr CDN 引入 `blueimp-md5`。要离线/自托管，把对应文件下载到 `docs/vendor/`，再改 `index.html` 里的 `<script src=...>`。
- **配置存储**：所有配置只写浏览器 localStorage，不上传到任何外部服务。
