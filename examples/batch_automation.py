"""Example: Batch testing/automation with netvelocimeter.

This script demonstrates running speed tests for the static provider on a schedule and
logging results to a file. It uses the standard logging module and can be adapted
for any provider or scheduler (e.g. cron).
"""

from dataclasses import asdict
from datetime import datetime
import logging
import time

from netvelocimeter import NetVelocimeter

# Configure logging to file
logging.basicConfig(
    filename="batch_speedtest.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Interval between tests in seconds (e.g., 3600 for hourly)
INTERVAL_SECONDS = 3600


def run_batch_tests() -> None:
    """Run speed tests for static provider and log results."""
    logger.info("Starting batch speed tests at %s", datetime.now().isoformat())

    # use the static provider for testing purposes
    try:
        # Create a NetVelocimeter instance for the static provider
        nv = NetVelocimeter(provider="static")

        # ONLY FOR TESTING AND EXAMPLE PURPOSES!
        # Accept all legal terms for automation
        nv.accept_terms(nv.legal_terms())

        # Perform the speed test
        result = nv.measure()

        # Log the result
        result_dict = asdict(result)
        logger.info(f"Provider: {nv.provider_name} | Result: {result_dict}")

        # extract and print the download speed
        print(
            f"[{datetime.now().isoformat()}] Success {nv.provider_name}: download speed {result.download_speed}"
        )
    except Exception as ex:
        # Log the error
        logger.error(f"Provider: {nv.provider_name} | Error: {ex}")

        # Print the error message
        print(f"[{datetime.now().isoformat()}] Error {nv.provider_name}: {ex}")


def main() -> None:
    """Main function to run batch tests on a schedule."""
    # Run once at startup, then every INTERVAL_SECONDS
    while True:
        run_batch_tests()
        print(f"Sleeping for {INTERVAL_SECONDS} seconds...")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
