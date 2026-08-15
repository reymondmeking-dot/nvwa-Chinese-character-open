---
name: chinese-character-open
description: Browse a numbered catalog of 24 Chinese fonts, inspect official sources and licenses, and preview, compare, export, or apply the 20 safely redistributable upstream font files. Use when a user asks for Chinese typography, a reusable Chinese font library, numbered font comparisons, webfont CSS, or installation of a Chinese font into a website or UI project.
---

# Chinese Character Open

Use the numbered 24-font collection to shortlist Chinese typography and safely apply fonts whose upstream licenses permit redistribution. The default “大胆个性” shortlist is `14`, `17`, and `18`.

## Workflow

1. Inspect the request and project before writing. Treat review-only requests as read-only.
2. Read [references/font-catalog.md](references/font-catalog.md) before choosing a font or making license claims. Treat `catalog/fonts.json` at the plugin root as the authoritative machine-readable catalog.
3. Run `scripts/fontkit.py list` to show all 24 IDs, distribution modes, and licenses. Use `info` for exact source and usage metadata.
4. For visual selection, use the four numbered preview sheets or generate a same-copy comparison for bundled fonts with `preview`; serve it over localhost and verify glyphs visually.
5. For project use, run `export` into a project-owned font directory. This copies the original upstream font file, generated `@font-face` rules, and all license files.
6. Build and browser-check the result. Confirm the selected Chinese glyphs render, no text clips, and no font request fails.

## Commands

List or inspect the collection:

```bash
python3 scripts/fontkit.py list
python3 scripts/fontkit.py list --json
python3 scripts/fontkit.py info 17
```

Generate a portable comparison page. When `--font` is omitted, the default is `14,17,18`:

```bash
python3 scripts/fontkit.py preview \
  --text "一句 prompt，直达原版 UI。" \
  --output /absolute/path/font-preview.html
```

Serve the preview’s parent directory over `http://127.0.0.1` before browser inspection. Do not rely on a `file://` URL for local font QA.

Export one or more bundled fonts with CSS and licenses:

```bash
python3 scripts/fontkit.py export \
  --font 14 \
  --output-dir /absolute/project/path/public/fonts/chinese-character-open
```

Use `--force` only when replacing an existing generated file is explicitly intended.

## Application rules

- Default shortlist for “大胆个性”: `14`, `17`, `18`.
- The catalog contains 24 entries: 20 `bundled`, 4 `link-only`.
- Never bypass `link-only` for `01` MiSans, `02` HarmonyOS Sans SC, `03` Alibaba PuHuiTi 3.0, or `06` Alimama FangYuanTi VF. Return their official links instead.
- Fonts `10` and `20` use IPA Font License 1.0. Export only their unmodified upstream TTF files; do not subset, convert, rename, or edit them through this skill.
- Use display faces for large text, not automatically for long UI copy or dense body text.
- Keep a neutral Chinese sans-serif fallback after the selected face.
- Preserve every copied license file alongside font assets.
- Keep generated CSS family aliases; do not rename font binaries or edit outlines unless the user explicitly requests font engineering and the license permits it.
- For Fusion Pixel, prefer sizes divisible by 12px to keep the pixel grid crisp.
- Do not describe the entire collection as having one license. Plugin code is MIT; every font remains under its own upstream license.

## Integration

Adapt the generated CSS to the project rather than forcing one framework pattern. For Vite or static sites, place exported font files under a public font directory and copy the generated `@font-face` blocks into the project stylesheet with root-relative URLs. For bundler-managed assets, move files under the source tree and let the bundler rewrite URLs.

After integration, verify both the font request and the computed `font-family` in the browser.
