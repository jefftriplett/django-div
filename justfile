@_default:
	just --list

@bootstrap:
	uv sync

@build:
	uv build

@bump *ARGS:
	uv tool run bumpver update --allow-dirty {{ ARGS }}

@bump-dry *ARGS:
	just bump --dry {{ ARGS }}

# refresh the MDN browser-compat-data snapshot the tests check against
@compat *ARGS:
	uv run python scripts/gen_compat.py {{ ARGS }}

@docs:
	uv run zensical serve

@docs-build:
	uv run zensical build --clean --strict
	uv run python scripts/gen_llms.py site

@example:
	uv run --with rich --with typer python examples/example.py

# install the prek git hooks so lint runs on commit
@install-hooks:
	uv run prek install

@lint:
	uv run prek run --all-files

@lock:
	uv lock

# bump the CalVer version, relock, and push the tag; CI publishes to PyPI
release *ARGS:
	#!/usr/bin/env bash
	set -euo pipefail
	just bump {{ ARGS }}
	just lock
	version="$(grep -m1 '^current_version' pyproject.toml | cut -d'"' -f2)"
	git add uv.lock
	git commit --amend --no-edit
	git tag -d "$version"
	git tag -a "$version" -m "$version"
	git push --follow-tags

# lint without prek, straight through ruff
@ruff:
	-uv run ruff check --fix
	-uv run ruff format

# regenerate the type stub after changing the public API
@stub:
	uv run python scripts/gen_stub.py

@test *ARGS:
	uv run pytest {{ ARGS }}

@update-hooks:
	uv run prek auto-update
