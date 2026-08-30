# openjoey-content — data contract

This repo holds everything the OpenJoey apps consume at runtime that is not
code. Formats here are load-bearing: other repos depend on the naming and
schema rules below.

## 1. Directory layout

```
data/
├── cards.json          # card database (generated — fetch_cards.py / CI)
├── images/<id>.jpg     # card art, one file per card (runtime-fetched)
├── card_back.png       # generated card back (make_assets.py)
├── card_back2.png      # spare back (in git; not yet referenced)
├── settings.json       # shipped-defaults reference (in git)
├── user_settings.json  # app-written overrides (gitignored)
├── decks/*.txt         # decks (in git)
└── assets/backgrounds/ # generated (menu background)
```

At build time `openjoey-app` symlinks `data/` into the build dir next to the
binary, so `<exe>/data/...` is the single runtime root.

## 2. `cards.json` — card database

YGOProDeck API v7 payload (`https://db.ygoprodeck.com/api/v7/cardinfo.php`
shape): `{"data": [ entry, ... ]}`. Parsed by
`openjoey::cards::parseYgoProDeckJson` — see `openjoey-cards/docs/API.md`
for the full parse contract (dedup by id, `"?"/string stats → 0`, Xyz `rank`
→ `level`, `imageId == cardId`, errors collected non-fatally).

Per-entry fields consumed: `id`, `name`, `desc`, `frameType`
(`spell`/`skill`/`trap`/everything-else→monster), `atk`, `def`, `level`,
`rank`.

## 3. Card images — the `<ygoproId>.jpg` contract

* `data/images/<cardId>.jpg` — full art; `data/images/<cardId>` must equal
  `Card::cardId` from `cards.json`. `CardImageCache` (openjoey-cards) and
  `fetch_cards.py` both use this naming.
* URLs: `https://images.ygoprodeck.com/images/cards/<id>.jpg` with
  `.../cards_small/<id>.jpg` as fallback.
* Missing files are fetched on demand at runtime (one background worker,
  curl-based) — bulk prefetch is optional (`fetch_cards.py --images --jobs N`).

## 4. Settings files

Two distinct files, different schemas:

* **`data/settings.json`** (in git) — shipped-defaults reference, grouped as
  `file` / `dir` / `url` / `app`. `openjoey::Settings::Load` (openjoey-core)
  applies it first: `file` / `dir` map onto the `Settings::Paths` path fields,
  `url` onto the URL fields (`cardsJsonUrl`, `cardImgUrl`, `cardImgSmallUrl`),
  `app` onto the window/download options. Path values are content-root
  relative (`data/cards.json`) and are resolved onto the effective data dir
  at load time; the compiled-in defaults in `Settings` are the fallback when
  the file (or a key) is absent.
* **`data/user_settings.json`** (gitignored, app-written) — what
  `Settings::Save()` produces and `Settings::Load()` applies last (it wins
  over `settings.json`). Same nested schema; partial files are fine — every
  missing key falls back to its earlier layer. The pre-0.2 flat layout
  (top-level `screenWidth`, …, plus a `paths` object with the old
  `ygoprodeckUrl` key names) is still accepted for older files.

Both files resolve in the same data dir (`Settings::settingsFile(argv0)` /
`referenceFile(argv0)`): `<exeDir>/data/` wins when the file exists there,
else `<cwd>/data/`, else `<exeDir>/data/` as the creation target.

## 5. Decks — `decks/*.txt`

* One cardId per line (decimal, matching `cards.json` ids).
* `#` starts a comment line; blank lines ignored.
* ≤ 3 copies per card id (classic-format limiter; UI enforces it via the
  copy counter).
* `default.txt` is the 40-card classic-era starter: the duel loads it whenever
  it starts outside the deck editor (`DuelScreen::buildDecks` via
  `loadDefaultDeck()`), and the editor loads it with `[L]`
  (`DeckEditorScreen::LoadDeck("default")`). It contains every wired
  classic-effect card from `duel/ClassicCatalog.hpp` +
  `field/ClassicEffects.hpp` (plus their Fusion/Ritual targets and classic
  normal staples as the tribute ladder).

## 6. Fetch pipeline

* `scripts/fetch_cards.py` — regenerates `cards.json` from the YGOProDeck
  API; flags: `--images` (bulk art), `--jobs N` (threads, default 8),
  `--no-card-back`.
* `scripts/make_assets.py` — generates `data/card_back.png` and
  `assets/backgrounds/menu_background.png` (pillow).
* `.github/workflows/fetch.yml` (`fetch-content`) — monthly; runs both
  scripts and publishes the `content-latest` release. Card images are
  excluded (GitHub's 2 GB asset cap) — the runtime on-demand fetcher covers
  them.
