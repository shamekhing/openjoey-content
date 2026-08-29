# openjoey-content

All runtime content for the OpenJoey split. This repo intentionally keeps
**only small, hand-maintained files in git**; anything fetched or generated is
gitignored and produced by the pipeline below.

| Path | In git? | Producer |
|---|---|---|
| `data/settings.json` | yes | hand-maintained defaults |
| `data/decks/` | yes | hand-maintained decks |
| `docs/SD_RuleBook_EN_10.pdf` | yes | reference (the rules this engine implements) |
| `scripts/fetch_cards.py` | yes | — downloads `cards.json` + card images |
| `scripts/make_assets.py` | yes | — generates `card_back.png`, menu background |
| `data/cards.json` (28MB) | **no** | `fetch_cards.py` / CI pipeline |
| `data/images/` (2.3GB) | **no** | app runtime (CardImageCache) / `fetch_cards.py --images` |
| `data/card_back.png`, `data/assets/backgrounds/*` | **no** | `make_assets.py` / CI pipeline |

## Getting content onto a fresh clone

Either run the scripts (network required):

```sh
python3 scripts/make_assets.py
python3 scripts/fetch_cards.py            # cards.json (add --images to bulk-fetch art)
```

…or download the assets from the `content-latest` release of this repository
(created by the `fetch-content` GitHub Actions pipeline).

At build time `openjoey-app` symlinks this repo's `data/` next to the binary so
runtime paths stay unchanged: `<builddir>/data/...`.
