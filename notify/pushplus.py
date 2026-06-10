from __future__ import annotations

from datetime import datetime

import requests

from config.settings import settings
from models import BattleReport


class PushPlusClient:
    endpoint = "https://www.pushplus.plus/send"

    @property
    def enabled(self) -> bool:
        return bool(settings.pushplus_token)

    def send(self, report: BattleReport, draft_status: str) -> None:
        if not self.enabled:
            return
        content = (
            "韩国团战战报已生成\n\n"
            f"比赛：\n{report.team_a.display_name} vs {report.team_b.display_name}\n\n"
            f"比分：\n{report.score_text}\n\n"
            f"公众号草稿：\n{draft_status}\n\n"
            f"时间：\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        response = requests.post(
            self.endpoint,
            json={"token": settings.pushplus_token, "title": "韩国团战战报已生成", "content": content},
            timeout=20,
        )
        response.raise_for_status()
