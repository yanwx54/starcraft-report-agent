# Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py --match-id 2449 --force
```

输出：

- `output/cards/<match_id>/`：PNG 卡片。
- `output/articles/<match_id>.html`：公众号 HTML。
- `output/agent.db`：生成历史。

可选配置：

- `DEEPSEEK_API_KEY`：启用 DeepSeek 翻译能力。
- `WECHAT_APP_ID`、`WECHAT_APP_SECRET`：启用公众号草稿。
- `PUSHPLUS_TOKEN`：启用通知。
- `DRY_RUN=0`：允许外部发布。
