from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config.settings import settings
from models import BattleReport, MatchGame, PlayerStat, Round, Team
from ratings.calculator import build_ratings
from ratings.image import draw_ratings_card
from translator.rules import PLAYER_ID_MAP


BG = "#101820"
PANEL = "#182330"
BLUE = "#39a0ed"
RED = "#ef476f"
GOLD = "#ffd166"
GREEN = "#38e27d"
TEXT = "#f8f9fa"
MUTED = "#a9b4c2"


def generate_cards(report: BattleReport, mvp: PlayerStat, out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or settings.card_dir / report.match_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_png in out_dir.glob("*.png"):
        old_png.unlink()
    paths: dict[str, Path] = {}
    paths["hero"] = out_dir / "hero.png"
    draw_hero_card(report, paths["hero"])

    for round_index, round_item in enumerate(report.all_rounds, start=1):
        key = "ace" if "大将战" in round_item.name or "Super Ace" in round_item.name else f"round_{round_index}"
        if not round_item.matches:
            continue
        paths[key] = out_dir / f"{key}.png"
        if key == "ace":
            draw_ace_round_card(report, round_item, paths[key])
        else:
            draw_round_card(report, round_item, round_index, paths[key])

    paths["ratings"] = out_dir / "ratings.png"
    draw_ratings_card(report, build_ratings(report), paths["ratings"])

    return paths


def draw_hero_card(report: BattleReport, path: Path) -> None:
    img, draw = canvas(1080, 545)
    draw_hero_accents(img)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, 1078, 543), radius=12, outline="#304a78", width=2)
    draw.rounded_rectangle((10, 10, 1070, 535), radius=10, outline="#0b1221", width=2)
    title = report.league_name
    if report.match_date:
        title = f"{report.match_date.strftime('%Y.%m.%d')} {title}"
    draw_center_text(draw, title, 540, 62, font_size=50, color=TEXT, stroke_width=2, stroke_fill="#020713")
    draw.line((135, 102, 945, 102), fill="#1b2e4a", width=2)
    draw.line((235, 106, 845, 106), fill="#314f7e", width=1)

    left_color = BLUE
    right_color = RED
    draw_team_panel(draw, report.team_a, (40, 126, 372, 505), left_color)
    draw_team_panel(draw, report.team_b, (708, 126, 1040, 505), right_color)

    prize = parse_prize_amount(report.prize_text)
    total_prize = prize * max(len(report.winner_team.players), 1) if prize else 0
    draw_center_text(draw, "TOTAL PRIZE POOL", 540, 150, 15, MUTED)
    draw_center_text(draw, money_label(total_prize), 540, 185, 36, GREEN, stroke_width=1, stroke_fill="#04150b")

    draw_center_text(draw, f"{report.team_a.score}", 505, 300, 96, TEXT, stroke_width=2, stroke_fill="#020713")
    draw_center_text(draw, ":", 540, 300, 76, "#5c6b82", stroke_width=1, stroke_fill="#020713")
    draw_center_text(draw, f"{report.team_b.score}", 585, 300, 96, TEXT, stroke_width=2, stroke_fill="#020713")
    draw_center_text(draw, "FINAL SCORE", 540, 386, 16, MUTED)

    draw_glow_rect(img, (390, 418, 690, 495), GOLD, radius=8, blur=10)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((390, 418, 690, 495), radius=8, outline="#8a6a12", fill="#111724", width=2)
    draw_center_text(draw, "WINNER PRIZE", 540, 444, 16, GOLD)
    prize_text = money_label(prize) if prize else (report.prize_text or "-")
    draw_center_text(draw, f"{prize_text} / Player", 540, 473, 22, GOLD)
    img.save(path)


def draw_team_panel(draw: ImageDraw.ImageDraw, team, box: tuple[int, int, int, int], color: str) -> None:
    x1, y1, x2, y2 = box
    panel_fill = "#0d1830" if color == BLUE else "#2a1019"
    draw.rounded_rectangle((x1 + 8, y1 + 10, x2 + 8, y2 + 10), radius=10, fill="#020713")
    draw.rounded_rectangle(box, radius=10, fill=panel_fill, outline=color, width=2)
    draw.rounded_rectangle((x1 + 1, y1 + 1, x2 - 1, y1 + 84), radius=9, fill="#102044" if color == BLUE else "#421321")
    draw.line((x1, y1 + 85, x2, y1 + 85), fill="#244069" if color == BLUE else "#662034", width=2)

    draw.text(
        (x1 + 20, y1 + 27),
        team.display_name,
        fill=TEXT,
        font=font_for(team.display_name, 35),
        stroke_width=1,
        stroke_fill="#020713",
    )
    badge_text = "WINNER" if team.is_winner else "LOSER"
    badge_fill = "#2f6cf6" if team.is_winner else "#46556a"
    draw.rounded_rectangle((x2 - 116, y1 + 26, x2 - 20, y1 + 60), radius=5, fill=badge_fill)
    draw_center_text(draw, badge_text, x2 - 68, y1 + 43, 16, TEXT)

    for index, player in enumerate(team.players[:5]):
        row_y = y1 + 120 + index * 47
        race_color = race_color_for(player.race)
        draw.rounded_rectangle((x1 + 26, row_y, x1 + 59, row_y + 33), radius=4, outline=race_color, width=2)
        draw_center_text(draw, player.race if player.race != "U" else "?", x1 + 42, row_y + 17, 17, race_color)
        english = PLAYER_ID_MAP.get(player.display_name, "")
        label = f"{player.display_name} {english}".strip()
        draw.text((x1 + 74, row_y - 2), label, fill=race_color, font=font_for(label, 27), stroke_width=1, stroke_fill="#07101c")


def draw_round_card(
    report: BattleReport,
    round_item: Round,
    round_index: int,
    path: Path,
) -> None:
    width = 1080
    rows = round_item.matches
    row_h = 76 if len(rows) >= 8 else 82
    row_gap = 12
    header_h = 180
    top_y = 210
    footer_h = 82
    height = max(900, top_y + len(rows) * row_h + max(0, len(rows) - 1) * row_gap + footer_h)
    img, draw = canvas(width, height)
    draw_card_accents(img)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=12, outline="#243b63", width=2)
    draw.rounded_rectangle((10, 10, width - 10, height - 10), radius=10, outline="#0b1221", width=2)
    draw.line((0, header_h, width, header_h), fill="#2b3b52", width=2)

    title = round_title(round_item.name)
    draw.text((40, 66), f"SET {round_index}", fill="#4f6384", font=font_for("SET 1", 31), stroke_width=1, stroke_fill="#020713")
    draw.text((138, 52), title, fill=TEXT, font=font_for(title, 43), stroke_width=2, stroke_fill="#020713")
    target_wins = max(round_item.score_a, round_item.score_b, 1)
    draw.text((44, 108), f"FIRST TO {target_wins} WINS", fill="#68a9ff", font=font_for("FIRST TO 4 WINS", 18), stroke_width=1, stroke_fill="#020713")

    score_x = 880
    display_score_a = round_item.score_a
    display_score_b = round_item.score_b
    left_color = TEXT if display_score_a > display_score_b else "#536075"
    right_color = TEXT if display_score_b > display_score_a else "#536075"
    draw_center_text(draw, str(display_score_a), score_x, 72, 82, left_color, stroke_width=2, stroke_fill="#020713")
    draw_center_text(draw, ":", score_x + 58, 72, 60, "#425068", stroke_width=1, stroke_fill="#020713")
    draw_center_text(draw, str(display_score_b), score_x + 116, 72, 82, right_color, stroke_width=2, stroke_fill="#020713")
    winner_text = f"{round_item.winner_team or winning_team_name(report, round_item)} WINS"
    winner_color = BLUE if winner_text.startswith(report.team_a.display_name) else RED
    draw_center_text(draw, winner_text, score_x + 58, 138, 23, winner_color, stroke_width=1, stroke_fill="#020713")

    y = top_y
    for game in rows:
        draw_game_row(draw, report, game, y, row_h)
        y += row_h + row_gap

    img.save(path)


def draw_ace_round_card(report: BattleReport, round_item: Round, path: Path) -> None:
    width, height = 1080, 520
    img, draw = canvas(width, height)
    draw_card_accents(img)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=12, outline="#a38100", width=3)
    winner_team = winning_team_name(report, round_item)
    draw.text((905, 30), f"{winner_team} WINS", fill=GOLD, font=font_for("永镇队 WINS", 18), stroke_width=1, stroke_fill="#020713")
    draw_center_text(draw, "SET 3: SUPER ACE MATCH", 540, 66, 40, TEXT, stroke_width=2, stroke_fill="#020713")
    draw_center_text(draw, '"Winner Takes All"', 540, 108, 18, MUTED)

    if not round_item.matches:
        draw_center_text(draw, "未进行", 540, 250, 82, GOLD, stroke_width=2, stroke_fill="#020713")
        draw_center_text(
            draw,
            f"{report.winner_team.display_name} 已以 {report.winner_team.score}:{report.loser_team.score} 结束比赛",
            540,
            342,
            34,
            TEXT,
            stroke_width=1,
            stroke_fill="#020713",
        )
        draw.rounded_rectangle((382, 390, 698, 435), radius=6, fill="#151b25", outline="#8a6a12", width=2)
        draw_center_text(draw, "NO ACE MATCH NEEDED", 540, 413, 22, GOLD)
        img.save(path)
        return

    game = round_item.matches[0]
    left_wins = game.winner == game.player_a.raw_name
    draw_ace_player(draw, game.player_a.display_name, game.player_a.race, team_name_for(report, game.player_a.raw_name), 226, 290, left_wins)
    draw_ace_player(draw, game.player_b.display_name, game.player_b.race, team_name_for(report, game.player_b.raw_name), 854, 290, not left_wins)
    draw_center_text(draw, "VS", 540, 304, 70, TEXT)
    draw.rounded_rectangle((477, 360, 603, 397), radius=5, fill="#13284b", outline="#3265b8", width=2)
    draw_center_text(draw, f"MAP: {game.map_name}", 540, 379, 17, "#87b8ff")
    img.save(path)


def draw_game_row(draw: ImageDraw.ImageDraw, report: BattleReport, game: MatchGame, y: int, row_h: int) -> None:
    x1, x2 = 30, 1050
    draw.rounded_rectangle((x1 + 6, y + 7, x2 + 6, y + row_h + 7), radius=10, fill="#020713")
    draw.rounded_rectangle((x1, y, x2, y + row_h), radius=10, fill="#172437", outline="#2b3e5d", width=1)
    draw.line((x1 + 2, y + 2, x2 - 2, y + 2), fill="#243b63", width=1)
    mid_y = y + row_h // 2
    left_win = game.winner == game.player_a.raw_name
    left_dim = not left_win
    right_dim = left_win
    draw_side_player(draw, game.player_a.display_name, game.player_a.race, 56, mid_y, left_win, dim=left_dim)
    draw_side_player(draw, game.player_b.display_name, game.player_b.race, 1024, mid_y, not left_win, align_right=True, dim=right_dim)
    draw_center_text(draw, f"GAME {game.id}", 540, mid_y - 12, 15, "#5e708f", stroke_width=1, stroke_fill="#0b1221")
    draw_center_text(draw, game.map_name, 540, mid_y + 12, 18, "#8b98ae")


def draw_side_player(
    draw: ImageDraw.ImageDraw,
    name: str,
    race: str,
    x: int,
    y: int,
    is_win: bool,
    align_right: bool = False,
    dim: bool = False,
) -> None:
    race_color = race_color_for(race)
    main_color = race_color if not dim else "#526075"
    result_color = "#32e66d" if is_win else "#526075"
    result = "WIN" if is_win else "LOSE"
    font_name = font_for(name, 28)
    font_result = font_for(result, 23)

    if align_right:
        draw.rounded_rectangle((x - 34, y - 18, x, y + 18), radius=4, outline=race_color, width=2)
        draw_center_text(draw, race if race != "U" else "?", x - 17, y, 16, race_color)
        name_bbox = draw.textbbox((0, 0), name, font=font_name)
        result_bbox = draw.textbbox((0, 0), result, font=font_result)
        name_x = x - 52 - (name_bbox[2] - name_bbox[0])
        result_x = name_x - 14 - (result_bbox[2] - result_bbox[0])
        draw.text((result_x, y - 17), result, fill=result_color, font=font_result, stroke_width=1, stroke_fill="#07101c")
        draw.text((name_x, y - 20), name, fill=main_color, font=font_name, stroke_width=1, stroke_fill="#07101c")
    else:
        draw.rounded_rectangle((x, y - 18, x + 34, y + 18), radius=4, outline=race_color, width=2)
        draw_center_text(draw, race if race != "U" else "?", x + 17, y, 16, race_color)
        draw.text((x + 52, y - 20), name, fill=main_color, font=font_name, stroke_width=1, stroke_fill="#07101c")
        name_bbox = draw.textbbox((0, 0), name, font=font_name)
        draw.text((x + 66 + name_bbox[2] - name_bbox[0], y - 17), result, fill=result_color, font=font_result, stroke_width=1, stroke_fill="#07101c")


def draw_ace_player(
    draw: ImageDraw.ImageDraw,
    name: str,
    race: str,
    team_name: str,
    x: int,
    y: int,
    is_winner: bool,
) -> None:
    color = race_color_for(race)
    draw.ellipse((x - 78, y - 78, x + 78, y + 78), outline=color, width=6)
    draw_center_text(draw, race, x, y, 72, color)
    if is_winner:
        draw.rounded_rectangle((x - 44, y + 64, x + 44, y + 88), radius=4, fill=GOLD)
        draw_center_text(draw, "WINNER", x, y + 76, 13, "#111111")
    draw_center_text(draw, name, x, y + 132, 34, TEXT)
    draw_center_text(draw, team_name, x, y + 170, 20, GOLD if is_winner else MUTED)


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    for i in range(height):
        ratio = i / height
        color = lerp_color((16, 24, 32), (8, 12, 18), ratio)
        draw.line((0, i, width, i), fill=color)
    draw.rectangle((0, 0, width, 12), fill=GOLD)
    draw.rectangle((0, height - 12, width, height), fill=BLUE)
    return img, draw


def draw_hero_accents(img: Image.Image) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    width, height = img.size
    for x in range(-height, width, 42):
        od.line((x, height, x + height, 0), fill=(55, 91, 148, 24), width=1)
    od.rectangle((0, 0, width, 118), fill=(5, 10, 24, 120))
    od.ellipse((-180, 70, 380, 650), fill=(30, 120, 255, 42))
    od.ellipse((700, 45, 1240, 620), fill=(255, 42, 112, 36))
    overlay = overlay.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(overlay) if img.mode == "RGBA" else img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def draw_card_accents(img: Image.Image) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    width, height = img.size
    for x in range(-height, width, 48):
        od.line((x, height, x + height, 0), fill=(55, 91, 148, 18), width=1)
    od.rectangle((0, 0, width, 180), fill=(5, 10, 24, 130))
    od.ellipse((-220, 80, 420, height + 180), fill=(30, 120, 255, 30))
    od.ellipse((720, 40, 1260, height + 140), fill=(255, 42, 112, 24))
    overlay = overlay.filter(ImageFilter.GaussianBlur(10))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def draw_glow_rect(img: Image.Image, box: tuple[int, int, int, int], color: str, radius: int, blur: int) -> None:
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    rgb = tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    gd.rounded_rectangle(box, radius=radius, outline=(*rgb, 120), width=4)
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))


def draw_center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font_size: int,
    color: str = TEXT,
    stroke_width: int = 0,
    stroke_fill: str = "#000000",
) -> None:
    font = font_for(text, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (x - (bbox[2] - bbox[0]) / 2, y - (bbox[3] - bbox[1]) / 2),
        text,
        fill=color,
        font=font,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def parse_prize_amount(value: str) -> int:
    match = re.search(r"([0-9][0-9,]*)", value or "")
    return int(match.group(1).replace(",", "")) if match else 0


def money_label(value: int) -> str:
    return f"₩{value:,}" if value else "-"


def race_color_for(race: str) -> str:
    return {"P": "#f2c900", "T": "#4b91ff", "Z": "#b16cff"}.get(race, MUTED)


def round_title(name: str) -> str:
    title = name.replace("第一轮 - ", "第1轮 - ").replace("第二轮 - ", "第2轮 - ")
    title = title.replace("职业联赛制", "7/4 职业联赛制") if "7/4" not in title and "职业联赛" in title else title
    title = title.replace("胜者联赛制", "9/5 胜者联赛制") if "9/5" not in title and "胜者联赛" in title else title
    return title


def winning_team_name(report: BattleReport, round_item: Round) -> str:
    if round_item.winner_team:
        return round_item.winner_team
    return report.team_a.display_name if round_item.score_a >= round_item.score_b else report.team_b.display_name


def team_name_for(report: BattleReport, player_raw_name: str) -> str:
    if any(player.raw_name == player_raw_name for player in report.team_a.players):
        return report.team_a.display_name
    if any(player.raw_name == player_raw_name for player in report.team_b.players):
        return report.team_b.display_name
    return ""






def font_for(text: str, size: int) -> ImageFont.FreeTypeFont:
    has_hangul = any("\uac00" <= char <= "\ud7a3" for char in text)
    candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
        Path("C:/Windows/Fonts/malgunbd.ttf") if has_hangul else Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/malgun.ttf") if has_hangul else Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/Dengb.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(math.floor(a[i] + (b[i] - a[i]) * t) for i in range(3))
