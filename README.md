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

With the [GitHub CLI](https://cli.github.com/), one command creates the repository
and clones it (replace `YOUR-THEME` with the name you want):

```sh
gh repo create YOUR-THEME --template dave-atx/netnewswire-theme-template --public --clone
cd YOUR-THEME
```

The marketplace lists only public repositories; use `--private` if you don't want
the theme listed.

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

The whole path, in order. Steps 1–3 happen once; step 4 is where you spend your time.

**1. Install the tools.** On macOS:

```sh
brew install uv playwright-cli gh
gh auth login
```

`uv` and `playwright-cli` are required. `gh`, the GitHub CLI, is optional but
recommended: it creates your repository in one step, and `init` uses it to fill in
GitHub defaults, warn about forks, and join the marketplace. Without it, join by adding
the `netnewswire-theme` topic in your repository's GitHub settings. On Linux, install
the same tools with their documented instructions.

**2. Get your own copy.** Create and clone your repository:

```sh
gh repo create YOUR-THEME --template dave-atx/netnewswire-theme-template --public --clone
cd YOUR-THEME
```

Or create it on GitHub (above) and clone **your** repository (replace
`YOUR-NAME/YOUR-THEME` with its GitHub path):

```sh
git clone https://github.com/YOUR-NAME/YOUR-THEME.git
cd YOUR-THEME
```

**3. Initialize, then commit.** `init` asks for the theme name, your name and home
page, and the theme's permanent identifier. It also offers to join the marketplace
and to install WebKit; say yes to both unless you have a reason not to.

```sh
uv run nnw-theme init
git add -A && git commit -m "Initialize theme"
```

Run `init` only while `.nnw-theme-uninitialized` exists. If WebKit setup failed or you
skipped it, run `uv run nnw-theme setup` before step 5.

**4. Design.** Start the live preview and edit the files in your `.nnwtheme` folder,
mostly `stylesheet.css`. The gallery rebuilds each time you save; refresh the browser
to see it. Stop with Ctrl-C.

```sh
uv run nnw-theme preview
```

**5. Check.** When it looks right, run the release gate. It tests every case in WebKit,
reports progress, and offers to open the results; fix any failures and run it again.

```sh
uv run nnw-theme check
```

**6. Choose the marketplace image.** This captures the Mac light article and saves it
as `screenshots/theme-preview.png`, the picture on your marketplace card.

```sh
uv run nnw-theme screenshot --promote
```

**7. Commit and push.**

```sh
git add -A && git commit -m "Design my theme"
git push
```

GitHub runs the same check on every push. The first time, enable **Settings → Pages →
Build and deployment → Source → GitHub Actions** so your gallery is published too.

**8. Publish.** Follow [Publish](#publish) below: bump the version, then run the
Publish workflow on GitHub. Repeat steps 4–8 for later versions.

The first `setup`, `preview`, or `check` downloads a small, pinned set of NetNewsWire
rendering files into an ignored cache. The `[tool.nnw-theme.netnewswire]`
configuration in `pyproject.toml` pins every file and its hash.

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
Article-JavaScript-off cases. Each fixture you add is checked on macOS and iPhone in
both appearances as well. Every footnote marker must open NetNewsWire's popover with
its note, stay legible, and match the others. External requests are blocked. Results are written to
`build/preview/`, a gallery grouped by scenario that marks each case passed or failed
and lists failures first; the release ZIP is written to `build/release/`. In a
terminal, `check` shows its progress and offers to open the gallery when it finishes.

After a successful default-branch check, the Pages workflow publishes the same
sandboxed gallery. Pull requests and failed checks retain it as a downloadable
diagnostic artifact; Pages is the normal hosted preview.

For each new repository, enable the included workflow once under **Settings → Pages →
Build and deployment → Source → GitHub Actions**. If Pages already publishes a site of
yours from a branch, the workflow leaves it alone and keeps the gallery as an artifact.

## Fixtures

Fixtures are the articles every preview and check renders: TOML files in `fixtures/`
whose keys are the template macros (`title`, `byline`, `feed_link_title`, `body`, and
so on). `article.toml` and `kitchen-sink.toml` come with the template; add your own
for the content your theme has to handle, and preview one with
`uv run nnw-theme render NAME`.

The best fixtures are real articles. `uv run nnw-theme capture` explains how to save
the one selected in a NetNewsWire debug build, exactly as the app would render it.
Previews never touch the network, so images that would load from the web appear as
same-size placeholders.

A fixture can also say what its footnotes must do. `check` then verifies each marker
by its text, that the listed links are left as ordinary links, and, with
`keep_with_word`, that no marker wraps onto a new line apart from its word:

```toml
[expect.footnotes]
plain_links = ["#not-a-footnote"]
keep_with_word = true

[expect.footnotes.notes]
"1" = "The first note's text."
"2" = "The second note's text."
```

Put these tables after the fixture's other keys, including `body`.

Generated gallery screenshots stay ignored under `build/`. Keep the deliberately
chosen `screenshots/theme-preview.png` in source control: the marketplace uses it for
the theme card. Initialization removes the template’s neutral image; create your own
with `uv run nnw-theme screenshot --promote`. The screenshot workflow can open a pull
request when it changes.

## Publish

1. Run `uv run nnw-theme bump` and commit the changed `Info.plist`.
2. In GitHub, choose **Actions → Publish theme → Run workflow**.
3. Enter a tag beginning with `v` (for example, `v1.0.0`) and optional notes.

If you leave the notes empty and the repository has a
[git-cliff](https://git-cliff.org) configuration at `.github/cliff.toml`, the notes
are generated from the commits since the previous tag.

The workflow releases only the current default-branch commit and refuses a reused
tag, a non-increasing plist version, or changes to the identifier or bundle filename.
Marketplace metadata remains advisory: private repositories and repositories without
the topic can still publish valid themes. See the
[publishing guide](.agents/skills/creating-nnw-themes/references/publishing.md).

## Update the tooling

Repositories made from the template keep their own copy of its tooling. To pull in
later fixes, commit your work, then run:

```sh
uv run nnw-theme update --dry-run   # list what would change
uv run nnw-theme update
```

By default this installs the template's newest release tag (such as `v1.2.0`). Use
`--ref` to pick a specific tag, branch, or commit instead.
It updates the tooling, tests, workflows, agent guidance, and the README below your
theme's heading. It also adds new fixtures and missing `.gitignore` entries. It never
touches your `.nnwtheme` bundle, your screenshot, or fixtures you already have, and it
keeps workflows you added. Review the result with `git diff`, run
`uv run nnw-theme check`, and commit.

To write your own README instead, keep it between the `nnw-theme-identity` markers and
delete everything after the closing one; `update` then leaves the README alone.
`CLAUDE.md` and `AGENTS.md` belong to the template, so put your own agent guidance in
`.claude/CLAUDE.md`, which Claude Code also reads.

Copies made before `update` existed can bootstrap it once:

```sh
uvx --from git+https://github.com/dave-atx/netnewswire-theme-template nnw-theme update
```

## Useful commands

```text
uv run nnw-theme init                  Personalize a fresh copy of the template (once)
uv run nnw-theme setup                 Download rendering files and install WebKit
uv run nnw-theme update [--dry-run]    Refresh tooling and docs from the template
uv run nnw-theme preview [--no-open]   Live gallery for editing; rebuilds on save
uv run nnw-theme render [fixture ...]  Write the gallery once, without checks
uv run nnw-theme check [--no-open]     Release gate: package and test every case
uv run nnw-theme screenshot --promote  Check one case and make it the marketplace image
uv run nnw-theme capture               Explain how to capture a real article as a fixture
uv run nnw-theme package               Validate and build the release ZIP only
uv run nnw-theme bump [--yes]          Increase the integer theme version
uv run nnw-theme marketplace enable    Add the GitHub discovery topic
```

For agent-oriented constraints, read [AGENTS.md](AGENTS.md).

Tooling and documentation are Apache-2.0 licensed. The starter theme is 0BSD licensed,
so authors may replace its identity and license without inheriting a notice burden.
Pinned NetNewsWire preview inputs are downloaded into an ignored cache and verified
before use; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
