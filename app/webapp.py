from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from .config import database_path
from .db import connect
from .repository import data_status, list_areas, market_stats, search_transactions


def create_app(db_path=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    path = db_path or database_path()

    def get_connection():
        return connect(path)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/search")
    def api_search():
        with get_connection() as connection:
            result = search_transactions(
                connection, request.args.get("q", ""), request.args.get("city", ""),
                request.args.get("district", ""), request.args.get("years", 3, type=int),
                request.args.get("limit", 100, type=int),
            )
        return jsonify({"transactions": result, "count": len(result)})

    @app.get("/api/stats")
    def api_stats():
        with get_connection() as connection:
            result = market_stats(connection, request.args.get("q", ""), request.args.get("city", ""),
                                  request.args.get("district", ""), request.args.get("years", 1, type=int))
        return jsonify(result)

    @app.get("/api/areas")
    def api_areas():
        with get_connection() as connection:
            return jsonify({"areas": list_areas(connection)})

    @app.get("/api/status")
    def api_status():
        with get_connection() as connection:
            return jsonify(data_status(connection))

    return app

