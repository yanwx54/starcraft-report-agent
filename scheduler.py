from __future__ import annotations

import time
from datetime import datetime

from agent import StarCraftReportAgent


def run_daily_loop(hour: int = 8, minute: int = 0) -> None:
    """Small dependency-free scheduler for Docker/Windows task usage."""
    last_run_date = ""
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.hour == hour and now.minute == minute and last_run_date != today:
            StarCraftReportAgent().run()
            last_run_date = today
        time.sleep(30)


if __name__ == "__main__":
    run_daily_loop()
