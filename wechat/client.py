from __future__ import annotations
import json
from pathlib import Path

import requests

from config.settings import settings


WECHAT_TITLE_MAX_CHARS = 25


class WechatClient:
    api_base = "https://api.weixin.qq.com"

    def __init__(self) -> None:
        self.app_id = settings.wechat_app_id
        self.app_secret = settings.wechat_app_secret

    @property
    def enabled(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def access_token(self) -> str:
        if not self.enabled:
            raise RuntimeError("未配置 WECHAT_APP_ID / WECHAT_APP_SECRET")
        response = requests.get(
            f"{self.api_base}/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": self.app_id, "secret": self.app_secret},
            timeout=20,
        )
        data = response.json()
        if "access_token" not in data:
            if data.get("errcode") == 40164:
                raise RuntimeError(
                    "获取微信 access_token 失败：当前服务器出口 IP 不在公众号 IP 白名单中。"
                    f"微信返回：{data.get('errmsg')}"
                )
            raise RuntimeError(f"获取微信 access_token 失败：{data}")
        return data["access_token"]

    def upload_image(self, image_path: Path, token: str) -> str:
        with image_path.open("rb") as file:
            response = requests.post(
                f"{self.api_base}/cgi-bin/media/uploadimg",
                params={"access_token": token},
                files={"media": (image_path.name, file, "image/png")},
                timeout=30,
            )
        data = response.json()
        if "url" not in data:
            raise RuntimeError(f"上传微信图片失败：{data}")
        return data["url"]

    def upload_thumb(self, image_path: Path, token: str) -> str:
        with image_path.open("rb") as file:
            response = requests.post(
                f"{self.api_base}/cgi-bin/material/add_material",
                params={"access_token": token, "type": "thumb"},
                files={"media": (image_path.name, file, "image/png")},
                timeout=30,
            )
        data = response.json()
        if "media_id" not in data:
            raise RuntimeError(f"上传微信封面素材失败：{data}")
        return data["media_id"]

    def add_draft(self, title: str, content: str, token: str, thumb_media_id: str = "") -> str:
        if not thumb_media_id:
            raise RuntimeError("创建微信草稿失败：缺少 thumb_media_id，请先上传封面素材")
        title = decode_literal_unicode(title)
        content = decode_literal_unicode(content)
        # Keep the push title compact so it displays cleanly in subscription feeds.
        draft_title = truncate_chars(title, WECHAT_TITLE_MAX_CHARS)
        draft_digest = truncate_chars(title, WECHAT_TITLE_MAX_CHARS)
        payload = {
            "articles": [
                {
                    "title": draft_title,
                    "digest": draft_digest,
                    "content": content,
                    "thumb_media_id": thumb_media_id,
                    "show_cover_pic": 0,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        response = requests.post(
            f"{self.api_base}/cgi-bin/draft/add",
            params={"access_token": token},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        data = response.json()
        if "media_id" not in data:
            raise RuntimeError(f"创建微信草稿失败：{data}")
        return data["media_id"]

    def publish_draft(self, title: str, html: str, image_paths: dict[str, Path]) -> tuple[str, dict[str, str]]:
        token = self.access_token()
        image_urls = {key: self.upload_image(path, token) for key, path in image_paths.items()}
        thumb_path = image_paths.get("hero") or next(iter(image_paths.values()))
        thumb_media_id = self.upload_thumb(thumb_path, token)
        media_id = self.add_draft(title, html, token, thumb_media_id)
        return media_id, image_urls


def local_image_urls(image_paths: dict[str, Path]) -> dict[str, str]:
    urls = {}
    for key, path in image_paths.items():
        resolved = path.resolve()
        version = int(resolved.stat().st_mtime)
        urls[key] = f"{resolved.as_uri()}?v={version}"
    return urls


def truncate_chars(value: str, max_chars: int) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def decode_literal_unicode(value: str) -> str:
    if "\\u" not in value:
        return value

    def replace(match):
        return chr(int(match.group(1), 16))

    import re

    return re.sub(r"\\u([0-9a-fA-F]{4})", replace, value)
