from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from nnw_theme_tools.browser import _parse_state
from nnw_theme_tools.project import find_theme
from nnw_theme_tools.render import (
    DEFAULT_DYNAMIC_TYPE_SIZE,
    DEFAULT_TEXT_SIZE_CLASS,
    LARGE_DYNAMIC_TYPE_SIZE,
    LARGE_TEXT_SIZE_CLASS,
    check_targets,
    normal_targets,
    render_page,
    render_site,
    substitute,
    write_gallery,
)


def make_snapshot(parent: Path) -> Path:
    snapshot = parent / "snapshot"
    files = {
        "Mac/page.html": "<html><head><title>[[title]]</title><style>[[style]]</style>"
        '<base href="[[baseURL]]"></head><body>[[body]]</body></html>',
        "iOS/page.html": "<html><head><title>[[title]]</title><style>[[style]]</style>"
        "</head><body>[[body]]</body></html>",
        # core.css carries no macros upstream; [[font-size]] lives in theme CSS.
        "Shared/core.css": "body { margin: 0; }",
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
        self.assertEqual(sum(target.large_text for target in check_targets()), 2)


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

    def test_gallery_groups_cases_by_scenario_and_reports_results(self) -> None:
        targets = check_targets()
        failing = next(t for t in targets if t.platform == "iphone" and t.appearance == "dark")
        results = {target.slug: [] for target in targets}
        results[failing.slug] = ["horizontal document overflow"]
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            write_gallery(site, "Quiet Reader", targets, results)
            gallery = (site / "index.html").read_text(encoding="utf-8")
        headings = re.findall(r"<section><h2>([^<]+)</h2>", gallery)
        self.assertEqual(
            headings,
            ["Everyday reading", "Stress test", "Large text", "Article JavaScript off"],
        )
        self.assertIn("16 cases · 15 passed · 1 failed", gallery)
        self.assertLess(gallery.index("<h2>Failures</h2>"), gallery.index("Everyday reading"))
        self.assertIn(f'href="#{failing.slug}"', gallery)
        self.assertEqual(gallery.count("✓ Passed"), 15)
        self.assertEqual(gallery.count("✗ Failed"), 1)
        self.assertIn("<li>horizontal document overflow</li>", gallery)

    def test_unchecked_gallery_has_no_results_or_screenshot_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            write_gallery(site, "Quiet Reader", normal_targets())
            gallery = (site / "index.html").read_text(encoding="utf-8")
        self.assertIn("12 cases, not checked yet", gallery)
        self.assertNotIn("Passed", gallery)
        self.assertNotIn("Screenshot</a>", gallery)
        self.assertNotIn("Large text", gallery)

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


class TextScalingTests(unittest.TestCase):
    """NetNewsWire scales text per platform; the preview has to match it exactly."""

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.theme = find_theme(self.root)
        self.fixture = {"title": "Hello", "body": "<p>Readable article body.</p>"}

    def render(self, target) -> str:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = make_snapshot(Path(directory))
            return render_page(self.root, self.theme, self.fixture, target, snapshot=snapshot)

    def target(self, platform: str, *, large_text: bool = False):
        pool = check_targets() if large_text else normal_targets()
        return next(
            item
            for item in pool
            if item.platform == platform
            and item.large_text == large_text
            and item.theme_scripts
        )

    def test_font_size_is_substituted_on_ios_and_left_literal_on_macos(self) -> None:
        # styleSubstitutions() is empty on macOS, so no theme can rely on it there.
        self.assertIn("[[font-size]]", self.render(self.target("mac")))

        iphone = self.render(self.target("iphone"))
        self.assertNotIn("[[font-size]]", iphone)
        self.assertIn(f"font-size: {DEFAULT_DYNAMIC_TYPE_SIZE:g}px", iphone)
        self.assertIn(
            f"font-size: {LARGE_DYNAMIC_TYPE_SIZE:g}px",
            self.render(self.target("iphone", large_text=True)),
        )

    def test_text_size_class_is_macos_only_and_defaults_to_large(self) -> None:
        # An unset macOS preference falls back to ArticleTextSize.large, not medium.
        self.assertEqual(DEFAULT_TEXT_SIZE_CLASS, "largeText")
        self.assertIn(
            f'class="articleBody {DEFAULT_TEXT_SIZE_CLASS}"', self.render(self.target("mac"))
        )
        self.assertIn(
            f'class="articleBody {LARGE_TEXT_SIZE_CLASS}"',
            self.render(self.target("mac", large_text=True)),
        )
        for platform in ("iphone", "ipad"):
            page = self.render(self.target(platform))
            self.assertIn('class="articleBody "', page)
            self.assertNotIn("[[text_size_class]]", page)

    def test_starter_theme_honors_both_scaling_mechanisms(self) -> None:
        css = (self.theme / "stylesheet.css").read_text(encoding="utf-8")
        self.assertIn("[[font-size]]", css)
        for name in ("smallText", "mediumText", "largeText"):
            self.assertIn(f".{name}", css)
        # NetNewsWire emits the capital-L spellings; its own themes select lowercase.
        for name in ("xLargeText", "xxLargeText", "xlargeText", "xxlargeText"):
            self.assertIn(f".{name}", css)
        # No desktop WebKit has -webkit-touch-callout; such a query previews false.
        self.assertNotIn("@supports", re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL))


if __name__ == "__main__":
    unittest.main()
