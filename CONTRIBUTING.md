# Contributing

Contributions are welcome, especially source corrections, improved metadata, and newly released open Chinese fonts.

## Adding or updating a font

1. Link the rightsholder’s official source and exact license text.
2. Show that the license permits independent redistribution of the font binary. “Free for commercial use” is not sufficient evidence.
3. Prefer the original, unmodified upstream TTF, OTF, WOFF, or WOFF2. Do not convert or subset a font with a Reserved Font Name unless every derived-font requirement is handled.
4. Place the binary and all notices under `plugins/chinese-character-open/fonts/<id>-<slug>/`.
5. Update the single manifest at `plugins/chinese-character-open/catalog/fonts.json`, including byte size and SHA-256.
6. Add or update a numbered visual preview.
7. Run `python3 scripts/validate_catalog.py` and the plugin commands from the README.

If redistribution is unclear or restricted, use `link-only` and do not commit a font binary, archive, converted file, or cache.

## License changes

License fixes take priority over convenience. A pull request may move a font from `bundled` to `link-only` when upstream terms change or earlier evidence proves insufficient.
