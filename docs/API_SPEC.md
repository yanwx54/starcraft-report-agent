# API Spec

安装依赖后启动：

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

接口：

- `GET /health`：健康检查。
- `POST /run?match_id=2449&force=true&publish=false`：生成指定比赛战报。
- `GET /history?limit=20`：查看本地文章生成历史。

命令行：

```bash
python main.py
python main.py --match-id 2449 --force
python main.py --match-id 2449 --publish
```
