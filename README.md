# NYSE Breadth Data — GitHub Actions 桥接

美股 NYSE 涨跌家数数据，通过 GitHub Actions (US IP) 每日从 Yahoo Finance 拉取，
推送到本仓库的 `nyse_breadth.json`。

## 为什么需要这个？

腾讯云国内服务器无法直接访问 Yahoo Finance（被 403 封 IP）。但 GitHub Actions 的 runner
在美国，可以正常访问。这个仓库作为数据桥接——Actions 拉取 → 推 JSON → 服务器 curl raw URL。

## 部署步骤

### 1. 创建 GitHub 仓库
```bash
# 在 GitHub 网页上创建新仓库: fredmaoonline/nyse-breadth-data
# 设置为 Public (raw.githubusercontent.com 需要公开仓库)

cd /path/to/this/folder
git init
git add .
git commit -m "Initial: NYSE breadth scraper via GitHub Actions"
git remote add origin git@github.com:fredmaoonline/nyse-breadth-data.git
git push -u origin main
```

### 2. 启用 GitHub Actions
- 仓库 → Settings → Actions → General
- 确保 "Allow all actions" 已选
- Workflow permissions: Read and write

### 3. 手动触发首次运行
- 仓库 → Actions → "Daily NYSE Breadth Fetch" → Run workflow

### 4. 验证
```bash
curl https://raw.githubusercontent.com/fredmaoonline/nyse-breadth-data/main/nyse_breadth.json
```

## 自动调度
- 美股交易日 16:30 ET (UTC 20:30/21:30) 自动运行
- 手动触发随时可用

## 数据格式
```json
{
  "last_update": "2026-06-27T20:30:00Z",
  "latest": {
    "date": "2026-06-27",
    "advancing": 1523,
    "declining": 1247,
    "net_advances": 276,
    "mcclellan": -84.5
  },
  "records": [...]
}
```
