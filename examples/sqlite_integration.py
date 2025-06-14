"""Example: Integrate netvelocimeter with SQLite for result storage.

This script demonstrates running a test and storing results in a local SQLite database
using only the Python standard library. The schema is minimal and can be extended as needed.
"""

from datetime import datetime, timezone
import os
import random
import sqlite3

from netvelocimeter import DataRateMbps, MeasurementResult, NetVelocimeter

# convert DB_PATH to canonical path
DB_PATH = os.path.abspath("netvelocimeter_results.sqlite3")

# Define the schema for storing results
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    download_speed REAL,
    upload_speed REAL,
    ping_latency_ms REAL,
    packet_loss REAL,
    persist_url TEXT
);
"""

INSERT_RESULT_SQL = """
INSERT INTO measurements (
    provider, timestamp, download_speed, upload_speed, ping_latency_ms, packet_loss, persist_url
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def store_result(conn: sqlite3.Connection, provider: str, result: MeasurementResult) -> None:
    """Store a single measurement result in the database using dataclass attributes."""
    conn.execute(
        INSERT_RESULT_SQL,
        (
            provider,
            datetime.now(timezone.utc).isoformat(),
            result.download_speed,
            result.upload_speed,
            result.ping_latency.total_seconds() * 1000 if result.ping_latency else None,
            result.packet_loss,
            result.persist_url,
        ),
    )
    conn.commit()


if __name__ == "__main__":
    # generate a pseudo-random float between 100.0 and 1000.0 for download speed
    random_download_speed = DataRateMbps(random.uniform(100.0, 1000.0))

    # Create a NetVelocimeter instance using static test provider with random download speed
    nv = NetVelocimeter(provider="static", download_speed=random_download_speed)

    # ONLY FOR TESTING AND EXAMPLE PURPOSES!
    # Accept all legal terms for automation
    nv.accept_terms(nv.legal_terms())

    # Perform the measurement
    result = nv.measure()

    # Connect to SQLite and ensure table exists
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)

    # Store the measurement result
    store_result(conn, nv.provider_name, result)

    # print the stored results and close the connection
    print(f"Results stored in {DB_PATH}:")
    for row in conn.execute("SELECT * FROM measurements ORDER BY id DESC"):
        print(row)
    conn.close()
