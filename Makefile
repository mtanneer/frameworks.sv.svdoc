.PHONY: help install lint test check build twine-check smoke-test verify release clean

VENV := .venv/bin
VERSION := $(shell $(VENV)/python -c "import tomllib,sys; sys.stdout.write(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>/dev/null || \
            grep -m1 '^version' pyproject.toml | cut -d'"' -f2)
WHEEL := dist/svdoc-$(VERSION)-py3-none-any.whl
SDIST := dist/svdoc-$(VERSION).tar.gz

help:
	@echo "svdoc release Makefile (version: $(VERSION))"
	@echo ""
	@echo "  make lint          ruff check"
	@echo "  make test          pytest with coverage (matches CI's --cov-fail-under=80)"
	@echo "  make check         lint + test"
	@echo "  make build         clean, build sdist+wheel into dist/"
	@echo "  make twine-check   validate built artifacts' metadata"
	@echo "  make smoke-test    install the built wheel into a throwaway venv, run svdoc"
	@echo "  make verify        check + build + twine-check + smoke-test (everything short of publishing)"
	@echo "  make release       verify, then tag vVERSION + push; release.yml publishes to PyPI + GitHub
	@echo "  make clean         remove dist/, build/, egg-info"

install:
	python3 -m venv .venv
	$(VENV)/pip install -e ".[dev]"

lint:
	$(VENV)/ruff check .

test:
	$(VENV)/python -m pytest --cov=svdoc --cov-report=term-missing --cov-fail-under=80

check: lint test

clean:
	rm -rf dist build svdoc.egg-info

build: clean
	$(VENV)/python -m build

twine-check: build
	$(VENV)/python -m twine check $(WHEEL) $(SDIST)

smoke-test: build
	rm -rf tmp/smoke_venv
	python3 -m venv tmp/smoke_venv
	tmp/smoke_venv/bin/pip install --quiet $(WHEEL)
	tmp/smoke_venv/bin/svdoc spike/example.sv --out mmd
	rm -f spike/example.mmd
	rm -rf tmp/smoke_venv

verify: check twine-check smoke-test
	@echo "verify passed for v$(VERSION) -- dist/ is ready to publish"

release: verify
	@read -p "Tag and push v$(VERSION) (CI publishes to PyPI + GitHub)? Type version to confirm: " c && [ "$$c" = "$(VERSION)" ] || (echo aborted; exit 1)
	git tag v$(VERSION) && git push origin v$(VERSION)
