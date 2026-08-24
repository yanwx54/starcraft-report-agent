from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
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
    parser.add_argument(
        "--mirror-sync",
        metavar="REMOTE",
        help="本机抓取 ELOBoard 页面镜像，上传到 REMOTE（如 root@1.2.3.4）并远程触发发布。需 SSH 免密登录",
    )
    parser.add_argument("--mirror-count", type=int, default=10, help="镜像同步时抓取的详情页数量，默认 10")
    parser.add_argument(
        "--mirror-remote-dir",
        default="/opt/starcraft-report-agent",
        help="服务器上的项目目录，默认 /opt/starcraft-report-agent",
    )
    return parser


def mirror_sync(remote: str, remote_dir: str, count: int) -> int:
    """本机抓取 ELOBoard 镜像 → scp 上传服务器 → SSH 触发服务器离线解析并发布。"""
    from crawler.eloboard import ELOBoardClient

    remote_dir = remote_dir.rstrip("/")
    mirror_dir = settings.output_dir / "mirror"
    mirror_dir.mkdir(parents=True, exist_ok=True)

    matches = None
    # Cloudflare 挑战/源站过载偶发失败，整个流程最多尝试 4 次，间隔递增退避
    for attempt in range(1, 5):
        client = ELOBoardClient()
        try:
            (mirror_dir / "list.html").write_text(client.fetch_html(settings.eloboard_list_url), encoding="utf-8")
            matches = client.list_matches(limit=count)
            if matches:
                for match in matches:
                    (mirror_dir / f"{match.match_id}.html").write_text(client.fetch_html(match.url), encoding="utf-8")
                    print(f"已镜像 {match.match_id}: {match.title}")
                break
            raise RuntimeError("未在 ELOBoard 列表页找到团战记录")
        except Exception as exc:
            print(f"第 {attempt} 次抓取失败：{exc}")
            if attempt == 4:
                raise
            wait = 30 * attempt
            print(f"{wait} 秒后重试...")
            time.sleep(wait)
        finally:
            client.close()

    remote_mirror = f"{remote_dir}/mirror"
    subprocess.run(["ssh", remote, f"mkdir -p {remote_mirror}"], check=True)
    subprocess.run(["scp", "-r", f"{mirror_dir}/.", f"{remote}:{remote_mirror}/"], check=True)
    print(f"镜像已上传：{remote}:{remote_mirror}")

    trigger = (
        f"cd {remote_dir} && ELOBOARD_MIRROR_DIR={remote_mirror} "
        "DRY_RUN=0 .venv/bin/python main.py --publish --json"
    )
    return subprocess.run(["ssh", remote, trigger], check=False).returncode


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    if args.mirror_sync:
        sys.exit(mirror_sync(args.mirror_sync, args.mirror_remote_dir, args.mirror_count))
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
