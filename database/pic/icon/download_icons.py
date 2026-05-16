from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "scraper" / "data" / "pets_detailed.json"
PET_DIR = Path(__file__).resolve().parent / "pets"
SKILL_DIR = Path(__file__).resolve().parent / "skills"
WIKI_BASE = "https://wiki.biligame.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": WIKI_BASE + "/rocom/",
}


def load_data(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}, got {type(data).__name__}")
    return data


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name.strip())
    name = re.sub(r"\s+", " ", name)
    return name.strip(" .") or "unnamed"


def build_full_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return urljoin(WIKI_BASE, url)


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def resolve_skill_icon_url(skill: dict) -> str:
    direct_url = skill.get("icon_src") or ""
    if direct_url and direct_url.endswith(".png"):
        return direct_url

    legacy_url = skill.get("icon_href") or ""
    if legacy_url and legacy_url.startswith(("http://", "https://")) and legacy_url.endswith(".png"):
        return legacy_url

    skill_page = skill.get("skill_page") or ""
    if skill_page:
        page_path = (ROOT / "scraper" / skill_page).resolve()
        html_text = read_text_file(page_path)
        if html_text:
            icon_href = re.escape(legacy_url)
            candidates: list[str] = []
            title = skill.get("icon_title") or skill.get("name") or ""
            if icon_href:
                candidates.append(rf'(?is)<a[^>]+href="{icon_href}"[^>]*>.*?<img[^>]+src="([^"]+)"')
            if title:
                escaped_title = re.escape(title)
                candidates.append(rf'(?is)<a[^>]+title="{escaped_title}"[^>]*>.*?<img[^>]+src="([^"]+)"')
                candidates.append(rf'(?is)<img[^>]+alt="[^"]*{escaped_title}[^"]*"[^>]+src="([^"]+)"')
            for pattern in candidates:
                match = re.search(pattern, html_text)
                if match:
                    return match.group(1)

    return legacy_url


def download_bytes(url: str, timeout: int = 30, retries: int = 3) -> bytes:
    if not url:
        raise ValueError("empty url")

    opener = build_opener(ProxyHandler({}))
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers=HEADERS)
            with opener.open(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * attempt)
    assert last_error is not None
    raise last_error


def write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def download_pet_icons(data: list[dict], overwrite: bool = False) -> tuple[int, int, int]:
    PET_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0

    for pet in data:
        title = pet.get("wikitext_title") or pet.get("name") or "unnamed"
        url = pet.get("art_abs") or pet.get("art") or ""
        if not url:
            failed += 1
            print(f"[pet] skip missing url: {title}")
            continue

        filename = sanitize_filename(f"{title}.png")
        outpath = PET_DIR / filename
        if outpath.exists() and not overwrite:
            skipped += 1
            continue

        try:
            content = download_bytes(url)
            write_file(outpath, content)
            downloaded += 1
            print(f"[pet] {title} -> {outpath.name}")
        except Exception as exc:
            failed += 1
            print(f"[pet] failed {title}: {exc}")

    return downloaded, skipped, failed


def download_skill_icons(data: list[dict], overwrite: bool = False) -> tuple[int, int, int]:
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0
    seen: set[str] = set()

    for pet in data:
        skills = pet.get("skills") or []
        for skill in skills:
            name = skill.get("name") or skill.get("icon_title") or "unnamed"
            if name in seen:
                continue
            seen.add(name)

            url = resolve_skill_icon_url(skill)
            if not url:
                failed += 1
                print(f"[skill] skip missing url: {name}")
                continue

            outname = sanitize_filename(f"{name}.png")
            outpath = SKILL_DIR / outname
            if outpath.exists() and not overwrite:
                skipped += 1
                continue

            try:
                content = download_bytes(build_full_url(url))
                write_file(outpath, content)
                downloaded += 1
                print(f"[skill] {name} -> {outpath.name}")
            except Exception as exc:
                failed += 1
                print(f"[skill] failed {name}: {exc}")

    return downloaded, skipped, failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download pet and skill icons from pets_detailed.json")
    parser.add_argument("--input", default=str(DATA_PATH), help="Path to pets_detailed.json")
    parser.add_argument(
        "--target",
        choices=("all", "pets", "skills"),
        default="all",
        help="Which icon set to download",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    data = load_data(input_path)

    if args.target in ("all", "pets"):
        downloaded, skipped, failed = download_pet_icons(data, overwrite=args.overwrite)
        print(f"Pets: downloaded={downloaded}, skipped={skipped}, failed={failed}")

    if args.target in ("all", "skills"):
        downloaded, skipped, failed = download_skill_icons(data, overwrite=args.overwrite)
        print(f"Skills: downloaded={downloaded}, skipped={skipped}, failed={failed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())