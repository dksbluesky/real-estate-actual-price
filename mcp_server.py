from mcp.server.fastmcp import FastMCP

from app.config import database_path
from app.db import connect
from app.repository import data_status, list_areas, market_stats, search_transactions


mcp = FastMCP(
    "real-estate-actual-price",
    instructions=(
        "Use these read-only tools for Taiwan official actual-price transaction searches. "
        "Always state the data coverage date and treat results as reference data, not an appraisal."
    ),
    host="127.0.0.1",
    port=8001,
)


@mcp.tool(name="search_transactions", annotations={"readOnlyHint": True, "openWorldHint": False, "destructiveHint": False})
def search_transactions_tool(query: str = "", city: str = "", district: str = "",
                             years: int = 3, limit: int = 50) -> dict:
    """Search transactions by address, district, or address/notes text such as a building name."""
    with connect(database_path()) as connection:
        records = search_transactions(connection, query, city, district, years, limit)
    return {"count": len(records), "transactions": records}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False, "destructiveHint": False})
def get_market_stats(query: str = "", city: str = "", district: str = "", years: int = 1) -> dict:
    """Calculate transaction count and unit-price statistics for the latest 1 or 3 years of loaded data."""
    if years not in (1, 3):
        raise ValueError("years must be 1 or 3")
    with connect(database_path()) as connection:
        return market_stats(connection, query, city, district, years)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False, "destructiveHint": False})
def list_available_areas() -> dict:
    """List loaded Taiwan cities and districts with their transaction counts."""
    with connect(database_path()) as connection:
        return {"areas": list_areas(connection)}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False, "destructiveHint": False})
def get_data_status() -> dict:
    """Return local data coverage, row count, and official import history."""
    with connect(database_path()) as connection:
        return data_status(connection)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
