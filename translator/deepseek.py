from __future__ import annotations

import requests

from config.settings import settings


class DeepSeekTranslator:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def translate_to_chinese(self, text: str) -> str:
        return self.chat(
            system="你是星际争霸赛事翻译。地图名使用中文翻译名，已替换好的选手名不要再翻译。",
            user=text,
            temperature=0.2,
        )

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not self.enabled:
            return user
        response = requests.post(
            f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            },
            timeout=40,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"DeepSeek 翻译失败：{data}") from exc
