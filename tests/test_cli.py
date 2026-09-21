from __future__ import annotations

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from nnw_theme_tools.cli import _absolute_homepage, command_init
from nnw_theme_tools.project import PLACEHOLDER_MARKER, ThemeError, write_plist


def _template(root: Path) -> Path:
    theme = root / "Starter.nnwtheme"
    theme.mkdir()
    write_plist(
        theme / "Info.plist",
        {
            "ThemeIdentifier": "com.example.starter",
            "Name": "Starter",
            "CreatorHomePage": "https://example.com",
            "CreatorName": "Theme Author",
            "Version": 1,
        },
    )
    (root / "README.md").write_text(
        "<!-- nnw-theme-identity:start -->\nold\n"
        "<!-- nnw-theme-identity:end -->\n\nKept documentation.\n",
        encoding="utf-8",
    )
    (root / "screenshots").mkdir()
    (root / "screenshots" / "theme-preview.png").write_bytes(b"template image")
    (root / PLACEHOLDER_MARKER).touch()
    return theme


def _init_args(*, install_browser: bool) -> argparse.Namespace:
    return argparse.Namespace(
        name="Quiet Reader",
        creator="Theme Author",
        homepage="https://github.com/theme-author",
        github_user="theme-author",
        identifier="io.github.theme-author.quiet-reader",
        confirm_identifier="io.github.theme-author.quiet-reader",
        marketplace="no",
        install_browser=install_browser,
    )


class InitTests(unittest.TestCase):
    def test_rejects_placeholder_homepage(self) -> None:
        with self.assertRaisesRegex(ThemeError, "placeholder"):
            _absolute_homepage("https://example.com")

    def test_initialization_removes_starter_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = _template(root)

            with (
                patch("nnw_theme_tools.cli.find_root", return_value=root),
                patch("nnw_theme_tools.cli.find_theme", return_value=theme),
                redirect_stdout(io.StringIO()),
            ):
                command_init(_init_args(install_browser=False))

            self.assertFalse((root / "screenshots" / "theme-preview.png").exists())
            self.assertFalse((root / PLACEHOLDER_MARKER).exists())
            self.assertTrue((root / "Quiet Reader.nnwtheme").is_dir())
            self.assertIn("Kept documentation.", (root / "README.md").read_text())

    def test_preview_setup_failure_does_not_fail_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = _template(root)
            stderr = io.StringIO()

            with (
                patch("nnw_theme_tools.cli.find_root", return_value=root),
                patch("nnw_theme_tools.cli.find_theme", return_value=theme),
                patch(
                    "nnw_theme_tools.cli.ensure_snapshot",
                    side_effect=ThemeError("install playwright-cli first"),
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                command_init(_init_args(install_browser=True))

            self.assertFalse((root / PLACEHOLDER_MARKER).exists())
            self.assertIn("install playwright-cli first", stderr.getvalue())
            self.assertIn("uv run nnw-theme setup", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
