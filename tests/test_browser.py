from __future__ import annotations

import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from nnw_theme_tools.browser import setup_webkit


class SetupWebKitTests(unittest.TestCase):
    def test_installs_when_listing_fails_on_a_fresh_cache(self) -> None:
        calls: list[list[str]] = []

        def run(arguments: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(arguments)
            if "--list" in arguments:
                return subprocess.CompletedProcess(
                    arguments, 1, "", "ENOENT: no such file or directory, scandir '.links'"
                )
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with (
            patch("nnw_theme_tools.browser.shutil.which", return_value="/bin/playwright-cli"),
            patch("nnw_theme_tools.browser.subprocess.run", side_effect=run),
            patch("nnw_theme_tools.browser.sys.platform", "darwin"),
            redirect_stdout(io.StringIO()),
        ):
            setup_webkit()

        self.assertEqual(calls[-1], ["playwright-cli", "install-browser", "webkit"])


if __name__ == "__main__":
    unittest.main()
