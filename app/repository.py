from __future__ import annotations

import calendar
import statistics
from datetime import date, datetime

from .importer import normalize_text


PING_PER_SQM = 1 / 3.305785


def _subtract_years(value: date, years: int) -> date:
    day = min(value.day, calendar.monthrange(value.year - years, value.month)[1])
    return value.replace(year=value.year - years, day=day)


def _filters(query: str = "", city: str = "", district: str = ""):
    clauses, params = [], []
    if city:
        clauses.append("city = ?")
        params.append(city)
    if district:
        clauses.append("district = ?")
        params.append(district)
    if query:
        token = f"%{normalize_text(query)}%"
        clauses.append("(address_normalized LIKE ? OR replace(lower(notes), ' ', '') LIKE ?)")
        params.extend((token, token))
    return (" AND ".join(clauses) if clauses else "1=1"), params


def _serialize(row):
    record = dict(row)
    sqm = record.pop("unit_price_sqm")
    area_sqm = record.pop("building_area_sqm")
    record["unit_price_per_ping"] = round(sqm / PING_PER_SQM) if sqm else None
    record["area_ping"] = round(area_sqm * PING_PER_SQM, 2) if area_sqm else None
    completion = record.get("completion_date")
    record["building_age"] = max(0, date.today().year - int(completion[:4])) if completion else None
    return record


def search_transactions(connection, query="", city="", district="", years=3, limit=100):
    where, params = _filters(query, city, district)
    latest = connection.execute("SELECT max(transaction_date) FROM transactions").fetchone()[0]
    if latest and years:
        start = _subtract_years(datetime.strptime(latest, "%Y-%m-%d").date(), years).isoformat()
        where += " AND transaction_date >= ?"
        params.append(start)
    rows = connection.execute(
        f"SELECT * FROM transactions WHERE {where} ORDER BY transaction_date DESC LIMIT ?",
        (*params, min(max(int(limit), 1), 500)),
    ).fetchall()
    return [_serialize(row) for row in rows]


def market_stats(connection, query="", city="", district="", years=1):
    where, params = _filters(query, city, district)
    latest = connection.execute("SELECT max(transaction_date) FROM transactions").fetchone()[0]
    if not latest:
        return {"years": years, "count": 0, "latest_data_date": None, "trend": []}
    end = datetime.strptime(latest, "%Y-%m-%d").date()
    start = _subtract_years(end, years)
    rows = connection.execute(
        f"SELECT transaction_date, unit_price_sqm FROM transactions "
        f"WHERE {where} AND transaction_date >= ? AND unit_price_sqm > 0 ORDER BY transaction_date",
        (*params, start.isoformat()),
    ).fetchall()
    values = [row["unit_price_sqm"] / PING_PER_SQM for row in rows]
    monthly = {}
    for row in rows:
        monthly.setdefault(row["transaction_date"][:7], []).append(row["unit_price_sqm"] / PING_PER_SQM)
    trend = [{"month": month, "median_unit_price_per_ping": round(statistics.median(prices)), "count": len(prices)}
             for month, prices in monthly.items()]
    return {
        "years": years,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "latest_data_date": latest,
        "count": len(values),
        "median_unit_price_per_ping": round(statistics.median(values)) if values else None,
        "average_unit_price_per_ping": round(statistics.fmean(values)) if values else None,
        "highest_unit_price_per_ping": round(max(values)) if values else None,
        "lowest_unit_price_per_ping": round(min(values)) if values else None,
        "trend": trend,
    }


def list_areas(connection):
    rows = connection.execute(
        "SELECT city, district, count(*) AS count FROM transactions GROUP BY city, district ORDER BY city, district"
    ).fetchall()
    cities = {}
    for row in rows:
        cities.setdefault(row["city"], []).append({"district": row["district"], "count": row["count"]})
    return [{"city": city, "districts": districts} for city, districts in cities.items()]


def data_status(connection):
    summary = connection.execute(
        "SELECT count(*) AS count, min(transaction_date) AS earliest, max(transaction_date) AS latest FROM transactions"
    ).fetchone()
    imports = [dict(row) for row in connection.execute(
        "SELECT source_period, source_url, imported_at, row_count FROM imports ORDER BY imported_at DESC"
    ).fetchall()]
    return {"transaction_count": summary["count"], "earliest_date": summary["earliest"],
            "latest_date": summary["latest"], "imports": imports}

