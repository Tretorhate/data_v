import logging
import os
import time
from typing import Any

import psycopg2
from psycopg2.extras import DictCursor
from prometheus_client import Gauge, start_http_server


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "data_v"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "0412"),
}

COLLECTION_INTERVAL = int(os.getenv("METRIC_REFRESH_SECONDS", "20"))
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "8000"))


METRICS = {
    "player_count": Gauge(
        "valorant_player_count_total",
        "Total number of players tracked in player_stats",
    ),
    "avg_player_rating": Gauge(
        "valorant_average_player_rating",
        "Average overall player rating",
    ),
    "top_player_rating": Gauge(
        "valorant_top_player_rating",
        "Highest individual player rating",
    ),
    "total_kills": Gauge(
        "valorant_total_kills",
        "Total kills accumulated by all players",
    ),
    "total_deaths": Gauge(
        "valorant_total_deaths",
        "Total deaths accumulated by all players",
    ),
    "total_assists": Gauge(
        "valorant_total_assists",
        "Total assists accumulated by all players",
    ),
    "matches_total": Gauge(
        "valorant_matches_total",
        "Total number of matches recorded",
    ),
    "matches_completed": Gauge(
        "valorant_matches_completed_total",
        "Number of matches marked as completed",
    ),
    "avg_attack_win_pct": Gauge(
        "valorant_average_attack_win_percent",
        "Average attack win percentage across all maps",
    ),
    "avg_defense_win_pct": Gauge(
        "valorant_average_defense_win_percent",
        "Average defense win percentage across all maps",
    ),
    "agents_total": Gauge(
        "valorant_agents_total",
        "Total number of agents tracked",
    ),
    "avg_agent_utilization": Gauge(
        "valorant_average_agent_utilization",
        "Average total utilization score across all agents",
    ),
    "map_rounds_played": Gauge(
        "valorant_total_map_rounds_played",
        "Total times maps have been played",
    ),
}


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(cursor_factory=DictCursor, **DB_CONFIG)


def _fetch_single_value(cursor: psycopg2.extensions.cursor, query: str) -> Any:
    cursor.execute(query)
    result = cursor.fetchone()
    return result[0] if result else None


def collect_metrics() -> None:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            values = {}

            values["player_count"] = _fetch_single_value(
                cursor, "SELECT COUNT(*) FROM player_stats"
            )
            values["avg_player_rating"] = _fetch_single_value(
                cursor,
                "SELECT COALESCE(AVG(rating), 0) FROM player_stats WHERE rating IS NOT NULL",
            )
            values["top_player_rating"] = _fetch_single_value(
                cursor,
                "SELECT COALESCE(MAX(rating), 0) FROM player_stats WHERE rating IS NOT NULL",
            )
            values["total_kills"] = _fetch_single_value(
                cursor, "SELECT COALESCE(SUM(kills), 0) FROM player_stats"
            )
            values["total_deaths"] = _fetch_single_value(
                cursor, "SELECT COALESCE(SUM(deaths), 0) FROM player_stats"
            )
            values["total_assists"] = _fetch_single_value(
                cursor, "SELECT COALESCE(SUM(assists), 0) FROM player_stats"
            )
            values["matches_total"] = _fetch_single_value(
                cursor, "SELECT COUNT(*) FROM matches"
            )
            values["matches_completed"] = _fetch_single_value(
                cursor,
                "SELECT COUNT(*) FROM matches WHERE status = 'Completed'",
            )
            values["avg_attack_win_pct"] = _fetch_single_value(
                cursor,
                "SELECT COALESCE(AVG(attack_win_percent), 0) FROM maps_stats",
            )
            values["avg_defense_win_pct"] = _fetch_single_value(
                cursor,
                "SELECT COALESCE(AVG(defense_win_percent), 0) FROM maps_stats",
            )
            values["agents_total"] = _fetch_single_value(
                cursor, "SELECT COUNT(*) FROM agents_stats"
            )
            values["avg_agent_utilization"] = _fetch_single_value(
                cursor,
                "SELECT COALESCE(AVG(total_utilization), 0) FROM agents_stats",
            )
            values["map_rounds_played"] = _fetch_single_value(
                cursor, "SELECT COALESCE(SUM(times_played), 0) FROM maps_stats"
            )

        for name, gauge in METRICS.items():
            value = values.get(name)
            if value is None:
                # Skip updating metric if query returned nothing
                continue
            gauge.set(float(value))

        logger.debug("Metrics updated: %s", values)

    except Exception as exc:
        logger.exception("Error collecting metrics: %s", exc)
    finally:
        if conn is not None:
            conn.close()


def main() -> None:
    logger.info(
        "Starting Valorant custom exporter on port %s (interval %ss)",
        EXPORTER_PORT,
        COLLECTION_INTERVAL,
    )
    start_http_server(EXPORTER_PORT)

    while True:
        collect_metrics()
        time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Exporter interrupted, shutting down")

