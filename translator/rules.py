from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import ROOT_DIR


PLAYER_ID_MAP: dict[str, str] = {
    "教主": "Flash",
    "解冻": "Jaedong",
    "老毕": "Bisu",
    "石头": "Stork",
    "永康": "SoulKey",
    "雨神": "Rain",
    "小雪": "Snow",
    "小胖": "Hero",
    "小零": "Queen",
    "光哥": "Light",
    "禽兽": "Best",
    "迷你": "Mini",
    "永镇": "Rush",
    "夏普": "Sharp",
    "抱歉": "Royal",
    "瞬本": "Action",
    "兵营": "Barracks",
    "教练": "Speed",
    "神麦": "Mind",
    "猪头": "Mong",
    "刷分": "Shine",
    "杀本": "Killer",
    "宝儿": "JUM",
    "木头": "Motive",
    "如影": "Ruin",
    "胡子": "Tulbo",
    "钢琴": "Piano",
    "KOP": "Kop",
    "Bishop": "Bishop",
    "寂寞": "Gaemo",
    "脑虫": "Clam",
    "胡克": "Hyuk",
    "BTS": "BTS",
    "小玄": "Hyun",
    "虎狼": "Horang",
    "泰森": "Tyson",
    "老师": "Movie",
    "釜山": "Pusan",
    "米大师": "Midas",
}


@dataclass(slots=True)
class TranslateRules:
    players: dict[str, str] = field(default_factory=dict)
    player_ids: dict[str, str] = field(default_factory=lambda: PLAYER_ID_MAP.copy())
    maps: dict[str, str] = field(default_factory=dict)
    maps_cn: dict[str, str] = field(default_factory=dict)
    terms: dict[str, str] = field(default_factory=dict)

    def translate_player(self, name: str) -> str:
        clean = compact_korean_name(name)
        return self.players.get(clean) or self.players.get(name.strip()) or name.strip()

    def player_label(self, name: str) -> str:
        display = self.translate_player(name)
        player_id = self.player_ids.get(display)
        return f"{display} ({player_id})" if player_id and player_id != display else display

    def translate_map(self, name: str) -> str:
        return self.map_cn(name)

    def map_cn(self, name: str) -> str:
        clean = normalize_map_key(name)
        return self.maps_cn.get(clean) or self.maps_cn.get(name.strip()) or self.maps.get(clean) or self.maps.get(name.strip()) or name.strip()


def compact_korean_name(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def normalize_map_key(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def load_translate_rules(path: Path | None = None) -> TranslateRules:
    path = path or ROOT_DIR / "translate_rules.md"
    text = path.read_text(encoding="utf-8")
    rules = TranslateRules()
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line
            continue
        if not line.startswith("|") or "---" in line:
            if ":" in line and not line.startswith("|"):
                key, value = [part.strip() for part in line.split(":", 1)]
                if key and value:
                    rules.terms[key] = value
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or "韩文" in cells[0]:
            continue

        if "人名" in section and len(cells) >= 3:
            for korean in cells[:2]:
                if korean:
                    rules.players[compact_korean_name(korean)] = cells[2]
        elif "地图" in section and len(cells) >= 4:
            korean_names = [cells[0], cells[1]]
            english, chinese = cells[2], cells[3]
            for korean in korean_names:
                if korean:
                    key = normalize_map_key(korean)
                    rules.maps[key] = english
                    rules.maps_cn[key] = chinese
            if english:
                rules.maps[normalize_map_key(english)] = english
                rules.maps_cn[normalize_map_key(english)] = chinese or english

    return rules
