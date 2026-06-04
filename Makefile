# AISECOPS 开发命令 —— 自用单节点。运行 `make` 看全部命令。
.DEFAULT_GOAL := help
PY  := .venv/bin/python
BIN := .venv/bin

.PHONY: help venv install dev down obs test lint fmt type check clean

help:  ## 列出所有命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

venv:  ## 建 Python 3.11 虚拟环境
	uv venv --python 3.11

install:  ## 安装依赖（含 dev）
	uv pip install -e ".[dev]"

dev:  ## 起核心数据层（PG + Redis）
	docker compose up -d db redis

down:  ## 停所有容器
	docker compose down

obs:  ## 额外起可观测栈（Prometheus / Grafana / OTel）
	docker compose --profile obs up -d

test:  ## 跑测试（stub 模式，不烧 token）
	$(PY) -m pytest -q

lint:  ## ruff 检查
	$(BIN)/ruff check .

fmt:  ## ruff 自动格式化
	$(BIN)/ruff format .

fmt-check:  ## ruff 格式检查（不改文件，CI 用）
	$(BIN)/ruff format --check .

type:  ## mypy 类型检查
	$(BIN)/mypy src

check: lint fmt-check type test  ## 一把过：lint + 格式 + type + test（与 CI 完全一致）

clean:  ## 清 __pycache__ 缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
