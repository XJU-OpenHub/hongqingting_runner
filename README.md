# 红蜻蜓脚本工具 🐉

这是一个基于 Python 的红蜻蜓刷公里数项目。

> ⚠️ 本项目会向远端服务器发送真实 HTTP 请求。请仅在你本人账号、合法授权和合规场景下使用，不要用于伪造、篡改或代替他人提交数据。

## 项目结构 📁

```text
.
├── hongqingting.py      # 主脚本
├── requirements.txt     # Python 依赖
├── location_1km         # 1km 轨迹数据
├── location_1_6km       # 1.6km 轨迹数据
├── location_1_16km      # 1.16km 轨迹数据
└── location_12km        # 12km 轨迹数据
```

## 环境准备 🛠️

建议使用 Python 3.8 或更高版本。

### 1. 创建虚拟环境

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果你的 pip 因为 `requirements.txt` 编码问题无法读取依赖文件，可以直接安装核心依赖：

```bash
python -m pip install requests
```

项目中使用到的其他模块如 `gzip`、`hashlib`、`json`、`random`、`re`、`time` 均为 Python 标准库，无需额外安装。

## 脚本使用 🚀

在项目根目录运行：

```bash
python hongqingting.py
```

运行后脚本会：

1. 提示输入学号。
2. 使用默认规则 `Stu + 学号` 生成密码并进行学生信息验证。
3. 查询当前跑步里程数据。
4. 根据 `__main__` 中的循环逻辑，调用上传函数生成并提交跑步轨迹数据。

当前主流程位于 `hongqingting.py` 末尾：

```python
if __name__ == '__main__':
    no = GetStuInfo()
    GetRunMeter(no)

    for i in range(0, 30):
        PostRunData_1_6km(no, i-0.3, 2)
```

⚠️ 注意：当前 `PostRunData_1_6km` 函数中的确认输入逻辑已被注释，调用后会直接发送上传请求。运行脚本前请务必确认循环次数、日期偏移、轨迹文件和账号信息都符合你的预期。

## 主要函数说明 🧩

| 函数 | 作用 |
| --- | --- |
| `GetStuInfo()` | 输入学号，按 `Stu + 学号` 规则生成密码并请求学生信息 |
| `GetRunMeter(no)` | 查询指定学号的跑步里程汇总 |
| `PostRunData_12km(no, day, uid)` | 使用 `location_12km` 轨迹生成约 12km 数据 |
| `PostRunData_1_6km(no, day, uid)` | 使用 `location_1_6km` 轨迹生成约 1.6km 数据 |
| `PostRunData_1_16km(no, day, uid)` | 生成约 1.16km 数据 |

参数含义：

- `no`：学号。
- `day`：日期偏移，表示相对当前时间往前推的天数。
- `uid`：`uid_list` 中的设备标识索引。

## 轨迹文件说明 🗺️

`location_*` 文件保存了预设轨迹点。脚本会读取对应轨迹文件，并根据本次生成的开始时间、结束时间和用时，重新填充轨迹点时间戳。

如果你要调整路线或距离，需要同步检查：

- 上传函数中读取的轨迹文件名。
- `distance` 的随机范围。
- `begintime`、`endtime` 和 `usetime` 的生成逻辑。
- 主流程中调用的是哪个 `PostRunData_*` 函数。

## 常见问题 💡

### `ModuleNotFoundError: No module named 'requests'`

说明依赖没有安装成功，请先激活虚拟环境，再执行：

```bash
python -m pip install requests
```

### 请求失败或返回异常

可能原因包括：

- 网络无法访问目标服务器。
- 目标接口地址或端口发生变化。
- 学号、密码规则或账号状态不正确。
- 请求头、设备标识或轨迹数据不符合服务端校验。

### 只想查询数据，不想上传

请在运行前检查 `hongqingting.py` 末尾的 `__main__` 代码，保留 `GetStuInfo()` 和 `GetRunMeter(no)`，并移除或注释上传循环。

## 免责声明 ⚖️

本项目仅供 Python 网络请求、数据压缩、脚本流程和接口调试学习参考。使用者需要自行确认使用场景的合法性、合规性和授权范围，并对运行脚本产生的结果负责。
