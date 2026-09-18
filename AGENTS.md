# Repository guidance

This repository creates one NetNewsWire theme. Before editing, run
`uv run nnw-theme init` if `.nnw-theme-uninitialized` exists. Prefer CSS changes;
change `template.html` only when the requested structure or behavior requires it.

Use `uv` for every Python command and Python 3.14. After changing Python, run:

```sh
uv run ruff check --fix .
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
```

Use the installed `playwright-cli` through `uv run nnw-theme`; never use `npx` for
local browser validation. Finish theme work with `uv run nnw-theme check` and report
the preview path. Do not change `ThemeIdentifier` or the `.nnwtheme` bundle name after
the first release. Increase the plist `Version` before every release.

Local edits, renders, checks, and packages are safe to perform as requested. Creating
a GitHub release, opening a pull request, changing repository topics, or otherwise
mutating GitHub requires the user’s explicit intent. Theme and fixture HTML/JavaScript
are untrusted executable inputs; keep browser checks loopback-only and deny external
requests.
