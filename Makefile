.PHONY: sync lint build preview run clean help

# Default target
help:
	@echo "RenderBrains Docs — available commands:"
	@echo ""
	@echo "  make sync     Convert vault/ notes to docs/ (wiki links → relative links)"
	@echo "  make lint     Validate frontmatter and links in publishable notes"
	@echo "  make build    Render the Quarto site to _site/"
	@echo "  make preview  Start a live-reload preview server"
	@echo "  make run      Run sync + lint + build (full pipeline)"
	@echo "  make clean    Remove _site/ and Python cache files"
	@echo ""

sync:
	uv run python scripts/sync.py

lint:
	uv run python scripts/lint.py

QUARTO ?= quarto
ifeq ($(OS),Windows_NT)
  QUARTO_LOCAL := $(LOCALAPPDATA)/Programs/Quarto/bin/quarto.exe
  ifneq ($(wildcard $(QUARTO_LOCAL)),)
    QUARTO := $(QUARTO_LOCAL)
  endif
endif

build:
	"$(QUARTO)" render

preview:
	"$(QUARTO)" preview

run: sync lint build

clean:
	rm -rf _site
	find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -not -path './.git/*' -delete 2>/dev/null || true
