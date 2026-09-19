<!-- nnw-theme-identity:start -->
# NetNewsWire Theme Template

A complete, self-guided workspace for creating and publishing a NetNewsWire theme.
<!-- nnw-theme-identity:end -->

The starter gives you:

- guided setup that creates and personalizes the theme;
- a local preview gallery that publishes to GitHub Pages; and
- automatic validation, packaging, and release builds with GitHub Actions.

This repository combines an editable starter theme with guided setup, realistic
previews, validation, packaging, and release automation. You can drive it through a
coding agent or use the same commands yourself. No Xcode or NetNewsWire source
checkout is required.

It is an independent community project and is not affiliated with or endorsed by
NetNewsWire. The theme file format is documented in NetNewsWire’s official
[Themes technote](https://github.com/Ranchero-Software/NetNewsWire/blob/main/Technotes/Themes.md).

## Create your theme repository

The [original repository](https://github.com/dave-atx/netnewswire-theme-template)
is a GitHub template, not a theme to install as-is. On its GitHub page, choose
**Use this template → Create a new repository**. Give your new repository a name,
then work in that repository. If you are reading this in a repository already
created from the template, skip this step.

Do not use **Fork** or simply clone the original template as your theme repository:
the marketplace skips forks, and a clone still points at the template repository.
Initialization warns if it detects a fork. You can choose whether your new repository
is listed in the marketplace during setup.

## Start with an agent

Give your agent this one prompt, whether you are in your own repository or starting
from the template's GitHub page:

> Help me make a NetNewsWire theme with `dave-atx/netnewswire-theme-template`.
> Guide me through setup and design. I want [describe the look or reading experience].

The agent will ask you to approve the theme’s permanent identifier. It should also
ask again before creating a GitHub release or making another external change.

## Start without an agent

After creating your repository from the template, clone **your** repository and enter
it (replace `YOUR-NAME/YOUR-THEME` with its GitHub path):

```sh
git clone https://github.com/YOUR-NAME/YOUR-THEME.git
cd YOUR-THEME
```

On macOS, install the two tools and run the guided initializer:

```sh
brew install uv playwright-cli
uv run nnw-theme init
uv run nnw-theme preview
```

Only run `init` if `.nnw-theme-uninitialized` exists. If your copy is already
initialized, go straight to `uv run nnw-theme preview`.

Linux is supported too; install `uv` and `playwright-cli` with their documented
package-manager instructions, then use the same commands. The initializer supplies
sensible defaults, offers to install WebKit, and can add the `netnewswire-theme`
GitHub topic when you say yes. It never publishes a release.

The first setup or preview downloads the small, pinned set of NetNewsWire rendering
inputs into an ignored cache. The `[tool.nnw-theme.netnewswire]` configuration in
`pyproject.toml` pins every source file and hash; subsequent previews reuse the cache.

## Theme Marketplace

The normal setup recommends inclusion in the
[NetNewsWire Theme Marketplace](https://dave-atx.github.io/nnw-theme-marketplace/).
Accepting the default marketplace prompt adds the `netnewswire-theme` GitHub topic.
Once the repository is public and its first stable release is published by the
included workflow, the marketplace can discover it automatically—there is no listing
form or curated pull request.

Marketplace participation is optional. To opt out, answer **No** during initialization
or pass `--marketplace no` when an agent runs it. If the topic was already added,
remove `netnewswire-theme` in the repository’s GitHub settings. You may still preview,
package, and publish the theme normally; it simply will not be discovered through the
marketplace topic.

## What is in the repository

The preview page rebuilds as you edit. The theme itself is the only `*.nnwtheme`
directory at the repository root:

- `stylesheet.css` contains the visual design and clearly named variables.
- `template.html` contains the article structure and NetNewsWire macros.
- `Info.plist` contains the public identity and integer version.

Run the release gate before sharing a theme:

```sh
uv run nnw-theme check
```

This validates and packages the exact theme, then checks 16 WebKit renders: two
articles across macOS, iPhone, iPad, light and dark appearances, plus large-text and
Article-JavaScript-off cases. External requests are blocked. Results are written to
`build/preview/`; the release ZIP is written to `build/release/`.

After a successful default-branch check, the Pages workflow publishes the same
sandboxed gallery. Pull requests and failed checks retain it as a downloadable
diagnostic artifact; Pages is the normal hosted preview.

For each new repository, enable the included workflow once under **Settings → Pages →
Build and deployment → Source → GitHub Actions**.

Generated gallery screenshots stay ignored under `build/`. Keep the deliberately
chosen `screenshots/theme-preview.png` in source control: the marketplace uses it for
the theme card. Initialization removes the template’s neutral image; create your own
with `uv run nnw-theme screenshot --promote`. The screenshot workflow can open a pull
request when it changes.

## Publish

1. Run `uv run nnw-theme bump` and commit the changed `Info.plist`.
2. In GitHub, choose **Actions → Publish theme → Run workflow**.
3. Enter a tag beginning with `v` (for example, `v1.0.0`) and optional notes.

The workflow releases only the current default-branch commit and refuses a reused
tag, a non-increasing plist version, or changes to the identifier or bundle filename.
Marketplace metadata remains advisory: private repositories and repositories without
the topic can still publish valid themes. See the
[publishing guide](.agents/skills/creating-nnw-themes/references/publishing.md).

## Useful commands

```text
uv run nnw-theme init                  Personalize a fresh template
uv run nnw-theme setup                 Download inputs and install or locate WebKit
uv run nnw-theme preview [--no-open]   Rebuilding local preview
uv run nnw-theme render [fixture ...]  Generate the static gallery only
uv run nnw-theme check                 Full release gate
uv run nnw-theme package               Deterministic release ZIP
uv run nnw-theme screenshot --promote  Update the deliberate marketplace image
uv run nnw-theme bump [--yes]          Increase the integer theme version
uv run nnw-theme marketplace enable    Add the GitHub discovery topic
```

For agent-oriented constraints, read [AGENTS.md](AGENTS.md).

Tooling and documentation are Apache-2.0 licensed. The starter theme is 0BSD licensed,
so authors may replace its identity and license without inheriting a notice burden.
Pinned NetNewsWire preview inputs are downloaded into an ignored cache and verified
before use; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
