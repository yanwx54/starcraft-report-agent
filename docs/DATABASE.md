# Database

默认数据库为 `output/agent.db`，使用 SQLite，便于本地直接运行。生产环境可在 `.env` 中配置 MySQL：

```env
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/starcraft_report?charset=utf8mb4
```

项目使用 SQLAlchemy 自动创建下列表。

```sql
CREATE TABLE article_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT UNIQUE,
    title TEXT,
    media_id TEXT,
    created_at TEXT
);

CREATE TABLE match_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT UNIQUE,
    match_date TEXT,
    team_a TEXT,
    team_b TEXT,
    score TEXT,
    raw_json TEXT
);
```

SQLite 本地字段与 MySQL 8.0 字段保持同等语义，`raw_json` 在 MySQL 中使用 JSON 类型。
