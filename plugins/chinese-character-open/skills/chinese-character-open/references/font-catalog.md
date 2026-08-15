# Font catalog and licensing policy

The authoritative catalog is [`../../../catalog/fonts.json`](../../../catalog/fonts.json). It contains exactly 24 numbered entries, official sources, license evidence, intended use, distribution mode, file size, and SHA-256 for every bundled binary.

## Distribution modes

- `bundled`: the unmodified upstream font binary is present under `fonts/`, together with its license files. The export command may copy it.
- `link-only`: no font binary is present. Return the official source link and do not download, convert, subset, cache, or copy it into a user project through this skill.

The four link-only entries are `01`, `02`, `03`, and `06`. “Free for commercial use” is not treated as permission to redistribute a font collection.

## License-sensitive entries

- `10` LXGW Neo XiHei and `20` LXGW Neo ZhiSong use IPA Font License 1.0. Their checked-in TTF files must remain byte-for-byte identical to the catalog hashes. Do not create a same-name WOFF2 or subset.
- `05` WenYuan Rounded SC, `09` Smiley Sans, and `23` LXGW WenKai have reserved-name considerations. Keep the checked-in upstream asset unmodified.
- `18` Fusion Pixel incorporates several upstream bitmap fonts. Preserve the entire `fonts/18-fusion-pixel/licenses/` tree when exporting it.

## Default bold shortlist

- `14` ZCOOL QingKe HuangYou: clean, compact, retro-geometric display voice.
- `17` LXGW Marker Gothic: broad marker strokes and editorial personality.
- `18` Fusion Pixel: intentionally digital, game-like, retro-computing voice; prefer sizes divisible by 12px.

Always preview the exact production sentence before applying a display font.
