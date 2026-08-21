from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import pytest

from app.db import connect
from app.importer import import_zip, roc_date
from app.repository import data_status, market_stats, search_transactions
from app.webapp import create_app
from scripts.sync_data import https_context


HEADERS = ["鄉鎮市區", "交易標的", "土地位置建物門牌", "交易年月日", "移轉層次", "總樓層數", "建物型態",
           "建築完成年月", "建物移轉總面積平方公尺", "建物現況格局-房", "建物現況格局-廳",
           "建物現況格局-衛", "總價元", "單價元平方公尺", "車位類別", "車位總價元", "備註", "編號"]
ROWS = [
    ["大安區", "房地(土地+建物)", "臺北市大安區信義路100號國安大廈", "1140105", "五層", "十二層", "住宅大樓",
     "0990101", "99.17355", "3", "2", "2", "30000000", "1000000", "坡道平面", "2000000", "含車位", "TEST001"],
    ["大安區", "房地(土地+建物)", "臺北市大安區信義路120號", "1130105", "八層", "十二層", "住宅大樓",
     "0980101", "66.1157", "2", "1", "1", "18000000", "900000", "", "0", "", "TEST002"],
    ["大安區", "房地(土地+建物)", "臺北市大安區未來路1號", "1200105", "一層", "一層", "透天厝",
     "0990101", "50", "1", "1", "1", "10000000", "200000", "", "0", "異常未來日期", "TEST003"],
    ["大安區", "房地(土地+建物)", "臺北市大安區歷史路1號", "0010105", "一層", "一層", "透天厝",
     "0010101", "50", "1", "1", "1", "10000000", "200000", "", "0", "制度前日期", "TEST004"],
]


@pytest.fixture()
def db_path(tmp_path: Path):
    csv_path = tmp_path / "a_lvr_land_a.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(ROWS)
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(csv_path, csv_path.name)
    path = tmp_path / "test.db"
    with connect(path) as connection:
        assert import_zip(connection, zip_path, "fixture", "local://fixture") == 2
    return path


def test_roc_date_conversion():
    assert roc_date("1140105") == "2025-01-05"
    assert roc_date("") is None


def test_https_context_keeps_certificate_checks():
    context = https_context()
    assert context.check_hostname is True
    assert context.verify_mode.name == "CERT_REQUIRED"


def test_search_by_building_text(db_path):
    with connect(db_path) as connection:
        result = search_transactions(connection, query="國安大廈")
    assert len(result) == 1
    assert result[0]["area_ping"] == 30
    assert result[0]["unit_price_per_ping"] == 3305785


def test_market_stats(db_path):
    with connect(db_path) as connection:
        stats = market_stats(connection, city="臺北市", district="大安區", years=3)
    assert stats["count"] == 2
    assert stats["median_unit_price_per_ping"] == 3140496
    assert len(stats["trend"]) == 2


def test_duplicate_import_is_idempotent(db_path):
    with connect(db_path) as connection:
        assert data_status(connection)["transaction_count"] == 2


def test_web_api(db_path):
    client = create_app(db_path).test_client()
    assert client.get("/health").json == {"status": "ok"}
    response = client.get("/api/search?q=信義路")
    assert response.status_code == 200
    assert response.json["count"] == 2
