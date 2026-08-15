#!/usr/bin/env python3
"""List, inspect, preview, and export the Chinese Character Open collection."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PLUGIN_ROOT / "catalog" / "fonts.json"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


CATALOG = load_catalog()
FONTS = {font["id"]: font for font in CATALOG["fonts"]}
DEFAULT_SHORTLIST = CATALOG["defaultShortlist"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def match_font(value: str) -> str:
    key = value.strip().casefold()
    if key in FONTS:
        return key
    for font_id, item in FONTS.items():
        candidates = [item["slug"], item["name"]["en"], item["name"]["zhHans"]]
        if key in {str(candidate).casefold() for candidate in candidates}:
            return font_id
    raise ValueError(f"Unknown font {value!r}. Choose an ID from 01 to 24.")


def selected_fonts(values: list[str] | None, require_bundled: bool = False) -> list[tuple[str, dict]]:
    raw_values = values or DEFAULT_SHORTLIST
    resolved: list[str] = []
    for raw in raw_values:
        for value in raw.split(","):
            font_id = match_font(value)
            if font_id not in resolved:
                resolved.append(font_id)

    fonts = [(font_id, FONTS[font_id]) for font_id in resolved]
    if require_bundled:
        link_only = [(font_id, item) for font_id, item in fonts if item["distribution"]["mode"] != "bundled"]
        if link_only:
            details = "; ".join(
                f'{font_id} {item["name"]["en"]}: {item["source"]["homepage"]}'
                for font_id, item in link_only
            )
            raise ValueError(f"Link-only fonts cannot be exported or rendered from this repository: {details}")
    return fonts


def asset_path(item: dict) -> Path:
    assets = item.get("assets", [])
    if len(assets) != 1:
        raise ValueError(f'{item["name"]["en"]} does not have exactly one bundled asset.')
    return PLUGIN_ROOT / assets[0]["path"]


def verify_asset(item: dict) -> Path:
    path = asset_path(item)
    asset = item["assets"][0]
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != asset["bytes"]:
        raise ValueError(f"Size mismatch for {path}")
    if sha256(path) != asset["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return path


def copy_safely(source: Path, destination: Path, force: bool) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256(source) == sha256(destination):
            return "unchanged"
        if not force:
            raise FileExistsError(f"Refusing to overwrite {destination}; rerun with --force if intended.")
    shutil.copy2(source, destination)
    return "copied"


def write_safely(path: Path, content: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return "unchanged"
        if not force:
            raise FileExistsError(f"Refusing to overwrite {path}; rerun with --force if intended.")
    path.write_text(content, encoding="utf-8")
    return "written"


def css_block(item: dict, filename: str) -> str:
    css = item["css"]
    asset = item["assets"][0]
    return "\n".join(
        [
            "@font-face {",
            f'  font-family: "{css["family"]}";',
            f'  src: url("./{filename}") format("{asset["format"]}");',
            f'  font-weight: {css["weight"]};',
            f'  font-style: {css["style"]};',
            "  font-display: swap;",
            "}",
        ]
    )


def export_fonts(fonts: list[tuple[str, dict]], output_dir: Path, force: bool) -> dict:
    output_dir = output_dir.expanduser().absolute()
    output_dir.mkdir(parents=True, exist_ok=True)
    css_parts: list[str] = []
    exported: list[dict] = []

    for font_id, item in fonts:
        source = verify_asset(item)
        filename = f'{font_id}-{item["slug"]}{source.suffix.lower()}'
        font_status = copy_safely(source, output_dir / filename, force)
        css_parts.append(css_block(item, filename))

        license_outputs: list[str] = []
        license_root = output_dir / "licenses" / item["slug"]
        source_license_root = PLUGIN_ROOT / "fonts" / f'{font_id}-{item["slug"]}' / "licenses"
        for relative_license in item["license"]["files"]:
            license_path = PLUGIN_ROOT / relative_license
            if not license_path.is_file():
                raise FileNotFoundError(license_path)
            destination = license_root / license_path.relative_to(source_license_root)
            copy_safely(license_path, destination, force)
            license_outputs.append(str(destination))

        exported.append(
            {
                "id": font_id,
                "slug": item["slug"],
                "family": item["css"]["family"],
                "font": str(output_dir / filename),
                "font_status": font_status,
                "licenses": license_outputs,
                "source": item["source"]["homepage"],
            }
        )

    css_path = output_dir / "chinese-character-open.css"
    css_content = "\n\n".join(css_parts) + "\n"
    css_status = write_safely(css_path, css_content, force)
    return {"output_dir": str(output_dir), "css": str(css_path), "css_status": css_status, "fonts": exported}


def preview_html(fonts: list[tuple[str, dict]], text: str, stylesheet: str) -> str:
    cards = []
    for font_id, item in fonts:
        css = item["css"]
        best_for = " · ".join(item["bestFor"])
        cards.append(
            f'''<article class="card" style="--family: '{html.escape(css['family'])}">
  <div class="meta"><span>{font_id}</span><strong>{html.escape(item['name']['en'])}</strong><small>{html.escape(item['name']['zhHans'])}</small></div>
  <div class="sample">{html.escape(text)}</div>
  <div class="secondary">搜索 · 数据 · 仪表盘 · 预览</div>
  <div class="usage">{html.escape(best_for)}</div>
</article>'''
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chinese Character Open Preview</title>
  <link rel="stylesheet" href="{html.escape(stylesheet)}">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 40px; background: #eef1f0; color: #171a1f; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; }}
    header {{ max-width: 1180px; margin: 0 auto 24px; }}
    .eyebrow {{ color: #139b73; font-size: 12px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; }}
    h1 {{ margin: 8px 0 0; font-size: 32px; letter-spacing: -.04em; }}
    main {{ max-width: 1180px; margin: auto; display: grid; gap: 16px; }}
    .card {{ min-height: 250px; padding: 24px 26px; border: 1px solid #d9dddc; border-radius: 20px; background: rgba(255,255,255,.9); box-shadow: 0 12px 28px rgba(20,30,28,.06); }}
    .meta {{ display: grid; grid-template-columns: 34px auto 1fr; align-items: baseline; gap: 10px; }}
    .meta span {{ color: #139b73; font-weight: 900; }}
    .meta strong {{ font-size: 16px; }}
    .meta small, .usage {{ color: #777e7c; }}
    .sample {{ margin-top: 34px; overflow-wrap: anywhere; font-family: var(--family), "PingFang SC", sans-serif; font-size: clamp(34px, 5vw, 58px); line-height: 1.18; }}
    .secondary {{ margin-top: 14px; color: #666e6c; font-family: var(--family), "PingFang SC", sans-serif; font-size: 18px; }}
    .usage {{ margin-top: 16px; font-size: 13px; }}
  </style>
</head>
<body>
  <header><div class="eyebrow">Chinese Character Open</div><h1>大胆个性中文字体</h1></header>
  <main>{''.join(cards)}</main>
</body>
</html>
'''


def command_list(args: argparse.Namespace) -> int:
    rows = [
        {
            "id": item["id"],
            "slug": item["slug"],
            "name": item["name"]["en"],
            "chinese_name": item["name"]["zhHans"],
            "distribution": item["distribution"]["mode"],
            "license": item["license"]["id"],
        }
        for item in CATALOG["fonts"]
    ]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print("ID  MODE       LICENSE       FONT")
        for row in rows:
            print(f'{row["id"]:<3} {row["distribution"]:<10} {row["license"]:<13} {row["name"]} / {row["chinese_name"]}')
    return 0


def command_info(args: argparse.Namespace) -> int:
    font_id = match_font(args.font)
    print(json.dumps(FONTS[font_id], ensure_ascii=False, indent=2))
    return 0


def command_export(args: argparse.Namespace) -> int:
    result = export_fonts(selected_fonts(args.font, require_bundled=True), Path(args.output_dir), args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_preview(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().absolute()
    if output.suffix.lower() != ".html":
        raise ValueError("--output must end in .html")
    fonts = selected_fonts(args.font, require_bundled=True)
    asset_dir = output.parent / f"{output.stem}-assets"
    export_fonts(fonts, asset_dir, args.force)
    stylesheet = f"./{asset_dir.name}/chinese-character-open.css"
    write_safely(output, preview_html(fonts, args.text, stylesheet), args.force)
    print(json.dumps({"preview": str(output), "assets": str(asset_dir), "fonts": [font_id for font_id, _ in fonts]}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="List all 24 catalog entries")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON")
    list_parser.set_defaults(func=command_list)

    info_parser = commands.add_parser("info", help="Show metadata, license, and source for one font")
    info_parser.add_argument("font", help="Font ID, slug, English name, or Chinese name")
    info_parser.set_defaults(func=command_info)

    export_parser = commands.add_parser("export", help="Copy bundled fonts, CSS, and licenses to a directory")
    export_parser.add_argument("--font", action="append", help="Font ID, slug, or comma-separated list; defaults to 14,17,18")
    export_parser.add_argument("--output-dir", required=True, help="Destination directory")
    export_parser.add_argument("--force", action="store_true", help="Replace different generated files")
    export_parser.set_defaults(func=command_export)

    preview_parser = commands.add_parser("preview", help="Generate a portable HTML comparison for bundled fonts")
    preview_parser.add_argument("--font", action="append", help="Font ID, slug, or comma-separated list; defaults to 14,17,18")
    preview_parser.add_argument("--text", default="一句 prompt，直达原版 UI。", help="Comparison text")
    preview_parser.add_argument("--output", required=True, help="Destination HTML file")
    preview_parser.add_argument("--force", action="store_true", help="Replace different generated files")
    preview_parser.set_defaults(func=command_preview)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
