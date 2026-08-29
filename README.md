# openjoey-content

All runtime content for the OpenJoey split. This repo intentionally keeps
**only small, hand-maintained files in git**; anything fetched or generated is
gitignored and produced by the pipeline below.

| Path | In git? | Producer / purpose |
|---|---|---|
| `data/settings.json` | yes | human-readable reference of shipped defaults (see `docs/DATA.md` — the app's compiled-in defaults are authoritative) |
| `data/decks/` | yes | hand-maintained decks (`default.txt` = 40-card classic starter) |
| `data/card_back2.png` | yes | spare/alternative card back — **not yet referenced by any code or script** |
| `docs/SD_RuleBook_EN_10.pdf` | yes | reference (the rules this engine implements) |
| `scripts/fetch_cards.py` | yes | downloads `cards.json` (`--images` to bulk-fetch art) |
| `scripts/make_assets.py` | yes | generates `card_back.png` + menu background |
| `data/cards.json` (28 MB) | **no** | `fetch_cards.py` / CI pipeline |
| `data/images/` (2.3 GB) | **no** | app runtime (`CardImageCache`) / `fetch_cards.py --images` |
| `data/card_back.png`, `data/assets/backgrounds/*` | **no** | `make_assets.py` / CI pipeline |
| `data/user_settings.json` | **no** | written by the app (`SettingsScreen`) at runtime |

## Getting content onto a fresh clone

Either run the scripts (network required):

```sh
python3 scripts/make_assets.py
python3 scripts/fetch_cards.py            # cards.json (add --images to bulk-fetch art)
```

…or download the assets from the `content-latest` release of this repository
(created by the `fetch-content` GitHub Actions pipeline, monthly). Card images
are **not** release assets (GitHub caps assets at 2 GB); the app fetches them
on demand at runtime via `openjoey-cards`' `CardImageCache`.

At build time `openjoey-app` symlinks this repo's `data/` next to the binary so
runtime paths stay unchanged: `<builddir>/data/...`.

## Data contract

Formats and naming rules are specified in [`docs/DATA.md`](docs/DATA.md) —
notably the `<ygoproId>.jpg` image-naming contract that `Card::imageId`
(openjoey-cards) depends on.

Extracted from OpenJoey2@21f1d8e. Consumed by: openjoey-app (build-time
symlink), openjoey-cards (image-cache URL/naming contract).
