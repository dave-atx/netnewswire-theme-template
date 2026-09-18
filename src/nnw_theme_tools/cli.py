from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import subprocess
import sys
import time
import webbrowser
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .browser import check_pages, serve, setup_webkit
from .package import build_archive
from .project import (
    PLACEHOLDER_MARKER,
    ThemeError,
    find_root,
    find_theme,
    read_plist,
    write_plist,
)
from .render import RenderTarget, check_targets, normal_targets, render_site
from .snapshot import ensure_snapshot

IDENTITY_START = "<!-- nnw-theme-identity:start -->"
IDENTITY_END = "<!-- nnw-theme-identity:end -->"


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _identifier_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "", _slug(value)) or "theme"


def _repository() -> dict[str, Any]:
    """Owner and fork status of the current repository, when gh can report them."""
    if not shutil.which("gh"):
        return {}
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,isFork"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _default_identifier(name: str, homepage: str, github_user: str | None) -> str:
    suffix = _identifier_slug(name)
    if github_user:
        return f"io.github.{_identifier_slug(github_user)}.{suffix}"
    hostname = (urlparse(homepage).hostname or "example.com").lower().split(".")
    domain = ".".join(reversed([_identifier_slug(part) for part in hostname]))
    return f"{domain}.{suffix}"


def _prompt_text(label: str, default: str) -> str:
    import questionary

    answer = questionary.text(label, default=default).ask()
    if answer is None:
        raise ThemeError("initialization cancelled")
    return answer.strip()


def _prompt_confirm(label: str, default: bool = True) -> bool:
    import questionary

    answer = questionary.confirm(label, default=default).ask()
    if answer is None:
        raise ThemeError("initialization cancelled")
    return answer


def _absolute_homepage(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ThemeError("creator home page must be an absolute HTTP(S) URL")
    if parsed.hostname in {"example.com", "www.example.com"}:
        raise ThemeError("creator home page must not use the example.com placeholder")
    return value


def _update_readme(root: Path, *, name: str, creator: str, homepage: str) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    start = text.find(IDENTITY_START)
    end = text.find(IDENTITY_END)
    if start < 0 or end < start:
        raise ThemeError("README identity markers are missing")
    replacement = (
        f"{IDENTITY_START}\n"
        f"# {name}\n\n"
        f"A NetNewsWire theme by [{creator}]({homepage}).\n"
        f"{IDENTITY_END}"
    )
    text = text[:start] + replacement + text[end + len(IDENTITY_END) :]
    readme.write_text(text, encoding="utf-8")


def marketplace_enable() -> bool:
    if not shutil.which("gh"):
        print(
            "Warning: GitHub CLI is not installed. Run `uv run nnw-theme marketplace enable` "
            "after installing and authenticating gh.",
            file=sys.stderr,
        )
        return False
    result = subprocess.run(
        ["gh", "repo", "edit", "--add-topic", "netnewswire-theme"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        print(
            "Warning: could not add the marketplace topic. "
            "Run `uv run nnw-theme marketplace enable` later.\n"
            + (result.stderr or result.stdout).strip(),
            file=sys.stderr,
        )
        return False
    print("Added the netnewswire-theme GitHub topic.")
    return True


def command_init(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    if not (root / PLACEHOLDER_MARKER).exists():
        raise ThemeError("this repository is already initialized")

    interactive = not all((args.name, args.creator, args.homepage))
    repository = _repository()
    if repository.get("isFork"):
        print(
            "Warning: this repository is a fork. The theme marketplace skips forks, so "
            "the theme will never be discovered. Start from GitHub's \"Use this "
            'template" button instead, then rerun initialization.',
            file=sys.stderr,
        )
    github_user = args.github_user or repository.get("owner", {}).get("login")
    name = args.name or _prompt_text("Theme name", "Quiet Reader")
    creator = args.creator or _prompt_text("Your name", "Theme Author")
    homepage_default = f"https://github.com/{github_user}" if github_user else ""
    homepage = _absolute_homepage(
        args.homepage
        or _prompt_text(
            "Your HTTP(S) home page (for example, your GitHub profile)", homepage_default
        )
    )
    proposed = args.identifier or _default_identifier(name, homepage, github_user)
    identifier = proposed
    if interactive and not args.identifier:
        identifier = _prompt_text("Stable theme identifier", proposed)
    if args.confirm_identifier:
        if args.confirm_identifier != identifier:
            raise ThemeError("--confirm-identifier must exactly match the chosen identifier")
    elif not _prompt_confirm(
        f"Use {identifier!r} permanently? It cannot change after the first release.",
        default=True,
    ):
        raise ThemeError("choose a permanent identifier and rerun initialization")

    if (
        not name.strip()
        or name in {".", ".."}
        or any(character in name for character in "/\\\0")
    ):
        raise ThemeError("theme name must be non-empty and cannot contain path separators")
    destination = root / f"{name}.nnwtheme"
    if destination.exists() and destination != theme:
        raise ThemeError(f"theme bundle already exists: {destination}")
    metadata = read_plist(theme)
    metadata.update(
        {
            "ThemeIdentifier": identifier,
            "Name": name,
            "CreatorHomePage": homepage,
            "CreatorName": creator,
            "Version": 1,
        }
    )
    if destination != theme:
        theme.rename(destination)
        theme = destination
    write_plist(theme / "Info.plist", metadata)
    _update_readme(root, name=name, creator=creator, homepage=homepage)
    (root / "screenshots" / "theme-preview.png").unlink(missing_ok=True)
    (root / PLACEHOLDER_MARKER).unlink()
    print(f"Initialized {theme.name} with identifier {identifier}.")
    print("Create a deliberate marketplace image with `uv run nnw-theme screenshot --promote`.")

    marketplace = args.marketplace
    if marketplace is None:
        marketplace = (
            "yes" if _prompt_confirm("Add this repository to the theme marketplace?") else "no"
        )
    if marketplace == "yes":
        marketplace_enable()

    install = args.install_browser
    if install is None and interactive:
        install = _prompt_confirm("Set up WebKit for previews now?")
    if install:
        snapshot = ensure_snapshot(root)
        print(f"NetNewsWire {snapshot.release} rendering inputs are ready.")
        setup_webkit()
    print("Next: describe the design you want, then run `uv run nnw-theme preview`.")


def _print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)


def command_package(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    destination, warnings = build_archive(
        theme, root / args.output_dir, allow_remote_media=args.allow_remote_media
    )
    _print_warnings(warnings)
    print(destination)


def command_setup(_args: argparse.Namespace) -> None:
    root = find_root()
    snapshot = ensure_snapshot(root)
    if snapshot.downloaded:
        print(
            f"Downloaded and verified {len(snapshot.downloaded)} NetNewsWire "
            f"{snapshot.release} rendering inputs."
        )
    else:
        print(f"NetNewsWire {snapshot.release} rendering inputs are already verified.")
    setup_webkit()


def command_render(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    targets = normal_targets()
    if args.fixtures:
        requested = set(args.fixtures)
        targets = [target for target in targets if target.fixture in requested]
        unknown = requested - {target.fixture for target in targets}
        if unknown:
            raise ThemeError(f"unknown fixture(s): {', '.join(sorted(unknown))}")
    site = render_site(root, theme, targets)
    print(site / "index.html")


def command_check(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    archive, warnings = build_archive(
        theme, root / "build" / "release", allow_remote_media=args.allow_remote_media
    )
    _print_warnings(warnings)
    targets = check_targets()
    site = render_site(root, theme, targets)
    failures = check_pages(site, targets)
    report_path = root / "build" / "check-report.txt"
    if failures:
        report_path.write_text("FAIL\n" + "\n".join(failures) + "\n", encoding="utf-8")
        raise ThemeError("browser checks failed:\n- " + "\n- ".join(failures))
    report_path.write_text(
        f"PASS\n{len(targets)} WebKit renders checked\nPackage: {archive.name}\n",
        encoding="utf-8",
    )
    print(f"PASS: {len(targets)} WebKit renders and {archive.name}")
    print(f"Preview: {site / 'index.html'}")


def _project_mtime(root: Path) -> int:
    watched = [*root.glob("*.nnwtheme/*"), *root.glob("fixtures/*.toml")]
    return max((path.stat().st_mtime_ns for path in watched if path.is_file()), default=0)


def command_preview(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    site = render_site(root, theme, normal_targets())
    with serve(site) as url:
        print(f"Preview: {url}")
        if not args.no_open:
            webbrowser.open(url)
        previous = _project_mtime(root)
        print("Watching theme and fixtures. Press Ctrl-C to stop.")
        try:
            while True:
                time.sleep(1)
                current = _project_mtime(root)
                if current != previous:
                    render_site(root, theme, normal_targets())
                    previous = current
                    print("Rebuilt preview.")
        except KeyboardInterrupt:
            print("\nPreview stopped.")


def _select_target(args: argparse.Namespace) -> RenderTarget:
    for target in normal_targets():
        if (
            target.fixture == args.fixture
            and target.platform == args.platform
            and target.appearance == args.appearance
        ):
            return target
    raise ThemeError("invalid screenshot target")


def command_screenshot(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    target = _select_target(args)
    site = render_site(root, theme, [target])
    failures = check_pages(site, [target])
    if failures:
        raise ThemeError("screenshot checks failed:\n- " + "\n- ".join(failures))
    source = site / "screenshots" / f"{target.slug}.png"
    print(source)
    if args.promote:
        destination = root / "screenshots" / "theme-preview.png"
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, destination)
        print(f"Promoted marketplace screenshot: {destination}")


def command_bump(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    metadata = read_plist(theme)
    current = metadata.get("Version")
    if not isinstance(current, int) or isinstance(current, bool):
        raise ThemeError("Info.plist Version must be an integer")
    proposed = current + 1
    if not args.yes and not _prompt_confirm(f"Increase Version from {current} to {proposed}?"):
        raise ThemeError("version bump cancelled")
    metadata["Version"] = proposed
    write_plist(theme / "Info.plist", metadata)
    print(f"Version is now {proposed}. Commit this change before publishing.")


def command_release_check(args: argparse.Namespace) -> None:
    root = find_root()
    theme = find_theme(root)
    current = read_plist(theme)
    previous_path = Path(args.previous_asset)
    with zipfile.ZipFile(previous_path) as archive:
        info_names = [name for name in archive.namelist() if name.endswith("/Info.plist")]
        if len(info_names) != 1:
            raise ThemeError("previous release must contain exactly one Info.plist")
        previous = plistlib.loads(archive.read(info_names[0]))
        old_bundle = info_names[0].split("/", 1)[0]
    if old_bundle != theme.name:
        raise ThemeError(f"bundle filename changed after release: {old_bundle} -> {theme.name}")
    if previous.get("ThemeIdentifier") != current.get("ThemeIdentifier"):
        raise ThemeError("ThemeIdentifier cannot change after the first release")
    if not isinstance(current.get("Version"), int) or current["Version"] <= previous.get(
        "Version", 0
    ):
        raise ThemeError("Info.plist Version must increase after the previous release")
    print(
        f"Release identity is stable and Version increases "
        f"{previous.get('Version')} -> {current['Version']}."
    )


def _add_common_remote_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-remote-media",
        action="store_true",
        help="acknowledge warnings for theme-owned remote fonts/images/media",
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="nnw-theme", description="Build a NetNewsWire theme")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="personalize this template")
    init.add_argument("--name")
    init.add_argument("--creator")
    init.add_argument("--homepage")
    init.add_argument("--identifier")
    init.add_argument("--confirm-identifier")
    init.add_argument("--github-user")
    init.add_argument("--marketplace", choices=("yes", "no"))
    init.add_argument("--install-browser", action=argparse.BooleanOptionalAction, default=None)
    init.set_defaults(function=command_init)

    setup = commands.add_parser(
        "setup", help="download pinned rendering inputs and install or locate WebKit"
    )
    setup.set_defaults(function=command_setup)

    render = commands.add_parser("render", help="build the static preview gallery")
    render.add_argument("fixtures", nargs="*")
    render.set_defaults(function=command_render)

    preview = commands.add_parser("preview", help="serve and rebuild the preview gallery")
    preview.add_argument("--no-open", action="store_true")
    preview.set_defaults(function=command_preview)

    package = commands.add_parser("package", help="validate and build the release ZIP")
    package.add_argument("--output-dir", default="dist")
    _add_common_remote_flag(package)
    package.set_defaults(function=command_package)

    check = commands.add_parser("check", help="run package and WebKit release checks")
    _add_common_remote_flag(check)
    check.set_defaults(function=command_check)

    screenshot = commands.add_parser("screenshot", help="capture a checked preview image")
    screenshot.add_argument("--fixture", choices=("article", "kitchen-sink"), default="article")
    screenshot.add_argument("--platform", choices=("mac", "iphone", "ipad"), default="mac")
    screenshot.add_argument("--appearance", choices=("light", "dark"), default="light")
    screenshot.add_argument("--promote", action="store_true")
    screenshot.set_defaults(function=command_screenshot)

    bump = commands.add_parser("bump", help="increase the plist Version integer")
    bump.add_argument("--yes", action="store_true")
    bump.set_defaults(function=command_bump)

    marketplace = commands.add_parser("marketplace", help="manage marketplace participation")
    marketplace_commands = marketplace.add_subparsers(dest="marketplace_command", required=True)
    enable = marketplace_commands.add_parser("enable", help="add the discovery topic on GitHub")
    enable.set_defaults(function=lambda _args: marketplace_enable())

    release_check = commands.add_parser("release-check", help=argparse.SUPPRESS)
    release_check.add_argument("--previous-asset", required=True)
    release_check.set_defaults(function=command_release_check)
    return root


def main() -> None:
    try:
        args = parser().parse_args()
        args.function(args)
    except ThemeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
