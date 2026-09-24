# Contributing

Contributions are welcome through GitHub issues and pull requests. Please open
an issue before substantial features, interaction changes, or interface
redesigns so the approach and scope can be discussed. Small fixes and
documentation improvements may be submitted directly.

Participation is governed by the [Code of conduct](CODE_OF_CONDUCT.md).

## Development setup

Use one of the latest Python version in a virtual environment:

```console
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,globe]"
```

On Windows, use `.venv\Scripts\python` instead. For coordinated work against a
sibling core checkout, install with
`python -m pip install -e ../cf-regions -e ".[dev,globe]"`.

Before opening a pull request, run:

```console
ruff check src tests
mypy src
QT_QPA_PLATFORM=offscreen pytest --cov=cfregions_gui --cov-report=term-missing
python -m build
twine check dist/*
```

On Windows, set `QT_QPA_PLATFORM=offscreen` using the shell's native syntax.
Keep region logic in `cf-regions`; this project should remain a native
presentation layer without a browser or local HTTP server. User-visible changes
need tests and a changelog entry.

By contributing, you agree that your contribution is distributed under
GPL-3.0-or-later.
