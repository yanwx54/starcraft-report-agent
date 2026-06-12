# StarCraft Report Agent

韩国星际争霸 5:5 团战战报自动生成系统。

项目会从 ELOBoard 抓取团战战报，解析队伍、选手、地图、轮次比分和大将战，生成公众号风格正文、PNG 战报卡片、公众号 HTML，并在本地配置密钥后创建微信公众号草稿。

## 功能概览

- 自动抓取 ELOBoard 最新战报。
- 同一天有多个战报时，优先选择 `메이저`，其次才是其他联赛；如果当天只有一个战报，就抓取那一个。
- 自动识别第一轮、第二轮、大将战。
- 大将战支持无编号韩文行，例如 `[녹아] 정영재T (승) vs (패) 김윤중P`。
- 选手名按 `translate_rules.md` 转为中文名。
- 地图名统一使用中文翻译名，例如 `击倒`、`北极星`、`赛点`。
- 生成卡片：
  - 总览卡显示总比分。
  - 第一轮、第二轮卡显示本轮小比分，例如 `4:0`、`2:5`。
  - 大将战卡显示大将战对阵和地图。
- 正文使用公众号手机优先排版。
- 公众号标题限制在 25 字以内。
- 支持 DeepSeek 生成公众号风格正文，并使用结构化赛果做事实校验。
- 支持微信公众号草稿创建。

## 安装

运行环境建议使用 Python 3.8+。如果服务器系统自带 Python 3.6，请单独安装 Python 3.8 并为本项目创建虚拟环境，不要修改系统默认 Python。

```bash
pip install -r requirements.txt
copy .env.example .env.local
```

如果没有 `.env.example`，可以手动创建 `.env.local`，参考下面的环境变量。

## 环境变量

密钥只放在本机 `.env.local` 或系统环境变量中，不要提交到仓库。

```env
DRY_RUN=1
DEEPSEEK_API_KEY=
WECHAT_APP_ID=
WECHAT_APP_SECRET=
PUSHPLUS_TOKEN=
DATABASE_URL=sqlite:///output/agent.db
```

说明：

- `DRY_RUN=1`：只生成本地文件，不创建公众号草稿。
- `DRY_RUN=0`：允许 `--publish` 创建微信公众号草稿。
- `DEEPSEEK_API_KEY`：用于生成公众号风格正文；未配置时使用本地模板。
- `WECHAT_APP_ID` / `WECHAT_APP_SECRET`：用于上传图片和创建公众号草稿。
- `PUSHPLUS_TOKEN`：可选，用于运行通知。
- `DATABASE_URL`：默认使用 SQLite。

MySQL 示例：

```env
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/starcraft_report?charset=utf8mb4
```

密钥安全说明见 [docs/SECURITY.md](docs/SECURITY.md)。

更多运维和排版文档：

- [微信公众号排版经验](docs/WECHAT_LAYOUT.md)
- [服务器操作指令](docs/SERVER_COMMANDS.md)

## 常用命令

抓取最新战报并生成本地文件：

```bash
python main.py --force
```

指定 ELOBoard `wr_id`：

```bash
python main.py --match-id 2450 --force
```

指定详情页 URL：

```bash
python main.py --url "https://eloboard.com/men/bbs/board.php?bo_table=pro_league&wr_id=2450" --force
```

输出 JSON：

```bash
python main.py --match-id 2450 --force --json
```

创建微信公众号草稿：

```bash
set DRY_RUN=0
python main.py --match-id 2450 --force --publish --json
```

PowerShell 临时关闭 dry-run：

```powershell
$env:DRY_RUN='false'; python main.py --match-id 2450 --force --publish --json
```

启动 API：

```bash
uvicorn api:app --reload
```

启动定时任务：

```bash
python scheduler.py
```

## 输出文件

生成后主要看这几个位置：

```text
output/articles/<match_id>.html
output/cards/<match_id>/hero.png
output/cards/<match_id>/round_1.png
output/cards/<match_id>/round_2.png
output/cards/<match_id>/ace.png
output/previews/<match_id>-mobile-preview.html
output/previews/<match_id>-mobile-390x3000.png
output/agent.db
```

当前项目默认文章输出：

- `output/articles/<match_id>.html`：公众号正文 HTML。
- `output/cards/<match_id>/`：战报卡片。
- `output/previews/`：手机预览 HTML 和截图。
- `output/agent.db`：历史记录，用于去重。

## 推荐工作流

1. 本地生成：

```bash
python main.py --match-id 2450 --force --json
```

2. 打开本地 HTML 检查正文：

```text
output/articles/2450.html
```

3. 检查卡片：

```text
output/cards/2450/
```

4. 生成或查看手机预览：

```text
output/previews/2450-mobile-preview.html
output/previews/2450-mobile-390x3000.png
```

5. 确认无误后推送公众号草稿：

```powershell
$env:DRY_RUN='false'; python main.py --match-id 2450 --force --publish --json
```

## 微信公众号草稿

创建草稿需要：

1. 配置 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`。
2. 微信公众平台后台把当前出口 IP 加入 IP 白名单。
3. 设置 `DRY_RUN=0` 或临时环境变量 `$env:DRY_RUN='false'`。
4. 运行 `--publish`。

成功后命令会返回：

```json
{
  "draft_media_id": "..."
}
```

注意：

- 公众号草稿中的图片会先上传到微信，再替换 HTML 中的本地图片地址。
- 本地预览使用 `file:///...` 图片地址。
- 微信图片地址在普通浏览器里可能有防盗链，预览公众号草稿请在微信后台或手机预览中查看。

## 生成规则

### 最新战报选择

默认 `python main.py --force` 会抓取 ELOBoard 最新列表：

- 先找最新日期。
- 如果同一天有多个战报，优先选择标题包含精确 `메이저` 的战报。
- 如果当天只有一个战报，则直接选择该战报。

示例：

```text
2026.05.20 스타 5:5 메이저 프로리그
2026.05.20 스타 5:5 K리그
```

会优先抓取 `메이저 프로리그`。

### 轮次和比分

- 总览卡显示最终大比分，例如 `2:1`。
- 第一轮、第二轮卡显示本轮具体比分，例如 `4:0`、`2:5`。
- 正文可以描述大比分进度，例如首轮后 `1:0`，第二轮后 `1:1`。
- 大将战存在时，正文必须写大将战；不会写成“未进行大将战”。

### 地图名

所有地图统一使用中文翻译名：

```text
Jane Doe    -> 无名氏
Attitude    -> 态度
Octagon     -> 八角笼
MatchPoint  -> 赛点
Neo Sylphid -> 小仙女
KnockOut    -> 击倒
Pole Star   -> 北极星
```

地图规则维护在 [translate_rules.md](translate_rules.md)。

### 标题

公众号标题限制为 25 字以内。

原因：

- 微信后台标题上限常见为 64 字。
- 但手机推送和订阅列表中过长标题会折叠。
- 本项目按更适合推送的 25 字以内生成和截断。

### 公众号版式

当前 HTML 模板位于：

```text
templates/article.html.j2
```

手机排版规则：

- 正文：`16px`
- 行高：`1.75`
- 小标题：`17px`
- 主标题：`22px`
- 顶部总览卡承担最终比分展示。
- 正文不再重复单独的“比赛结果 / FINAL SCORE”块。

## 测试

运行：

```bash
python -m pytest -q
```

测试覆盖：

- 翻译规则加载。
- 最新战报优先级。
- 大将战识别。
- 大将战事实校验。
- 标题长度限制。

## 项目结构

```text
agent.py              主流程编排
main.py               CLI 入口
crawler/eloboard.py   ELOBoard 抓取和解析
report/generator.py   正文生成和事实校验
report/html.py        HTML 渲染
cards/generator.py    PNG 卡片生成
wechat/client.py      微信公众号上传和草稿
translator/rules.py   选手和地图翻译
templates/            公众号 HTML 模板
tests/                自动化测试
output/               生成结果
```

## 注意事项

- 运行发布前先检查本地 HTML 和手机预览。
- 不要提交 `.env.local`、`.env`、`output/` 中的敏感或临时文件。
- 如果微信公众号返回 IP 白名单错误，需要在公众平台后台添加当前出口 IP。
- 如果本地浏览器显示旧图，通常是缓存问题；重新生成后图片 URL 会带 `?v=` 版本号。
