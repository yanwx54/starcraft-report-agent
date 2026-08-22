# Agent Architecture

模块对应关系：

- `crawler/eloboard.py`：Spider Agent，抓取并解析 ELOBoard。
- `translator/rules.py`：Name Agent，解析 `translate_rules.md`。
- `translator/deepseek.py`：Translate Agent，封装 DeepSeek Chat API。
- `report/generator.py`：Report Agent，生成标题、正文、MVP；写作后处理遵循 [blader/humanizer](https://github.com/blader/humanizer)，并在大将战正文中保留抽签模式、双方选手、地图和胜者。
- `cards/generator.py`：Card Agent，生成大比分总览图与轮次 PNG 卡；MVP 只在正文描述。
- `report/html.py`：公众号 HTML 生成。
- `wechat/client.py`：Wechat Agent，获取 token、上传图片、创建草稿。
- `notify/pushplus.py`：Notify Agent，发送 PushPlus。
- `database/store.py`：历史记录和去重。
- `agent.py`：总编排入口。

定时运行：

```bash
python scheduler.py
```

也可以用 Windows 任务计划程序或 Docker cron 每天 08:00 执行：

```bash
python main.py
```
