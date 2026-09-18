from __future__ import annotations

import plistlib
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_THEME_FILES = ("Info.plist", "template.html", "stylesheet.css")
OPTIONAL_THEME_FILE_PREFIXES = ("LICENSE", "NOTICE")
PLACEHOLDER_MARKER = ".nnw-theme-uninitialized"


class ThemeError(RuntimeError):
    """A user-actionable theme project error."""


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "fixtures").is_dir():
            return candidate
    raise ThemeError("run this command inside the theme repository")


def find_theme(root: Path) -> Path:
    themes = sorted(path for path in root.glob("*.nnwtheme") if path.is_dir())
    if len(themes) != 1:
        names = ", ".join(path.name for path in themes) or "none"
        raise ThemeError(
            f"expected one .nnwtheme directory at the repository root; found {names}"
        )
    return themes[0]


def read_plist(theme: Path) -> dict[str, Any]:
    path = theme / "Info.plist"
    try:
        with path.open("rb") as stream:
            value = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException) as error:
        raise ThemeError(f"{path}: invalid property list: {error}") from error
    if not isinstance(value, dict):
        raise ThemeError(f"{path}: the top-level value must be a dictionary")
    return value


def write_plist(path: Path, metadata: dict[str, Any]) -> None:
    with path.open("wb") as stream:
        plistlib.dump(metadata, stream, fmt=plistlib.FMT_XML, sort_keys=False)


def read_fixture(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ThemeError(f"{path}: invalid fixture: {error}") from error
    if not isinstance(value, dict):
        raise ThemeError(f"{path}: fixture must be a table")
    return value


def fixture_paths(root: Path, names: list[str] | None = None) -> list[Path]:
    if not names:
        paths = sorted((root / "fixtures").glob("*.toml"))
    else:
        paths = []
        for name in names:
            path = root / "fixtures" / (name if name.endswith(".toml") else f"{name}.toml")
            if not path.is_file():
                raise ThemeError(f"fixture not found: {path}")
            paths.append(path)
    if not paths:
        raise ThemeError("no fixtures found")
    return paths
