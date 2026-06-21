from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import BattleReport
from ratings.calculator import PlayerRating


def draw_ratings_card(report: BattleReport, ratings: list[PlayerRating], path: Path) -> None:
    width, height = 1080, 1320
    img = Image.new("RGB", (width, height), "#101820")
    draw = ImageDraw.Draw(img)
    for y in range(height):
        c = int(18 - y / height * 10)
        draw.line((0, y, width, y), fill=(c, c + 8, c + 17))

    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-220, 60, 430, 700), fill=(40, 130, 255, 42))
    gd.ellipse((690, 110, 1280, 760), fill=(255, 60, 120, 36))
    gd.ellipse((250, 820, 880, 1520), fill=(255, 210, 80, 22))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=18, outline="#d8ae32", width=3)
    draw.rounded_rectangle((20, 20, width - 20, height - 20), radius=16, outline="#20385e", width=2)

    center(draw, "POST MATCH RATINGS", width // 2, 70, 24, "#9fb1c8")
    center(draw, "赛后评分", width // 2, 120, 56, "#ffffff")
    center(draw, f"{report.team_a.display_name} {report.score_text} {report.team_b.display_name}", width // 2, 174, 28, "#6fb1ff")

    top = ratings[0]
    draw.rounded_rectangle((80, 220, 1000, 370), radius=18, fill="#151f2e", outline="#ffd166", width=2)
    draw.text((115, 245), "MVP", font=font_for("MVP", 24), fill="#ffd166")
    draw.text((115, 285), top.stat.display_name, font=font_for(top.stat.display_name, 52), fill=race_color_for(top.stat.race))
    draw.text((340, 296), top.tag, font=font_for(top.tag, 28), fill="#ffffff")
    center(draw, f"{top.score:.1f}", 885, 296, 78, "#ffd166")

    y = 410
    for index, rating in enumerate(ratings, start=1):
        stat = rating.stat
        row_color = "#18283a" if index % 2 else "#142132"
        draw.rounded_rectangle((58, y, 1022, y + 76), radius=12, fill=row_color, outline="#263b55", width=1)
        center(draw, f"{index:02d}", 92, y + 38, 20, "#8393aa")
        race_color = race_color_for(stat.race)
        draw.rounded_rectangle((130, y + 22, 166, y + 58), radius=5, outline=race_color, width=2)
        center(draw, stat.race, 148, y + 40, 18, race_color)
        draw.text((190, y + 18), stat.display_name, font=font_for(stat.display_name, 30), fill=race_color)
        draw.text((320, y + 26), stat.team, font=font_for(stat.team, 19), fill="#7f8fa6")
        draw.text((550, y + 26), f"{stat.wins}胜{stat.losses}负", font=font_for("3胜1负", 22), fill="#d6dee9")
        tag_color = tag_color_for(rating.score)
        draw.rounded_rectangle((710, y + 21, 812, y + 58), radius=8, fill=tag_color)
        center(draw, rating.tag, 761, y + 40, 20, "#0b111c")
        center(draw, f"{rating.score:.1f}", 930, y + 39, 42, tag_color)
        y += 86

    center(draw, "虎扑锐评版 · 仅根据本场战绩自动计算", width // 2, height - 54, 18, "#718198")
    img.save(path)


def tag_color_for(score: float) -> str:
    if score >= 8.5:
        return "#38e27d"
    if score >= 7.0:
        return "#6fb1ff"
    if score >= 5.8:
        return "#ffd166"
    if score >= 4.5:
        return "#ff9f45"
    return "#ef476f"


def center(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, size: int, color: str) -> None:
    font = font_for(text, size)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2),
        text,
        font=font,
        fill=color,
        stroke_width=1,
        stroke_fill="#050912",
    )


def race_color_for(race: str) -> str:
    return {"P": "#f2c900", "T": "#4b91ff", "Z": "#b16cff"}.get(race, "#a9b4c2")


def font_for(text: str, size: int) -> ImageFont.FreeTypeFont:
    has_hangul = any("\uac00" <= char <= "\ud7a3" for char in text)
    candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("C:/Windows/Fonts/malgunbd.ttf") if has_hangul else Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/malgun.ttf") if has_hangul else Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
    ]
    for font_path in candidates:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default(size=size)
