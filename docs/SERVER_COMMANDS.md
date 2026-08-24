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

指定某一场比赛：

```bash
python main.py --match-id 2454 --force --json
```

## 5. 推送微信公众号草稿

创建公众号草稿必须临时关闭 dry-run：

```bash
DRY_RUN=0 python main.py --force --publish --json
```

指定某一场比赛并推草稿：

```bash
DRY_RUN=0 python main.py --match-id 2454 --force --publish --json
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

## 7. 镜像同步部署（当前推送方式）

服务器机房 IP 被 ELOBoard 的 Cloudflare 挑战拦截（UDP 也被封，WARP 不通），当前采用
「本机抓取 → 上传服务器 → 服务器离线解析并创建公众号草稿」的模式：

```text
本机（家庭 IP，能过 Cloudflare）            服务器（微信白名单 IP）
  python main.py --mirror-sync root@IP
    ① 抓列表页 + 最近10场详情 → output/mirror/
    ② scp 上传 ──────────────────────→  /opt/starcraft-report-agent/mirror/
    ③ ssh 触发 ──────────────────────→  ELOBOARD_MIRROR_DIR=mirror 下离线解析
                                           → 生成文章/卡片 → 创建公众号草稿
```

### 7.1 本机 SSH 免密配置（一次性）

计划任务无人值守运行，不能交互输密码。本机 PowerShell 执行：

```powershell
ssh-keygen -t ed25519   # 一路回车，已有密钥则跳过
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@199.180.116.188 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
ssh root@199.180.116.188 "echo ok"   # 不再要密码即成功
```

### 7.2 服务器端准备（一次性）

```bash
cd /opt/starcraft-report-agent
git pull --ff-only origin main
crontab -e   # 删除原来的每日 8:30 推送任务（改为本机触发）
```

### 7.3 本机注册计划任务（每天 9:00 + 错过后开机补跑）

管理员 PowerShell 执行（按实际 Python 路径调整，`Get-Command python` 可查）：

```powershell
$action = New-ScheduledTaskAction -Execute "D:\Python\python.exe" -Argument "main.py --mirror-sync root@199.180.116.188" -WorkingDirectory "D:\WORKSPACE\projects\Project02_starcraft_report_agent"
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "StarCraftMirrorSync" -Action $action -Trigger $trigger -Settings $settings
```

`-StartWhenAvailable` 表示错过 9:00（电脑没开）时，下次开机联网后自动补跑。

手动同步一次：

```powershell
cd D:\WORKSPACE\projects\Project02_starcraft_report_agent
python main.py --mirror-sync root@199.180.116.188
```

### 7.4 同步说明

- 本机抓取偶发被 Cloudflare 挑战拦截，命令内置 3 次重试；仍失败则当天跳过，下次开机补跑即可。
- 镜像命名：列表页 `list.html`，详情页 `<wr_id>.html`。服务器离线解析优先读镜像，
  镜像里没有的比赛回落到在线抓取（配合 `ELOBOARD_HTTP_PROXY` 可并存）。
- 本机代码需与服务器保持同步：改动后正常 `git push`，两台机器各自 `git pull`。

## 8. 排查一次同步是否成功

镜像同步改为本机触发后没有 daily.log，排查方式：

- 本机看计划任务输出：任务计划程序 → StarCraftMirrorSync → 历史，或手动跑一次看控制台。
- 服务器看历史记录（见第 9 节），有新记录且 `media_id` 非空即成功。
- 服务器手动补跑（镜像已上传时）：

```bash
cd /opt/starcraft-report-agent
ELOBOARD_MIRROR_DIR=/opt/starcraft-report-agent/mirror DRY_RUN=0 .venv/bin/python main.py --publish --json
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
