.PHONY: help install lint test check build twine-check smoke-test verify \
        publish-pypi gh-release release clean

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
	@echo "  make publish-pypi  upload dist/ to PyPI (irreversible -- asks for confirmation)"
	@echo "  make gh-release    tag vVERSION and create a GitHub release with dist/ attached"
	@echo "  make release       verify, then publish-pypi, then gh-release, in order"
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

publish-pypi: verify
	@echo "About to upload v$(VERSION) to PyPI. This is IRREVERSIBLE."
	@read -p "Type the version number ($(VERSION)) to confirm: " confirm && [ "$$confirm" = "$(VERSION)" ] || (echo "aborted"; exit 1)
	TWINE_USERNAME=__token__ TWINE_PASSWORD=$$(security find-generic-password -s "pypi-token" -w) \
		$(VENV)/python -m twine upload $(WHEEL) $(SDIST)

gh-release:
	gh release create v$(VERSION) $(WHEEL) $(SDIST) --title "v$(VERSION)" --generate-notes

release: publish-pypi gh-release
	@echo "v$(VERSION) released to PyPI and GitHub"
