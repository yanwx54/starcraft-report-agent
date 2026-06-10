# Local Secrets Policy

所有真实密钥只保存在本机，不写入代码、不写入文档、不提交版本控制、不打进 Docker 镜像。

## 本地密钥文件

推荐使用根目录的 `.env.local`：

```env
DEEPSEEK_API_KEY=你的本地密钥
WECHAT_APP_ID=你的本地 appid
WECHAT_APP_SECRET=你的本地 secret
PUSHPLUS_TOKEN=你的本地 token
DRY_RUN=1
```

加载优先级：

1. 系统环境变量
2. `.env.local`
3. `.env`
4. 代码默认值

`.env` 和 `.env.local` 已加入 `.gitignore` 与 `.dockerignore`，不会被提交或复制进镜像。仓库里只保留 `.env.example`，其中不能填写真实密钥。

## 发布开关

默认 `DRY_RUN=1`，即使配置了微信密钥也不会发布到公众号草稿。需要真实创建草稿时，本机手动设置：

```env
DRY_RUN=0
```

## 注意事项

- 不要把真实密钥粘贴到聊天窗口、README、issue、日志或截图里。
- 如果曾经公开过密钥，立即到对应平台撤销并重新生成。
- Docker 部署时用运行时环境变量或挂载本机 `.env.local`，不要在镜像中 bake 密钥。
