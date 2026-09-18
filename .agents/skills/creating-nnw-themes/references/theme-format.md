# NetNewsWire theme format

Read this when changing theme structure, metadata, scripts, or resources.

The one root-level `<Name>.nnwtheme` directory is the release bundle. It contains
exactly `Info.plist`, `template.html`, `stylesheet.css`, and optional license or notice
files. NetNewsWire does not serve arbitrary bundle-local assets: do not add fonts,
images, media, or references to them. Small demonstrated assets may use data URLs.

`Info.plist` requires non-empty `ThemeIdentifier`, `Name`, `CreatorHomePage`, and
`CreatorName`, plus an integer `Version`. `Name` and the bundle stem match exactly,
including spaces and capitalization. `CreatorHomePage` is an absolute HTTP(S) URL.
The identifier and bundle name stay stable after the first release.

NetNewsWire performs two single-pass substitutions. First, article values replace
macros in `template.html`; then that body and combined core/theme CSS enter a platform
page skeleton. Unknown macros remain literal, and substituted values are not scanned
again. Common template macros are visible in the starter markup and synthetic
fixtures.

The renderer pins NetNewsWire `mac-7.1.3` commit
`f2daca0f24f29c08d9cb16e1bdc56293fd6fe286`. It uses upstream `core.css`, macOS and
iOS page skeletons, and `main.js`, `main_mac.js`, `main_ios.js`, and `newsfoot.js`.
`[tool.nnw-theme.netnewswire]` in `pyproject.toml` records each source path and
SHA-256; the tools download missing or corrupted inputs into the ignored
`.cache/netnewswire/` directory and verify them before use. iPhone and iPad share the
iOS skeleton. WebKit native
color-scheme emulation controls light/dark captures; CSS is not rewritten.

Inline scripts in `template.html` are supported. External scripts and stylesheets are
rejected. Remote theme-owned fonts, images, audio, or video require an explicit local
warning override and are still blocked during checks. The article must remain useful
when Article JavaScript is off; those smoke renders remove theme inline scripts while
retaining NetNewsWire’s injected scripts.
