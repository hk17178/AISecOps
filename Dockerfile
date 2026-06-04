# AISECOPS 应用镜像 —— 多阶段构建（uv + Python 3.11）
# 说明：当前代码 0 行，本镜像先把依赖与运行骨架备好；有了 FastAPI 入口即可起服务。

# ---- 构建阶段：装依赖 ----
FROM python:3.11-slim AS builder

# uv：极快的包管理器（与本地一致，见 ADR-0005）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 先只拷依赖清单，利用层缓存
COPY pyproject.toml ./
# 装运行依赖到独立 venv（不含 dev）
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install -e .

# ---- 运行阶段：精简镜像 ----
FROM python:3.11-slim AS runtime

# 非 root 运行（安全开发基线）
RUN useradd -m -u 10001 appuser

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src ./src
COPY pyproject.toml ./

USER appuser

# 入口占位：有了 FastAPI app 后改为
#   CMD ["uvicorn", "aisecops.L01_human_interface.api:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "-c", "import aisecops; print('AISECOPS image OK —— 待接入 FastAPI 入口')"]
