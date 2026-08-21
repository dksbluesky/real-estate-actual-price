from __future__ import annotations

import argparse
import ssl
import tempfile
import urllib.request
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import database_path  # noqa: E402
from app.db import connect  # noqa: E402
from app.importer import import_zip  # noqa: E402


CURRENT_URL = "https://plvr.land.moi.gov.tw/opendata/lvr_landAcsv.zip"
SEASON_URL = "https://plvr.land.moi.gov.tw/DownloadSeason?season={season}&type=zip&fileName=lvr_landcsv.zip"


def https_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    # Python 3.13+ enables OpenSSL strict mode. The official historical-download
    # chain currently lacks an SKI extension, so relax only strict RFC checks;
    # CA validation and hostname verification remain enabled.
    strict_flag = getattr(ssl, "VERIFY_X509_STRICT", 0)
    if strict_flag:
        context.verify_flags &= ~strict_flag
    return context


def download_and_import(url: str, period: str, cities: set[str] | None) -> int:
    print(f"下載 {period} 官方資料…")
    with tempfile.TemporaryDirectory(prefix="real-price-") as temp_dir:
        target = Path(temp_dir) / f"{period}.zip"
        request = urllib.request.Request(url, headers={"User-Agent": "RealEstateActualPrice/0.1"})
        with urllib.request.urlopen(request, timeout=180, context=https_context()) as response, target.open("wb") as output:
            output.write(response.read())
        with connect(database_path()) as connection:
            count = import_zip(connection, target, period, url, cities)
    print(f"{period}: 已匯入/更新 {count:,} 筆")
    return count


def main():
    parser = argparse.ArgumentParser(description="同步內政部官方實價登錄買賣資料")
    parser.add_argument("--current", action="store_true", help="匯入當期資料")
    parser.add_argument("--season", action="append", default=[], help="歷史季度，例如 114S4；可重複")
    parser.add_argument("--city", action="append", default=[], help="只匯入指定縣市；可重複")
    args = parser.parse_args()
    if not args.current and not args.season:
        parser.error("請指定 --current 或至少一個 --season")
    cities = set(args.city) or None
    if args.current:
        download_and_import(CURRENT_URL, "current", cities)
    for season in args.season:
        if not season[:-2].isdigit() or season[-2:-1].upper() != "S" or season[-1:] not in "1234":
            parser.error(f"季度格式錯誤: {season}")
        normalized = season.upper()
        download_and_import(SEASON_URL.format(season=normalized), normalized, cities)


if __name__ == "__main__":
    main()
