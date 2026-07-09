"""无依赖 .env 加载器。

把仓库根目录 .env 的 KEY=VALUE 注入 os.environ（已存在的值不覆盖），
使 DEEPSEEK_API_KEY / NEO4J_PASSWORD 等密钥脱离源码硬编码。

在导入 orchestrator / kg_adapter 之前调用 load_env()，确保 kg_adapter
导入时能读到 NEO4J_PASSWORD 模块级常量。
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env(path: str | Path | None = None) -> None:
    target = Path(path) if path else Path(__file__).resolve().parent / ".env"
    if not target.exists():
        return
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


# 模块导入时自动加载一次
load_env()
