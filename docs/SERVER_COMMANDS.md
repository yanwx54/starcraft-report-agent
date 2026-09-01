# 服务器操作指令

本文记录登录服务器后的常用操作命令。服务器路径默认是：

```text
/opt/starcraft-report-agent
```

服务器 IP：

```text
199.180.116.188
```

## 1. 登录服务器

在本地终端执行：

```bash
ssh root@199.180.116.188
```

进入项目目录：

```bash
cd /opt/starcraft-report-agent
```

## 2. 从 GitHub 拉取最新代码

```bash
cd /opt/starcraft-report-agent
git pull --ff-only origin main
```

查看当前最新提交：

```bash
git log -1 --oneline
```

## 3. 激活虚拟环境

```bash
source .venv/bin/activate
```

确认 Python 版本：

```bash
python --version
which python
```

## 4. 本地生成战报，不推公众号

```bash
python main.py --force --json
```

指定某一场比赛（新版比赛 ID 为「赛事-日」格式，如 `43-66`；旧版 wr_id 如 `2454` 仍可用）：

```bash
python main.py --match-id 43-66 --force --json
```

## 5. 推送微信公众号草稿

创建公众号草稿必须临时关闭 dry-run：

```bash
DRY_RUN=0 python main.py --force --publish --json
```

指定某一场比赛并推草稿：

```bash
DRY_RUN=0 python main.py --match-id 43-66 --force --publish --json
```

成功时，输出里应该有非空的 `draft_media_id`：

```json
{
  "draft_media_id": "一串微信 media_id"
}
```

如果 `draft_media_id` 是空，说明没有真正创建公众号草稿，需要检查：

- `.env.local` 里是否配置了 `WECHAT_APP_ID`。
- `.env.local` 里是否配置了 `WECHAT_APP_SECRET`。
- 当前命令是否带了 `DRY_RUN=0`。
- 微信公众号后台是否配置了服务器出口 IP 白名单。

## 6. 检查环境变量和微信配置

```bash
cd /opt/starcraft-report-agent
source .venv/bin/activate

python - <<'PY'
from config.settings import settings
from wechat.client import WechatClient

print("dry_run =", settings.dry_run)
print("wechat_app_id_set =", bool(settings.wechat_app_id))
print("wechat_app_secret_set =", bool(settings.wechat_app_secret))
print("wechat_enabled =", WechatClient().enabled)
print("database_url =", settings.database_url)
PY
```

正常推公众号时应看到：

```text
dry_run = False
wechat_app_id_set = True
wechat_app_secret_set = True
wechat_enabled = True
```

注意：如果 `.env.local` 中写了 `DRY_RUN=1`，可以用命令前缀临时覆盖：

```bash
DRY_RUN=0 python main.py --force --publish --json
```

## 7. 服务器定时推送（当前推送方式）

2026-09 ELOBoard 改版后，服务器已能直连新版赛事页（`/events/43`、`/events/33`），
不再需要「本机抓取镜像 → 上传服务器」的模式，直接在服务器上配置 cron 定时推送。

### 7.1 确认服务器时区

cron 按服务器本地时间执行，先确认时区：

```bash
date
```

如果显示 UTC，北京时间凌晨 4 点对应 UTC 前一天 20:00，cron 应写 `0 20 * * *`；
或者直接把服务器时区改成北京时间：

```bash
timedatectl set-timezone Asia/Shanghai
```

### 7.2 配置 crontab（每天凌晨 4:00）

```bash
mkdir -p /opt/starcraft-report-agent/logs
crontab -e
```

加入（服务器本地时间凌晨 4:00）：

```cron
0 4 * * * cd /opt/starcraft-report-agent && git pull --ff-only origin main >> logs/cron.log 2>&1; DRY_RUN=0 .venv/bin/python main.py --publish --json >> logs/cron.log 2>&1
```

要点：

- 用 `.venv/bin/python` 直接调用，无需 `source activate`（cron 环境下更可靠）。
- **不带 `--force`**：最新战报已推送过（历史记录有非空 `media_id`）时自动跳过，不会重复推草稿；
  手动补跑或强制重新生成时才加 `--force`。
- 先 `git pull` 保证服务器跑最新代码；拉取失败不影响当天发布（用 `;` 分隔）。
- 日志追加到 `logs/cron.log`。

### 7.3 验证定时任务环境

不等 4 点，手动模拟 cron 环境跑一次：

```bash
cd /opt/starcraft-report-agent && DRY_RUN=0 .venv/bin/python main.py --json
```

输出 `"skipped": true` 即正常（最新战报已推送过）。要立即重推一次草稿则加 `--force`。

## 8. 排查一次定时推送是否成功

- 看定时任务日志：

```bash
tail -n 200 /opt/starcraft-report-agent/logs/cron.log
```

- 服务器看历史记录（见第 9 节），有新记录且 `media_id` 非空即成功。
- 服务器手动补跑：

```bash
cd /opt/starcraft-report-agent
DRY_RUN=0 .venv/bin/python main.py --publish --json
```

- （备用）本机镜像同步模式仍保留，ELOBoard 再次封锁服务器 IP 时可临时启用：

```powershell
python main.py --mirror-sync root@199.180.116.188
```

## 9. 查看历史推送记录

服务器上不一定安装 `sqlite3` 命令，可以直接用 Python 查：

```bash
cd /opt/starcraft-report-agent
source .venv/bin/activate

python - <<'PY'
import sqlite3

conn = sqlite3.connect("output/agent.db")
for row in conn.execute(
    "select match_id,title,media_id,created_at from article_history order by id desc limit 10"
):
    print(row)
conn.close()
PY
```

如果某条记录的 `media_id` 为空，说明只是本地生成，没有成功创建公众号草稿。

## 10. 常见故障

### 公众号草稿没有推送

检查：

```bash
tail -n 200 /opt/starcraft-report-agent/logs/daily.log
```

如果看到：

```json
"skipped": true
```

说明系统认为这场已经处理过。现在代码只会在存在非空 `media_id` 时认为已经成功推送。

### 微信返回 IP 白名单错误

需要到微信公众号后台添加服务器出口 IP。

常见错误是：

```text
获取微信 access_token 失败：当前服务器出口 IP 不在公众号 IP 白名单中
```

### ELOBoard 被 Cloudflare 拦截

ELOBoard 站点开启了 Cloudflare Managed Challenge（Turnstile），普通 requests 抓取会收到 403。
当前代码的处理方式：

1. 先用 curl_cffi 模拟 Chrome TLS 指纹快速请求。
2. 若仍被挑战（403 + `Cf-Mitigated: challenge`），自动启动 camoufox 反检测浏览器
   （Linux 上通过 Xvfb 虚拟显示器运行，Windows 上无头运行）完成验证并抓取，
   本次运行内后续页面都走浏览器。

如果日志里出现“反检测浏览器未能在时限内通过验证”，检查：

```bash
cd /opt/starcraft-report-agent
source .venv/bin/activate
python -m camoufox fetch   # 确认浏览器已下载
apt install -y xvfb        # Linux 上虚拟显示器模式依赖 Xvfb
```

Ubuntu 18.04 还需要 toolchain PPA 的新版 libstdc++（要求 GLIBCXX_3.4.26+）：

```bash
add-apt-repository -y ppa:ubuntu-toolchain-r/test
apt update && apt install --only-upgrade libstdc++6
```

仍未通过时，可配置 `.env.local` 中的 `ELOBOARD_HTTP_PROXY`（HTTP/HTTPS 代理，
格式 `http://user:password@host:port`），浏览器和快速路径都会使用该代理。

### 中文字体显示成方框或 xx

服务器需要安装中文字体，常见包：

```bash
apt update
apt install -y fonts-noto-cjk fonts-wqy-zenhei
```

安装后重新生成并推送：

```bash
DRY_RUN=0 python main.py --force --publish --json
```

### 报错：没有可评选 MVP 的选手统计

说明抓到的页面没有解析出有效对局。最新代码会跳过无效候选并尝试下一个战报。

先更新代码：

```bash
git pull --ff-only origin main
```

再重新运行：

```bash
DRY_RUN=0 python main.py --force --publish --json
```

## 11. 推荐完整发布流程

每次本地修改代码并推到 GitHub 后，服务器执行：

```bash
cd /opt/starcraft-report-agent
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m camoufox fetch
python -m pytest -q
DRY_RUN=0 python main.py --force --publish --json
```

`python -m camoufox fetch` 首次执行会下载反检测浏览器（约 500MB，只需一次；更新 requirements.txt 后如提示浏览器缺失再执行）。

如果测试依赖在服务器上不完整，可以跳过 `pytest`，但正式更新后建议至少运行一次。
