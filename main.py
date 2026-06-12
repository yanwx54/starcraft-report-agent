from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from agent import StarCraftReportAgent
from config.settings import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="韩国星际争霸团战战报自动生成系统")
    parser.add_argument("--match-id", help="指定 ELOBoard wr_id，例如 2449")
    parser.add_argument("--url", help="指定 ELOBoard 详情页 URL")
    parser.add_argument("--force", action="store_true", help="忽略历史记录并重新生成")
    parser.add_argument("--publish", action="store_true", help="创建微信公众号草稿。需配置微信密钥且 DRY_RUN=0")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出运行结果")
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    target = args.url or args.match_id
    result = StarCraftReportAgent().run(target, force=args.force, publish=args.publish)
    if args.json:
        print(
            json.dumps(
                {
                    "match_id": result.report.match_id,
                    "title": result.article.title,
                    "score": result.report.score_text,
                    "html_path": str(result.html_path),
                    "cards": {key: str(path) for key, path in result.card_paths.items()},
                    "draft_media_id": result.draft_media_id,
                    "skipped": result.skipped,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if result.skipped:
        print(f"已跳过：match_id={result.report.match_id} 已存在。使用 --force 可重新生成。")
        return
    print(f"战报已生成：{result.article.title}")
    print(f"比赛：{result.report.team_a.display_name} {result.report.score_text} {result.report.team_b.display_name}")
    print(f"HTML：{result.html_path}")
    print(f"卡片目录：{settings.card_dir / result.report.match_id}")
    if result.draft_media_id:
        print(f"微信公众号草稿 media_id：{result.draft_media_id}")
    else:
        print("微信公众号草稿：未发布（默认 DRY_RUN 或未配置微信密钥）")


if __name__ == "__main__":
    main()
