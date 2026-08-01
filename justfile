@_default:
	just --list

@bootstrap:
	uv pip install --requirement requirements.in

# install the prek git hooks so lint runs on commit
@install-hooks:
	prek install

@lint:
	prek run --all-files

# lint without prek, straight through ruff
@ruff:
	-python -m ruff check --fix
	-python -m ruff format

@test *ARGS:
	python -m pytest {{ ARGS }}

@update-hooks:
	prek auto-update
