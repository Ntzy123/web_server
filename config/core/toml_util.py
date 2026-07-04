# config/core/toml_util.py
"""简化的 TOML 读写工具（利用 stdlib tomllib 读取，手动序列化写入）"""

import os

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


def load(filepath, default=None):
    """读取 TOML 文件，文件不存在时返回 default"""
    if not os.path.exists(filepath):
        return default
    with open(filepath, 'rb') as f:
        return tomllib.load(f)


def dump(obj, filepath):
    """将简单 Python dict 写入 TOML 文件（原子写入）。

    支持的 obj 结构：
      - 顶层 k=v 对
      - 顶层 k 为 list[dict] → 写为 [[k]] 表数组
    """
    lines = []
    # 先写简单 k=v
    for key, value in obj.items():
        if isinstance(value, list) and value and all(isinstance(i, dict) for i in value):
            continue  # 表数组统一在后面写
        if isinstance(value, dict):
            continue  # 暂不支持嵌套表
        lines.append(f"{key} = {_fmt(value)}")

    # 再写表数组 [[key]]
    for key, value in obj.items():
        if not (isinstance(value, list) and all(isinstance(i, dict) for i in value)):
            continue
        if not value:
            lines.append(f"{key} = []")
            continue
        for item in value:
            lines.append(f"\n[[{key}]]")
            for k, v in item.items():
                lines.append(f"{k} = {_fmt(v)}")

    content = "\n".join(lines) + "\n"
    tmp = filepath + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp, filepath)


def _fmt(v):
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        escaped = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    if isinstance(v, list):
        if not v:
            return "[]"
        items = ", ".join(_fmt(i) for i in v)
        return f"[{items}]"
    return '""'
