from __future__ import annotations

import base64
import hashlib
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project import ThemeError, read_fixture
from .snapshot import ensure_snapshot

MACRO_RE = re.compile(r"\[\[([a-zA-Z0-9_-]+)\]\]")
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
TEMPLATE_KEYS = (
    "title",
    "preferred_link",
    "external_link_label",
    "external_link_stripped",
    "external_link",
    "feed_link_title",
    "feed_link",
    "byline",
    "avatar_src",
    "dateline_style",
    "datetime_long",
    "datetime_medium",
    "datetime_short",
    "date_long",
    "date_medium",
    "date_short",
    "time_long",
    "time_medium",
    "time_short",
    "text_size_class",
    "body",
)
# macOS scales through text_size_class, iOS through the font-size macro. largeText
# is the macOS default: an unset preference falls back to ArticleTextSize.large.
DEFAULT_TEXT_SIZE_CLASS = "largeText"
LARGE_TEXT_SIZE_CLASS = "xxLargeText"
DEFAULT_DYNAMIC_TYPE_SIZE = 17.0
LARGE_DYNAMIC_TYPE_SIZE = 23.0
WEBKIT_SHIM = """
window.webkit = window.webkit || {messageHandlers: new Proxy({}, {
  get: function() { return {postMessage: function() {}}; }
})};
"""
IOS_LABEL_SHIM = """
window.localizedStrings = window.localizedStrings || {};
"""


@dataclass(frozen=True)
class RenderTarget:
    fixture: str
    platform: str
    appearance: str
    width: int
    height: int
    large_text: bool = False
    theme_scripts: bool = True

    @property
    def ios(self) -> bool:
        return self.platform in {"iphone", "ipad"}

    @property
    def slug(self) -> str:
        parts = [self.fixture, self.platform, self.appearance]
        if self.large_text:
            parts.append("large-text")
        if not self.theme_scripts:
            parts.append("no-article-js")
        return "-".join(parts)


def normal_targets() -> list[RenderTarget]:
    viewports = {
        "mac": (1280, 800),
        "iphone": (393, 852),
        "ipad": (834, 1112),
    }
    return [
        RenderTarget(fixture, platform, appearance, *viewports[platform])
        for fixture in ("article", "kitchen-sink")
        for platform in ("mac", "iphone", "ipad")
        for appearance in ("light", "dark")
    ]


def check_targets() -> list[RenderTarget]:
    return [
        *normal_targets(),
        RenderTarget("kitchen-sink", "mac", "light", 1280, 800, large_text=True),
        RenderTarget("kitchen-sink", "iphone", "light", 393, 852, large_text=True),
        RenderTarget("article", "mac", "light", 1280, 800, theme_scripts=False),
        RenderTarget("article", "iphone", "light", 393, 852, theme_scripts=False),
    ]


def substitute(template: str, mapping: dict[str, Any]) -> str:
    """Perform NetNewsWire's single-pass, non-recursive macro substitution."""

    return MACRO_RE.sub(
        lambda match: str(mapping.get(match.group(1), match.group(0))), template
    )


def _avatar_data_uri(title: str) -> str:
    words = title.strip().split()
    initials = "?" if not words else "".join(word[0] for word in words[:3]).upper()
    hue = int(hashlib.sha256(title.encode()).hexdigest()[:2], 16) / 255 * 360
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96">'
        f'<rect width="96" height="96" rx="18" fill="hsl({hue:.0f} 42% 38%)"/>'
        '<text x="48" y="50" text-anchor="middle" dominant-baseline="central" '
        'font-family="system-ui" font-size="32" font-weight="700" fill="white">'
        f"{html.escape(initials)}</text></svg>"
    )
    encoded = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


def _fixture_mapping(fixture: dict[str, Any], target: RenderTarget) -> dict[str, str]:
    mapping = {key: str(fixture.get(key, "")) for key in TEMPLATE_KEYS}
    if not mapping["dateline_style"]:
        mapping["dateline_style"] = (
            "articleDateline" if mapping["title"] else "articleDatelineTitle"
        )
    if not mapping["avatar_src"] or mapping["avatar_src"].startswith("nnwImageIcon:"):
        mapping["avatar_src"] = _avatar_data_uri(mapping["feed_link_title"])
    if target.ios:
        # NetNewsWire leaves this macro unresolved on iOS; empty renders the same.
        mapping["text_size_class"] = ""
    else:
        default = LARGE_TEXT_SIZE_CLASS if target.large_text else DEFAULT_TEXT_SIZE_CLASS
        mapping["text_size_class"] = str(fixture.get("text_size_class") or default)
    return mapping


def _inject_scripts(page: str, rendering_inputs: Path, platform: str) -> str:
    platform_dir = "iOS" if platform in {"iphone", "ipad"} else "Mac"
    platform_script = "main_ios.js" if platform_dir == "iOS" else "main_mac.js"
    scripts = [WEBKIT_SHIM]
    if platform_dir == "iOS":
        scripts.append(IOS_LABEL_SHIM)
    for path in (
        rendering_inputs / "Shared" / "main.js",
        rendering_inputs / platform_dir / platform_script,
        rendering_inputs / "Shared" / "newsfoot.js",
    ):
        scripts.append(path.read_text(encoding="utf-8"))
    bundle = "\n".join(f"<script>\n{script}\n</script>" for script in scripts)
    return page.replace("</body>", f"{bundle}\n</body>", 1)


def render_page(
    root: Path,
    theme: Path,
    fixture: dict[str, Any],
    target: RenderTarget,
    *,
    snapshot: Path | None = None,
) -> str:
    rendering_inputs = snapshot or ensure_snapshot(root).path
    page_path = rendering_inputs / ("iOS" if target.ios else "Mac") / "page.html"
    required = [
        page_path,
        rendering_inputs / "Shared" / "core.css",
        rendering_inputs / "Shared" / "main.js",
    ]
    if not all(path.is_file() for path in required):
        raise ThemeError("cached NetNewsWire rendering inputs are incomplete")

    skeleton = SCRIPT_RE.sub("", page_path.read_text(encoding="utf-8"))
    stylesheet = (theme / "stylesheet.css").read_text(encoding="utf-8")
    # styleSubstitutions() is empty on macOS, so the macro must stay literal there.
    style_substitutions: dict[str, str] = {}
    if target.ios:
        size = LARGE_DYNAMIC_TYPE_SIZE if target.large_text else DEFAULT_DYNAMIC_TYPE_SIZE
        style_substitutions["font-size"] = f"{float(fixture.get('font_size', size)):g}"
    style = substitute(
        (rendering_inputs / "Shared" / "core.css").read_text(encoding="utf-8")
        + "\n"
        + stylesheet,
        style_substitutions,
    )

    template = (theme / "template.html").read_text(encoding="utf-8")
    body = substitute(template, _fixture_mapping(fixture, target))
    if not target.theme_scripts:
        body = SCRIPT_RE.sub("", body)
    page = substitute(
        skeleton,
        {
            "title": fixture.get("title", "Theme preview"),
            "style": style,
            "body": body,
            "baseURL": fixture.get("preferred_link") or fixture.get("feed_link") or "",
            "windowScrollY": "0",
        },
    )
    page = _inject_scripts(page, rendering_inputs, target.platform)
    csp = (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "img-src data:; media-src data:; connect-src 'none'; frame-src 'none'; "
        "object-src 'none'; base-uri http: https:; form-action 'none'"
    )
    head = (
        '<meta charset="utf-8">\n'
        '<meta name="color-scheme" content="light dark">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
    )
    return re.sub(r"(<head[^>]*>)", rf"\1\n{head}", page, count=1, flags=re.IGNORECASE)


def render_site(
    root: Path,
    theme: Path,
    targets: list[RenderTarget],
    *,
    snapshot: Path | None = None,
) -> Path:
    rendering_inputs = snapshot or ensure_snapshot(root).path
    site = root / "build" / "preview"
    if site.exists():
        shutil.rmtree(site)
    pages = site / "pages"
    views = site / "views"
    shots = site / "screenshots"
    pages.mkdir(parents=True, exist_ok=True)
    views.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    cards: list[str] = []
    for target in targets:
        fixture = read_fixture(root / "fixtures" / f"{target.fixture}.toml")
        destination = pages / f"{target.slug}.html"
        destination.write_text(
            render_page(root, theme, fixture, target, snapshot=rendering_inputs),
            encoding="utf-8",
        )
        viewer = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(target.slug)} · {html.escape(theme.stem)} preview</title><style>
html,body,iframe {{ border: 0; height: 100%; margin: 0; width: 100%; }}
</style></head><body><iframe src="../pages/{target.slug}.html" sandbox="allow-scripts"
title="Sandboxed {html.escape(target.slug)} theme preview"></iframe></body></html>"""
        (views / f"{target.slug}.html").write_text(viewer, encoding="utf-8")
        shot = f"screenshots/{target.slug}.png"
        labels = [target.fixture, target.platform, target.appearance]
        if target.large_text:
            labels.append("large text")
        if not target.theme_scripts:
            labels.append("article JavaScript off")
        cards.append(
            '<article class="card">'
            '<div class="preview">'
            f'<iframe loading="lazy" src="pages/{target.slug}.html" sandbox="allow-scripts" '
            f'title="Sandboxed {html.escape(target.slug)} theme preview"></iframe>'
            f'<img src="{shot}" alt="{html.escape(target.slug)} checked screenshot" '
            'onload="this.previousElementSibling.hidden=true"></div>'
            f"<h2>{html.escape(' · '.join(labels))}</h2>"
            f'<p><a href="views/{target.slug}.html">Open full size</a> · '
            f'<a href="{shot}">Screenshot</a></p>'
            "</article>"
        )
    gallery = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
<title>{html.escape(theme.stem)} preview</title><style>
:root {{ color-scheme: light dark; font-family: system-ui; }}
body {{ margin: 0 auto; max-width: 90rem; padding: 2rem; }}
.notice {{ background: CanvasText; color: Canvas; padding: .75rem 1rem; }}
.grid {{ display: grid; gap: 1.5rem;
  grid-template-columns: repeat(auto-fit,minmax(18rem,1fr)); }}
.card {{ border: 1px solid color-mix(in srgb, CanvasText 20%, Canvas);
  border-radius: .6rem; overflow: hidden; }}
.preview {{ aspect-ratio: 16/10; background: color-mix(in srgb, CanvasText 8%, Canvas);
  overflow: hidden; position: relative; }}
.card iframe,.card img {{ border: 0; height: 100%; inset: 0; position: absolute;
  width: 100%; }}
.card iframe {{
  background: color-mix(in srgb, CanvasText 8%, Canvas); display: block;
  pointer-events: none; }}
.card img {{ object-fit: cover; object-position: top; }}
.card h2,.card p {{ margin: .8rem 1rem; }} .card h2 {{ font-size: 1rem; }}
</style></head><body><p class="notice">Development preview — install themes only
from a release.</p><h1>{html.escape(theme.stem)} preview</h1>
<p>Generated from the same renderer used by checks.</p>
<p>Before checked screenshots exist, live thumbnails follow your system appearance.</p>
<main class="grid">{"".join(cards)}</main></body></html>"""
    (site / "index.html").write_text(gallery, encoding="utf-8")
    return site
