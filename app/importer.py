from __future__ import annotations

import csv
import hashlib
import io
import re
import sqlite3
import unicodedata
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path


CITY_CODES = {
    "a": "臺北市", "b": "臺中市", "c": "基隆市", "d": "臺南市",
    "e": "高雄市", "f": "新北市", "g": "宜蘭縣", "h": "桃園市",
    "i": "嘉義市", "j": "新竹縣", "k": "苗栗縣", "m": "南投縣",
    "n": "彰化縣", "o": "新竹市", "p": "雲林縣", "q": "嘉義縣",
    "t": "屏東縣", "u": "花蓮縣", "v": "臺東縣", "w": "金門縣",
    "x": "澎湖縣", "z": "連江縣",
}

UPSERT = """
INSERT INTO transactions (
    record_id, city, district, address, address_normalized, transaction_date,
    transaction_target, total_price, unit_price_sqm, building_area_sqm, floor,
    total_floors, building_type, completion_date, rooms, halls, bathrooms,
    parking_type, parking_price, notes, source_period, imported_at
) VALUES (
    :record_id, :city, :district, :address, :address_normalized, :transaction_date,
    :transaction_target, :total_price, :unit_price_sqm, :building_area_sqm, :floor,
    :total_floors, :building_type, :completion_date, :rooms, :halls, :bathrooms,
    :parking_type, :parking_price, :notes, :source_period, :imported_at
)
ON CONFLICT(record_id) DO UPDATE SET
    city=excluded.city, district=excluded.district, address=excluded.address,
    address_normalized=excluded.address_normalized, transaction_date=excluded.transaction_date,
    transaction_target=excluded.transaction_target, total_price=excluded.total_price,
    unit_price_sqm=excluded.unit_price_sqm, building_area_sqm=excluded.building_area_sqm,
    floor=excluded.floor, total_floors=excluded.total_floors,
    building_type=excluded.building_type, completion_date=excluded.completion_date,
    rooms=excluded.rooms, halls=excluded.halls, bathrooms=excluded.bathrooms,
    parking_type=excluded.parking_type, parking_price=excluded.parking_price,
    notes=excluded.notes, source_period=excluded.source_period, imported_at=excluded.imported_at
"""


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).lower()


def _number(value: str | None, cast):
    if value is None or not value.strip():
        return None
    try:
        return cast(float(value.replace(",", "")))
    except ValueError:
        return None


def roc_date(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 5:
        return None
    digits = digits.zfill(7)
    year = int(digits[:-4]) + 1911
    month, day = int(digits[-4:-2]), int(digits[-2:])
    if not 1 <= month <= 12:
        return None
    if day == 0:
        day = 1
    try:
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return None


def _row_to_record(row: dict[str, str], city: str, source_period: str, imported_at: str):
    transaction_date = roc_date(row.get("交易年月日"))
    address = (row.get("土地位置建物門牌") or row.get("土地區段位置建物區段門牌") or "").strip()
    district = (row.get("鄉鎮市區") or "").strip()
    if not transaction_date or not district or not address:
        return None
    parsed_transaction_date = date.fromisoformat(transaction_date)
    if parsed_transaction_date < date(2012, 8, 1) or parsed_transaction_date > date.today():
        return None
    official_id = (row.get("編號") or "").strip()
    if not official_id:
        raw_key = "|".join((city, district, address, transaction_date, row.get("總價元", "")))
        official_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]
    return {
        "record_id": official_id,
        "city": city,
        "district": district,
        "address": address,
        "address_normalized": normalize_text(address),
        "transaction_date": transaction_date,
        "transaction_target": (row.get("交易標的") or "").strip(),
        "total_price": _number(row.get("總價元"), int),
        "unit_price_sqm": _number(row.get("單價元平方公尺"), float),
        "building_area_sqm": _number(row.get("建物移轉總面積平方公尺"), float),
        "floor": (row.get("移轉層次") or "").strip(),
        "total_floors": (row.get("總樓層數") or "").strip(),
        "building_type": (row.get("建物型態") or "").strip(),
        "completion_date": roc_date(row.get("建築完成年月")),
        "rooms": _number(row.get("建物現況格局-房"), int),
        "halls": _number(row.get("建物現況格局-廳"), int),
        "bathrooms": _number(row.get("建物現況格局-衛"), int),
        "parking_type": (row.get("車位類別") or "").strip(),
        "parking_price": _number(row.get("車位總價元"), int),
        "notes": (row.get("備註") or "").strip(),
        "source_period": source_period,
        "imported_at": imported_at,
    }


def import_zip(connection: sqlite3.Connection, zip_path: Path, source_period: str,
               source_url: str, cities: set[str] | None = None) -> int:
    imported_at = datetime.now(UTC).isoformat()
    total = 0
    with zipfile.ZipFile(zip_path) as archive:
        entries = [entry for entry in archive.infolist()
                   if re.fullmatch(r"[a-z]_lvr_land_a\.csv", Path(entry.filename).name.lower())]
        for entry in entries:
            code = Path(entry.filename).name[0].lower()
            city = CITY_CODES.get(code)
            if not city or (cities and city not in cities):
                continue
            with archive.open(entry) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text)
                records = []
                for row in reader:
                    record = _row_to_record(row, city, source_period, imported_at)
                    if record:
                        records.append(record)
                connection.executemany(UPSERT, records)
                total += len(records)
    connection.execute(
        "INSERT INTO imports(source_period, source_url, imported_at, row_count) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(source_period) DO UPDATE SET source_url=excluded.source_url, "
        "imported_at=excluded.imported_at, row_count=excluded.row_count",
        (source_period, source_url, imported_at, total),
    )
    connection.execute(
        "DELETE FROM transactions WHERE transaction_date < '2012-08-01' OR transaction_date > ?",
        (date.today().isoformat(),),
    )
    connection.commit()
    return total
