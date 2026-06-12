# 微信公众号排版经验

本文记录本项目生成微信公众号草稿时踩过的排版坑，以及后续修改版式时优先检查的规则。

## 核心结论

微信公众号编辑器和普通浏览器不一样。浏览器里正常的多行缩进 HTML，进入公众号草稿后可能被处理成明显空白。

本项目的公众号正文 HTML 应尽量做到：

- 少用源码换行和缩进。
- 少套无意义外层容器。
- 避免隐藏占位块，例如 `display:none`。
- 所有关键间距写成内联样式。
- 外层容器顶部 `padding` 尽量为 `0`。
- 图片、卡片、段落之间用小 `margin` 控制，不用大段空白分隔。

## 当前版式规则

当前模板位置：

```text
templates/article.html.j2
```

当前渲染入口：

```text
report/html.py
```

当前手机阅读尺寸：

```text
正文：16px
行高：1.75
小标题：17px
主标题：22px
```

正文结构：

- 顶部总览卡图片。
- 居中标题区。
- 蓝色摘要框。
- 对局回顾。
- 每轮文字 + 对应卡片图片。
- 本场焦点 / MVP。
- 总结。

注意：正文里不再单独放“比赛结果 / FINAL SCORE”块，因为顶部总览卡已经展示最终比分。

## 已踩过的坑

### 1. 草稿里出现大块空白

常见原因：

- 模板 HTML 使用多行缩进字符串。
- 外层容器设置了较大的顶部或底部 `padding`。
- 卡片之间使用了过大的 `margin`。
- 图片外面又包了多层 `section`。

当前解决方式：

- `render_article_html()` 会调用 `compact_wechat_html()`。
- 该函数会移除标签之间的源码空白和换行。
- 模板里的容器间距都用较小的内联 `margin` 控制。

### 2. 公众号里图片和文字间距太大

图片外层推荐：

```html
<p style="margin:2px 0 0;">
  <img src="..." style="width:100%;display:block;border-radius:4px;" />
</p>
```

不要使用大段：

```html
<section style="margin:20px 0 24px;">
```

### 3. 标题重复或信息重复

顶部总览卡已经包含：

- 比赛日期。
- 联赛名。
- 队伍。
- 最终比分。
- 奖金信息。

因此正文里不要再放一个独立的 `FINAL SCORE` 区块。

### 4. 隐藏块不适合公众号

避免在正文 HTML 中出现：

```html
display:none
```

虽然浏览器里不可见，但公众号编辑器可能不友好，容易带来异常空白或不可控结构。

## 推荐检查命令

生成一篇本地文章后运行：

```powershell
cd "D:\codex Project\starcraft-report-agent"

@'
from pathlib import Path

html = Path("output/articles/2454.html").read_text(encoding="utf-8")
checks = {
    "has_newlines": "\n" in html,
    "old_hidden_meta": "display:none" in html,
    "old_outer_padding": "padding:24px 12px 52px" in html,
    "body_size": "font-size:16px;line-height:1.75" in html,
    "compact_image_margin": "margin:2px 0 0" in html,
    "outer_zero_padding": "margin:0 auto;padding:0" in html,
}
for key, value in checks.items():
    print(f"{key}: {value}")
'@ | python -
```

理想结果：

```text
has_newlines: False
old_hidden_meta: False
old_outer_padding: False
body_size: True
compact_image_margin: True
outer_zero_padding: True
```

## 测试

修改模板或 HTML 渲染逻辑后，必须运行：

```bash
python -m pytest -q
```

重点关注这些测试：

- 没有大将战时不生成大将战章节。
- 生成 HTML 不包含源码换行。
- 生成 HTML 不包含 `display:none`。
- 生成 HTML 保持正文 `16px / 1.75`。

## 发布注意事项

已经创建到微信公众号后台的旧草稿不会自动更新样式。修改代码后，必须重新运行发布命令创建一篇新的草稿。

服务器重新生成公众号草稿：

```bash
cd /opt/starcraft-report-agent
git pull --ff-only origin main
source .venv/bin/activate
DRY_RUN=0 python main.py --force --publish --json
```
