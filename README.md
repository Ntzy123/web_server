# web_server

个人 Web 服务器（Flask + waitress）：下载站、配置页、桶装水订单统计、人员设备状态、WBTools 版本 API。

## 目录结构

```
src/web_server/
├── __init__.py        # 导出 app / init_app / main
├── __main__.py        # python -m web_server 入口
├── core.py            # Flask 应用与全部路由
├── utils.py           # TOML 读写（stdlib tomllib + 手写序列化）
├── lib/
│   ├── api_defs.py    # 万物云接口定义与认证头
│   └── night_check.py # 夜查工单查询（接口暂时禁用）
├── templates/         # Jinja2 模板（随包分发）
└── static/            # CSS / 图片（随包分发）
docs/                  # 接口文档
tests/                 # pytest
```

## 开发

```bash
make setup     # 建 .venv、pip install -e .、克隆并安装外部依赖
make run       # python -m web_server，监听 0.0.0.0:5000
make test
make build     # 构建 wheel/sdist 到 dist/
```

外部依赖（非 PyPI 包）由根目录 `setup_deps.py` 克隆到**同级目录**，再以 editable 方式安装：

| 仓库                                                  | 安装位置                  |
| ----------------------------------------------------- | ------------------------- |
| https://github.com/Ntzy123/get-easycheck-url          | `../get-easycheck-url`    |

## 运行时目录（相对当前工作目录，首次启动自动创建）

| 目录              | 用途                                     |
| ----------------- | ---------------------------------------- |
| `download/`       | 下载站文件根目录                         |
| `config_runtime/` | `settings.toml`、`secret_key.txt`、人员设备状态配置 |
| `cache/`          | 管理员 Cookie、人员设备状态与历史缓存    |

管理员密钥由 `config_runtime/secret_key.txt` 提供，用于上传与配置页鉴权。
