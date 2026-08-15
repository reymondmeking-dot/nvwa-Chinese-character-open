#!/usr/bin/env python3
"""Validate the font catalog, licenses, binaries, and plugin wiring."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont, TTLibError
except ImportError as error:  # pragma: no cover - exercised by missing dependency
    raise SystemExit("fontTools is required. Run: python3 -m pip install 'fonttools[woff]'") from error


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "chinese-character-open"
CATALOG_PATH = PLUGIN_ROOT / "catalog" / "fonts.json"
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar"}
EXPECTED_IDS = [f"{number:02d}" for number in range(1, 25)]
MAX_GITHUB_FILE_BYTES = 100 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_inside(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as error:
        raise ValueError(f"Path escapes plugin root: {relative}") from error
    return candidate


def main() -> int:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"catalog error: {error}", file=sys.stderr)
        return 1

    fonts = catalog.get("fonts", [])
    ids = [font.get("id") for font in fonts]
    slugs = [font.get("slug") for font in fonts]
    require(ids == EXPECTED_IDS, "Catalog IDs must be exactly 01 through 24 in order.")
    require(len(set(slugs)) == 24, "Catalog slugs must be unique.")
    require(catalog.get("defaultShortlist") == ["14", "17", "18"], "Default shortlist must be 14, 17, 18.")

    expected_assets: set[Path] = set()
    bundled_count = 0
    link_only_count = 0
    total_bytes = 0
    expected_font_dirs: set[str] = set()

    for font in fonts:
        font_id = font.get("id", "??")
        slug = font.get("slug", "")
        label = f"{font_id} {slug}"
        font_dir_name = f"{font_id}-{slug}"
        font_dir = PLUGIN_ROOT / "fonts" / font_dir_name
        expected_font_dirs.add(font_dir_name)
        require(font_dir.is_dir(), f"{label}: missing font directory {font_dir}")

        source = font.get("source", {})
        require(str(source.get("homepage", "")).startswith("https://"), f"{label}: homepage must use HTTPS")
        require(str(source.get("license", "")).startswith("https://"), f"{label}: license evidence must use HTTPS")

        distribution = font.get("distribution", {}).get("mode")
        assets = font.get("assets", [])
        license_info = font.get("license", {})
        license_files = license_info.get("files", [])

        if distribution == "link-only":
            link_only_count += 1
            require(not assets, f"{label}: link-only entry must have no assets")
            require(not license_files, f"{label}: link-only entry must not claim a local license file")
            require((font_dir / "LINK_ONLY.md").is_file(), f"{label}: missing LINK_ONLY.md")
            if font_dir.is_dir():
                binaries = [path for path in font_dir.rglob("*") if path.suffix.lower() in FONT_EXTENSIONS]
                require(not binaries, f"{label}: link-only directory contains font binaries: {binaries}")
            continue

        require(distribution == "bundled", f"{label}: invalid distribution mode {distribution!r}")
        if distribution != "bundled":
            continue
        bundled_count += 1
        require(len(assets) == 1, f"{label}: bundled entry must declare exactly one asset")
        require(bool(license_files), f"{label}: bundled entry must declare license files")

        for relative_license in license_files:
            try:
                license_path = resolve_inside(PLUGIN_ROOT, relative_license)
            except ValueError as error:
                errors.append(f"{label}: {error}")
                continue
            require(license_path.is_file(), f"{label}: missing license file {relative_license}")
            if license_path.is_file():
                require(license_path.stat().st_size > 100, f"{label}: license file is unexpectedly small: {relative_license}")

        if len(assets) != 1:
            continue
        asset = assets[0]
        try:
            asset_path = resolve_inside(PLUGIN_ROOT, asset.get("path", ""))
        except ValueError as error:
            errors.append(f"{label}: {error}")
            continue
        expected_assets.add(asset_path)
        require(asset_path.parent == font_dir / "files", f"{label}: asset must live in its files directory")
        require(asset_path.suffix.lower() in FONT_EXTENSIONS, f"{label}: unsupported asset extension")
        require(asset_path.is_file(), f"{label}: missing asset {asset.get('path')}")
        require(not asset_path.is_symlink(), f"{label}: font asset must not be a symlink")
        if not asset_path.is_file():
            continue

        actual_bytes = asset_path.stat().st_size
        total_bytes += actual_bytes
        require(actual_bytes == asset.get("bytes"), f"{label}: byte size mismatch")
        require(actual_bytes < MAX_GITHUB_FILE_BYTES, f"{label}: asset exceeds GitHub's 100 MiB limit")
        require(sha256(asset_path) == asset.get("sha256"), f"{label}: SHA-256 mismatch")

        try:
            with TTFont(asset_path, lazy=False) as opened_font:
                cmap = opened_font.getBestCmap() or {}
                for character in "中文":
                    require(ord(character) in cmap, f"{label}: missing required Chinese glyph {character}")
                require("name" in opened_font, f"{label}: missing OpenType name table")
        except (TTLibError, OSError, ValueError) as error:
            errors.append(f"{label}: fontTools could not open asset: {error}")

        if license_info.get("id") == "IPA-1.0":
            require(asset_path.suffix.lower() == ".ttf", f"{label}: IPA asset must remain the upstream TTF")

    font_root = PLUGIN_ROOT / "fonts"
    actual_font_dirs = {path.name for path in font_root.iterdir() if path.is_dir()}
    require(actual_font_dirs == expected_font_dirs, "Font directories must match the 24 catalog entries exactly.")

    actual_assets = {
        path.resolve()
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
    }
    unregistered = sorted(str(path.relative_to(REPO_ROOT)) for path in actual_assets - expected_assets)
    missing = sorted(str(path.relative_to(REPO_ROOT)) for path in expected_assets - actual_assets)
    require(not unregistered, f"Unregistered font binaries found: {unregistered}")
    require(not missing, f"Registered font binaries missing from scan: {missing}")

    archives = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in ARCHIVE_EXTENSIONS
    )
    require(not archives, f"Font/archive packages are not allowed in the repository: {archives}")

    plugin_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    require(plugin_manifest.get("name") == "chinese-character-open", "Plugin manifest name mismatch")
    require(plugin_manifest.get("version") == "0.1.0", "Plugin version must be 0.1.0 for the initial release")

    marketplace = json.loads((REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    require(marketplace.get("name") == "nvwa-chinese-character-open", "Marketplace name mismatch")
    marketplace_plugins = marketplace.get("plugins", [])
    require(len(marketplace_plugins) == 1, "Marketplace must expose exactly one plugin")
    if marketplace_plugins:
        require(marketplace_plugins[0].get("name") == "chinese-character-open", "Marketplace plugin name mismatch")
        require(marketplace_plugins[0].get("source", {}).get("path") == "./plugins/chinese-character-open", "Marketplace source path mismatch")

    require(bundled_count == 20, f"Expected 20 bundled fonts, found {bundled_count}")
    require(link_only_count == 4, f"Expected 4 link-only fonts, found {link_only_count}")

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Validated 24 entries: {bundled_count} bundled, {link_only_count} link-only, "
        f"{total_bytes / (1024 * 1024):.1f} MiB of registered font assets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
