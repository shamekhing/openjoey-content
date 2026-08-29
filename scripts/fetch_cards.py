#!/usr/bin/env python3
"""Download the Yu-Gi-Oh! card database + images for OpenJoey2.

This is the canonical asset-fetch tool. It is intentionally more robust than a
naive "curl every id" loop:

  * It queries the YGOProDeck ``cardinfo.php?name=`` endpoint with a real
    browser User-Agent (so we don't get 403'd), then reads back the
    authoritative ``image_url`` / ``image_url_small`` from the response. The
    filename stem always matches what the C++ engine expects:

        openjoey::Card::imageId  (== cardId == YGOProDeck ``id``)

    and the on-disk path is ``data/images/<imageId>.jpg`` -- exactly where
    ``CardImageCache`` looks (via ``ContentPaths::cardImgDir()``).

  * Per-download retry with exponential backoff and a >1KB size check, so a
    truncated/placeholder response is never accepted.

  * Atomic writes via a ``.tmp`` sibling renamed into place on success, so a
    crash mid-download never leaves a partial image for the engine to load.

  * Skip-if-present, so re-running is fast and resume-able.

  * A thread-pool mode (``--images --jobs N``) for bulk downloads.

It also fetches the card back to ``data/card_back.png`` (the path
``ContentPaths::cardBackImg()`` points at -- note the .png extension, which is
what DuelScreen loads). If PIL is available the JPEG is re-encoded as PNG;
otherwise the raw JPEG bytes are written to the .png path, which raylib loads
fine because stb_image sniffs content magic bytes, not the file extension.

Usage:
    python3 scripts/fetch_cards.py                  # JSON + banlist only
    python3 scripts/fetch_cards.py --images         # also download card images
    python3 scripts/fetch_cards.py --images --jobs 8 # with a thread pool
    python3 scripts/fetch_cards.py --images --no-card-back

NOTE: requires network access. The app also downloads images on demand at
runtime via CardImageCache, so ``--images`` is optional -- run it once to
pre-warm the cache for offline play.
"""
import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
BANLIST_API = "https://db.ygoprodeck.com/api/v7/forbiddenLimitedList.php"
IMG_DIR = DATA / "images"           # MUST match ContentPaths::cardImgDir()
CARD_BACK = DATA / "card_back.png"  # MUST match ContentPaths::cardBackImg()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
DELAY = 0.3  # polite pause between lookups against the API


def get(url, attempts=3):
    """GET with retry + exponential backoff. Raises on hard/4xx failure."""
    last_err = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                raise  # client errors are not retryable
            last_err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
        if i < attempts - 1:
            time.sleep(2 ** (i + 1))
    raise last_err if last_err else RuntimeError("failed: " + url)


def fetch_image_url(card_name):
    """Ask YGOProDeck for a card by name; return its image URL (or None)."""
    params = urllib.parse.urlencode({"name": card_name})
    try:
        data = json.loads(get(API + "?" + params).decode())
        images = data["data"][0].get("card_images", [])
        if not images:
            return None
        return images[0].get("image_url") or images[0].get("image_url_small")
    except Exception as e:
        print("  API error for '%s': %s" % (card_name, e))
        return None


def id_from_url(url):
    """Pull the numeric card id out of a YGOProDeck image URL."""
    try:
        stem = pathlib.Path(urllib.parse.urlparse(url).path).stem
        return int(stem)
    except (ValueError, TypeError):
        return None


def download_bytes(url, dest):
    """Download `url` to `dest` atomically. True only for a real (>1KB) image."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        data = get(url)
    except Exception as e:
        print("  download error for %s: %s" % (url, e))
        return False
    if len(data) < 1024:  # YGOProDeck serves a ~1KB placeholder on misses
        return False
    tmp.write_bytes(data)
    tmp.replace(dest)
    return True


def download_card_image(card):
    """Download a single card image. Returns (name, ok, image_id_str)."""
    name = card.get("name", "")
    image_id = card.get("id") or card.get("cid")
    if not image_id:
        return (name, False, "n/a")

    id_str = str(image_id)
    dest = IMG_DIR / (id_str + ".jpg")
    if dest.exists() and dest.stat().st_size > 1024:
        return (name, True, id_str)  # skip existing

    img_url = fetch_image_url(name)
    if not img_url:
        return (name, False, id_str)

    # Use the URL's id (authoritative) if it differs from the json id.
    url_id = id_from_url(img_url)
    if url_id is not None:
        id_str = str(url_id)
        dest = IMG_DIR / (id_str + ".jpg")

    ok = download_bytes(img_url, dest)
    return (name, ok, id_str)


def download_images_threaded(cards, jobs):
    work = [c for c in cards if c.get("id") or c.get("cid")]
    if not work:
        print("no card ids found; skipping images")
        return
    idx = 0
    lock = threading.Lock()
    ok = skip = fail = 0

    def worker():
        nonlocal idx, ok, skip, fail
        while True:
            with lock:
                if idx >= len(work):
                    return
                card = work[idx]
                idx += 1
            name, was_ok, id_str = download_card_image(card)
            time.sleep(DELAY)
            with lock:
                if was_ok:
                    ok += 1
                else:
                    fail += 1

    threads = [threading.Thread(target=worker) for _ in range(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("\n=== images: %d downloaded, %d skipped, %d failed / %d total ==="
          % (ok, len(work) - ok - fail, fail, len(work)))
    print("Images in: %s" % IMG_DIR)


def write_cards():
    DATA.mkdir(parents=True, exist_ok=True)
    text = get(API).decode("utf-8")
    obj = json.loads(text)
    if isinstance(obj, list):
        obj = {"data": obj}
    cards_path = DATA / "cards.json"
    cards_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    print("wrote %s (%d cards)" % (cards_path, len(obj["data"])))


def try_write_banlist():
    try:
        text = get(BANLIST_API).decode("utf-8")
        obj = json.loads(text)
        path = DATA / "banlist.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        print("wrote %s" % path)
    except Exception as e:
        print("skip banlist.json: %s" % e, file=sys.stderr)


def download_card_back(do_download):
    if not do_download:
        print("card_back.png  skip  (--no-card-back)")
        return
    if CARD_BACK.exists():
        print("card_back.png  skip  (already exists)")
        return
    print("card_back.png  fetch ...", end=" ", flush=True)
    try:
        data = get("https://images.ygoprodeck.com/images/cards/back.jpg")
        if len(data) < 1024:
            print("placeholder"); return
        try:
            from PIL import Image
            import io
            Image.open(io.BytesIO(data)).save(str(CARD_BACK), "PNG")
        except ImportError:
            CARD_BACK.write_bytes(data)  # raylib loads by content magic, not .png ext
        print("ok  (%dKB)" % (CARD_BACK.stat().st_size // 1024))
    except Exception as e:
        print("download error: %s" % e)


def main():
    ap = argparse.ArgumentParser(description="Download Yu-Gi-Oh! DB + images for OpenJoey2")
    ap.add_argument("--images", action="store_true", help="also download card images")
    ap.add_argument("--jobs", type=int, default=8, help="image download threads")
    ap.add_argument("--no-card-back", action="store_true", help="skip fetching the card back")
    args = ap.parse_args()

    write_cards()
    try_write_banlist()

    if args.images:
        obj = json.loads((DATA / "cards.json").read_text())
        download_card_back(not args.no_card_back)
        print()
        download_images_threaded(obj["data"], args.jobs)


if __name__ == "__main__":
    main()
