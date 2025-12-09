#!/usr/bin/env python3
"""
CivicBand Umami Analytics Data Retrieval Script

This script retrieves event data from Umami Analytics and stores it in SQLite
for detailed analysis. Designed to run as a cron job for periodic data collection.

Usage:
    python retrieve_umami_analytics.py --days 7 --output ./analytics/
    python retrieve_umami_analytics.py --days 1 --events  # Daily cron job
    python retrieve_umami_analytics.py --days 30 --events --summary  # Monthly report

Environment Variables Required:
    UMAMI_URL - Umami instance URL (default: https://analytics.civic.band)
    UMAMI_USERNAME - Username for API authentication
    UMAMI_PASSWORD - Password for API authentication
    UMAMI_WEBSITE_ID - Website ID to query
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_stat_value(stats: Dict, key: str) -> int:
    """
    Extract a stat value handling both old and new Umami API formats.

    Old format: {"pageviews": {"value": 1000}}
    New format: {"pageviews": 1000}

    Args:
        stats: Dictionary of stats from Umami API
        key: The stat key to extract

    Returns:
        The integer value, or 0 if not found/invalid
    """
    value = stats.get(key, 0)
    if isinstance(value, dict):
        return value.get("value", 0)
    return value if isinstance(value, int) else 0


class UmamiClient:
    """Client for Umami Analytics API."""

    def __init__(self, url: str, username: str, password: str, website_id: str):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.website_id = website_id
        self.token = None

    def authenticate(self) -> bool:
        """Authenticate and get access token."""
        try:
            logger.info("Authenticating with Umami...")
            response = requests.post(
                f"{self.url}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            self.token = data.get("token")

            if not self.token:
                logger.error("No token in authentication response")
                return False

            logger.info("Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def get_website_stats(
        self, start_date: datetime, end_date: datetime
    ) -> Optional[Dict]:
        """Get website statistics for date range."""
        try:
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)

            response = requests.get(
                f"{self.url}/api/websites/{self.website_id}/stats",
                headers=self._get_headers(),
                params={"startAt": start_ms, "endAt": end_ms},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get website stats: {e}")
            return None

    def get_metrics(
        self, start_date: datetime, end_date: datetime, metric_type: str = "url"
    ) -> Optional[List[Dict]]:
        """Get metrics data (URLs, events, etc.)."""
        try:
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)

            response = requests.get(
                f"{self.url}/api/websites/{self.website_id}/metrics",
                headers=self._get_headers(),
                params={"startAt": start_ms, "endAt": end_ms, "type": metric_type},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get metrics: {e}")
            return None

    def get_events(
        self, start_date: datetime, end_date: datetime
    ) -> Optional[List[Dict]]:
        """Get all events for date range."""
        try:
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)

            response = requests.get(
                f"{self.url}/api/websites/{self.website_id}/events",
                headers=self._get_headers(),
                params={"startAt": start_ms, "endAt": end_ms},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get events: {e}")
            return None

    def get_active_users(self) -> int:
        """Get currently active users count."""
        try:
            response = requests.get(
                f"{self.url}/api/websites/{self.website_id}/active",
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("x", 0)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get active users: {e}")
            return 0


class AnalyticsDatabase:
    """SQLite database for storing analytics data.

    Supports context manager protocol for safe resource cleanup:

        with AnalyticsDatabase(db_path) as db:
            db.insert_website_stats(...)
    """

    # Valid table names for metrics to prevent SQL injection
    VALID_METRIC_TABLES = {"url_metrics", "event_metrics"}

    def __init__(self, db_path: Union[str, Path], retrieved_at: Optional[str] = None):
        """
        Initialize the analytics database.

        Args:
            db_path: Path to the SQLite database file
            retrieved_at: Optional timestamp for all inserts in this session.
                         If not provided, uses current time at init.
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.conn = None
        self.retrieved_at = retrieved_at or datetime.now().isoformat()
        self._init_database()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False  # Don't suppress exceptions

    def _init_database(self):
        """Initialize database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))

        # Create tables with unique constraints to prevent duplicates
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS website_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrieved_at TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                pageviews INTEGER,
                unique_visitors INTEGER,
                visits INTEGER,
                bounces INTEGER,
                total_time INTEGER,
                stats_json TEXT,
                UNIQUE(start_date, end_date)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrieved_at TEXT NOT NULL,
                event_name TEXT,
                event_url TEXT,
                event_hostname TEXT,
                event_data TEXT,
                event_timestamp INTEGER
            );

            CREATE TABLE IF NOT EXISTS url_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrieved_at TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                url TEXT,
                visits INTEGER,
                metric_data TEXT,
                UNIQUE(start_date, end_date, url)
            );

            CREATE TABLE IF NOT EXISTS event_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrieved_at TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                event_name TEXT,
                event_count INTEGER,
                metric_data TEXT,
                UNIQUE(start_date, end_date, event_name)
            );

            CREATE INDEX IF NOT EXISTS idx_events_name ON events(event_name);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(event_timestamp);
            CREATE INDEX IF NOT EXISTS idx_stats_dates ON website_stats(start_date, end_date);
        """)
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def insert_website_stats(
        self, start_date: datetime, end_date: datetime, stats: Dict
    ):
        """Insert website statistics.

        Uses INSERT OR REPLACE to update existing records for the same date range.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO website_stats (
                retrieved_at, start_date, end_date,
                pageviews, unique_visitors, visits, bounces, total_time,
                stats_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.retrieved_at,
                start_date.isoformat(),
                end_date.isoformat(),
                get_stat_value(stats, "pageviews"),
                get_stat_value(stats, "visitors"),
                get_stat_value(stats, "visits"),
                get_stat_value(stats, "bounces"),
                get_stat_value(stats, "totaltime"),
                json.dumps(stats),
            ),
        )
        self.conn.commit()

    def insert_events(self, events: List[Dict]):
        """Insert events data."""
        for event in events:
            self.conn.execute(
                """
                INSERT INTO events (
                    retrieved_at, event_name, event_url, event_hostname,
                    event_data, event_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    self.retrieved_at,
                    event.get("name"),
                    event.get("url"),
                    event.get("hostname"),
                    json.dumps(event.get("data", {})),
                    event.get("timestamp"),
                ),
            )
        self.conn.commit()

    def insert_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        metrics: List[Dict],
        metric_type: str,
    ):
        """Insert metrics data.

        Uses INSERT OR REPLACE to update existing records for the same date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            metrics: List of metric dictionaries from Umami API
            metric_type: Either "url" or "event"

        Raises:
            ValueError: If metric_type is not "url" or "event"
        """
        # Validate metric_type to prevent SQL injection
        if metric_type not in ("url", "event"):
            raise ValueError(
                f"Invalid metric_type: {metric_type}. Must be 'url' or 'event'"
            )

        for metric in metrics:
            if metric_type == "url":
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO url_metrics (
                        retrieved_at, start_date, end_date,
                        url, visits, metric_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.retrieved_at,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        metric.get("x"),
                        metric.get("y"),
                        json.dumps(metric),
                    ),
                )
            else:  # event metrics
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO event_metrics (
                        retrieved_at, start_date, end_date,
                        event_name, event_count, metric_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.retrieved_at,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        metric.get("x"),
                        metric.get("y"),
                        json.dumps(metric),
                    ),
                )
        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def generate_summary_report(
    stats: Dict, events: List[Dict], start_date: datetime, end_date: datetime
) -> Dict:
    """Generate summary report from analytics data.

    Args:
        stats: Website statistics from Umami API (handles both old and new format)
        events: List of events from Umami API
        start_date: Start of the reporting period
        end_date: End of the reporting period

    Returns:
        Dictionary containing the summary report
    """
    event_counts: Dict[str, int] = {}
    subdomain_counts: Dict[str, int] = {}

    for event in events:
        event_name = event.get("name", "unknown")
        event_counts[event_name] = event_counts.get(event_name, 0) + 1

        # Extract subdomain from event data
        event_data = event.get("data", {})
        if isinstance(event_data, dict):
            subdomain = event_data.get("subdomain")
            if subdomain:
                subdomain_counts[subdomain] = subdomain_counts.get(subdomain, 0) + 1

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": (end_date - start_date).days,
        },
        "overview": {
            "pageviews": get_stat_value(stats, "pageviews"),
            "unique_visitors": get_stat_value(stats, "visitors"),
            "visits": get_stat_value(stats, "visits"),
            "bounce_rate": get_stat_value(stats, "bounces"),
            "total_time_seconds": get_stat_value(stats, "totaltime"),
        },
        "events": {
            "total_events": len(events),
            "event_breakdown": event_counts,
            "top_events": sorted(
                event_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        },
        "municipalities": {
            "total_municipalities": len(subdomain_counts),
            "municipality_breakdown": subdomain_counts,
            "top_municipalities": sorted(
                subdomain_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        },
        "generated_at": datetime.now().isoformat(),
    }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Retrieve Umami analytics data for CivicBand"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of data to retrieve (default: 7)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./analytics"),
        help="Output directory for analytics data (default: ./analytics)",
    )
    parser.add_argument(
        "--events", action="store_true", help="Retrieve detailed event data"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate and save summary report as JSON",
    )

    args = parser.parse_args()

    # Get configuration from environment
    umami_url = os.getenv("UMAMI_URL", "https://analytics.civic.band")
    umami_username = os.getenv("UMAMI_USERNAME")
    umami_password = os.getenv("UMAMI_PASSWORD")
    umami_website_id = os.getenv("UMAMI_WEBSITE_ID")

    if not all([umami_username, umami_password, umami_website_id]):
        logger.error("Missing required environment variables")
        logger.error("Required: UMAMI_USERNAME, UMAMI_PASSWORD, UMAMI_WEBSITE_ID")
        sys.exit(1)

    # Initialize client
    client = UmamiClient(umami_url, umami_username, umami_password, umami_website_id)

    # Authenticate
    if not client.authenticate():
        logger.error("Failed to authenticate with Umami")
        sys.exit(1)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    logger.info(f"Retrieving data from {start_date.date()} to {end_date.date()}")

    # Initialize database with context manager for safe cleanup
    db_path = args.output / "umami_events.db"

    with AnalyticsDatabase(db_path) as db:
        # Get website stats
        logger.info("Retrieving website statistics...")
        stats = client.get_website_stats(start_date, end_date)

        if stats:
            db.insert_website_stats(start_date, end_date, stats)
            pageviews = get_stat_value(stats, "pageviews")
            visitors = get_stat_value(stats, "visitors")
            logger.info(f"Stats: {pageviews} pageviews, {visitors} unique visitors")
        else:
            logger.warning("No stats data retrieved")
            stats = {}

        # Get events if requested
        events = []
        if args.events:
            logger.info("Retrieving event data...")
            events = client.get_events(start_date, end_date) or []

            if events:
                db.insert_events(events)
                logger.info(f"Retrieved {len(events)} events")
            else:
                logger.warning("No events data retrieved")

            # Get event metrics
            logger.info("Retrieving event metrics...")
            event_metrics = client.get_metrics(start_date, end_date, "event") or []
            if event_metrics:
                db.insert_metrics(start_date, end_date, event_metrics, "event")
                logger.info(f"Retrieved metrics for {len(event_metrics)} event types")

        # Get URL metrics
        logger.info("Retrieving URL metrics...")
        url_metrics = client.get_metrics(start_date, end_date, "url") or []
        if url_metrics:
            db.insert_metrics(start_date, end_date, url_metrics, "url")
            logger.info(f"Retrieved metrics for {len(url_metrics)} URLs")

        # Generate summary if requested
        if args.summary:
            logger.info("Generating summary report...")
            summary = generate_summary_report(stats, events, start_date, end_date)

            summary_path = (
                args.output / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2, default=str)

            logger.info(f"Summary saved to {summary_path}")

            # Print summary to console
            print("\n=== Analytics Summary ===")
            print(
                f"Period: {summary['period']['start']} to {summary['period']['end']} "
                f"({summary['period']['days']} days)"
            )
            print("\nOverview:")
            print(f"  Pageviews: {summary['overview']['pageviews']:,}")
            print(f"  Unique Visitors: {summary['overview']['unique_visitors']:,}")
            print(f"  Total Visits: {summary['overview']['visits']:,}")

            if summary["events"]["total_events"] > 0:
                print("\nEvents:")
                print(f"  Total Events: {summary['events']['total_events']:,}")
                print("  Top Event Types:")
                for event_name, count in summary["events"]["top_events"]:
                    print(f"    - {event_name}: {count:,}")

            if summary["municipalities"]["total_municipalities"] > 0:
                print("\nMunicipalities:")
                print(
                    f"  Total Municipalities: {summary['municipalities']['total_municipalities']}"
                )
                print("  Top Municipalities:")
                for subdomain, count in summary["municipalities"]["top_municipalities"]:
                    print(f"    - {subdomain}: {count:,} events")

    logger.info("Analytics retrieval complete")
    logger.info(f"Data stored in {db_path}")


if __name__ == "__main__":
    main()
