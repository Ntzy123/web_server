# ============================================================================
# Makefile - web_server
# Cross-platform (Windows / Linux / macOS)
# ============================================================================

# --- OS detection ---
ifeq ($(OS),Windows_NT)
    PYTHON      = python
    VENV_PYTHON = .venv\Scripts\python.exe
    VENV_PIP    = .venv\Scripts\pip.exe
    SEP         = ;
    NULL        = nul
else
    PYTHON      = python3
    VENV_PYTHON = .venv/bin/python
    VENV_PIP    = .venv/bin/pip
    SEP         = :
    NULL        = /dev/null
endif

APP_NAME = web_server

.PHONY: help setup mirror run build test

# --- File target: only creates venv when the Python interpreter is missing ---
$(VENV_PYTHON):
	$(PYTHON) -m venv .venv

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  setup    Create venv, clone missing external deps & install"
	@echo "  mirror   Switch pip to Tsinghua mirror"
	@echo "  run      Run the application"
	@echo "  test     Run tests with pytest"
	@echo "  build    Build wheel/sdist into dist/"
	@echo "  help     Show this help"

setup: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip > $(NULL) 2>&1
	$(VENV_PIP) install -e .
	@$(PYTHON) setup_deps.py
	$(VENV_PIP) install -e ../get-easycheck-url
	@echo "Setup complete."

mirror: $(VENV_PYTHON)
	$(VENV_PIP) config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
	@echo "Mirror set."

run: $(VENV_PYTHON)
	@$(VENV_PYTHON) -m $(APP_NAME)

test: $(VENV_PYTHON)
	$(VENV_PIP) install pytest pytest-cov > $(NULL) 2>&1
	$(VENV_PYTHON) -m pytest tests/ -v --cov=src/$(APP_NAME) --cov-report=term-missing

build: $(VENV_PYTHON)
	$(VENV_PIP) install build > $(NULL) 2>&1
	$(VENV_PYTHON) -m build
	@echo "Build complete: dist/"
