# run all check tasks
[group("check")]
check: format check-code check-type check-security check-hooks check-audit

# check code quality
[group("check")]
check-code:
    uv run ruff check {{SOURCES}} {{TESTS}}

# check code security
[group("check")]
check-security:
    uv run bandit --recursive --configfile=pyproject.toml {{SOURCES}}

# check code typing with ty (astral type checker)
[group("check")]
check-type:
    uv run ty check {{SOURCES}}

# check pre-commit hooks
[group("check")]
check-hooks:
    uv run pre-commit run --all-files

# scan for vulnerabilities in dependencies
[group("check")]
check-audit:
    uv sync --all-groups --all-extras
    uv run pip-audit --local --skip-editable
