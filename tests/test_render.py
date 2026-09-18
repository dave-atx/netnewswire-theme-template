from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nnw_theme_tools.browser import _parse_state
from nnw_theme_tools.project import find_theme
from nnw_theme_tools.render import (
    check_targets,
    normal_targets,
    render_page,
    render_site,
    substitute,
)


def make_snapshot(parent: Path) -> Path:
    snapshot = parent / "snapshot"
    files = {
        "Mac/page.html": "<html><head><title>[[title]]</title><style>[[style]]</style>"
        '<base href="[[baseURL]]"></head><body>[[body]]</body></html>',
        "iOS/page.html": "<html><head><title>[[title]]</title><style>[[style]]</style>"
        "</head><body>[[body]]</body></html>",
        "Shared/core.css": "body { font-size: [[font-size]]px; }",
        "Shared/main.js": "function processPage() {}",
        "Shared/newsfoot.js": "// test newsfoot",
        "Mac/main_mac.js": "function postRenderProcessing() {}",
        "iOS/main_ios.js": "function postRenderProcessing() {}",
    }
    for relative, content in files.items():
        path = snapshot / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return snapshot


class MacroTests(unittest.TestCase):
    def test_playwright_stringified_json_result_is_unwrapped(self) -> None:
        self.assertEqual(_parse_state('"{\\"article\\": true}"'), {"article": True})

    def test_substitution_is_single_pass_and_preserves_unknown_macros(self) -> None:
        actual = substitute("[[known]] [[unknown]]", {"known": "[[nested]]", "nested": "no"})
        self.assertEqual(actual, "[[nested]] [[unknown]]")

    def test_matrix_has_twelve_normal_and_four_stress_targets(self) -> None:
        self.assertEqual(len(normal_targets()), 12)
        self.assertEqual(len(check_targets()), 16)
        self.assertEqual(sum(not target.theme_scripts for target in check_targets()), 2)
        self.assertEqual(sum(target.scale != 1 for target in check_targets()), 2)


class RenderTests(unittest.TestCase):
    def test_gallery_links_to_sandboxed_viewer(self) -> None:
        root = Path(__file__).resolve().parents[1]
        theme = find_theme(root)
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            (output_root / "fixtures").symlink_to(root / "fixtures", target_is_directory=True)
            snapshot = make_snapshot(output_root)
            target = normal_targets()[0]
            site = render_site(output_root, theme, [target], snapshot=snapshot)
            gallery = (site / "index.html").read_text(encoding="utf-8")
            viewer = (site / "views" / f"{target.slug}.html").read_text(encoding="utf-8")
            self.assertIn(f"views/{target.slug}.html", gallery)
            self.assertIn(f"pages/{target.slug}.html", gallery)
            self.assertIn(f"screenshots/{target.slug}.png", gallery)
            self.assertIn('sandbox="allow-scripts"', gallery)
            self.assertIn('sandbox="allow-scripts"', viewer)

    def test_render_uses_pinned_input_and_keeps_inline_theme_script(self) -> None:
        root = Path(__file__).resolve().parents[1]
        theme = find_theme(root)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = make_snapshot(Path(directory))
            fixture = {
                "title": "Hello",
                "feed_link_title": "Example",
                "preferred_link": "https://example.org/post",
                "body": "<p>Readable article body.</p>",
            }
            target = normal_targets()[0]
            page = render_page(root, theme, fixture, target, snapshot=snapshot)
            self.assertIn("Readable article body.", page)
            self.assertIn("Content-Security-Policy", page)
            self.assertIn("base-uri http: https:", page)
            self.assertIn("function processPage()", page)
            self.assertNotIn("[[title]]", page)

    def test_theme_scripts_can_be_removed_without_removing_nnw_scripts(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory) / "Test.nnwtheme"
            theme.mkdir()
            snapshot = make_snapshot(Path(directory))
            (theme / "stylesheet.css").write_text("body {}", encoding="utf-8")
            (theme / "template.html").write_text(
                '<article class="articleBody">[[body]]'
                "<script>window.themeRan=true</script></article>",
                encoding="utf-8",
            )
            target = next(target for target in check_targets() if not target.theme_scripts)
            page = render_page(
                root,
                theme,
                {
                    "title": "Test",
                    "body": "<p>Still readable.</p><script>window.articleRan=true</script>",
                },
                target,
                snapshot=snapshot,
            )
            self.assertNotIn("window.themeRan", page)
            self.assertNotIn("window.articleRan", page)
            self.assertIn("function processPage()", page)


if __name__ == "__main__":
    unittest.main()
