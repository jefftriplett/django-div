@_default:
	just --list

@bootstrap:
	uv sync

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

# lint without prek, straight through ruff
@ruff:
	-uv run ruff check --fix
	-uv run ruff format

@test *ARGS:
	uv run pytest {{ ARGS }}

@update-hooks:
	uv run prek auto-update
