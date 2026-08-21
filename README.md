# Real Estate Actual Price

個人用台灣實價登錄查詢 MVP。Web/PWA 與 MCP tools 共用同一個 SQLite 資料庫及查詢邏輯，不需要 OpenAI API key。

## 第一階段功能

- 匯入內政部地政司官方實價登錄買賣 CSV ZIP（當期或歷史季度）
- 依地址、行政區、地址內可辨識的社區/建物文字查詢
- 顯示成交日期、單價、總價、坪數、樓層、屋齡及建物類型
- 計算近 1 年/3 年筆數、單價中位數、平均、最高、最低及月趨勢
- 提供 `search_transactions`、`get_market_stats`、`list_areas`、`get_data_status` MCP tools
- 手機可用的 responsive Web/PWA

## Windows 本機啟動

使用 Python 3.11–3.14；以下指令會採用這台電腦目前可正常執行的 Python。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scripts\sync_data.py --current
python web.py
```

瀏覽 `http://127.0.0.1:5000`。第一次同步只匯入當期資料；若需要完整三年統計，請再匯入近 12 個已完成季度，例如：

```powershell
python scripts\sync_data.py --season 112S3 --season 112S4 --season 113S1 --season 113S2 --season 113S3 --season 113S4 --season 114S1 --season 114S2 --season 114S3 --season 114S4 --season 115S1 --season 115S2
```

也可只匯入指定縣市以縮短時間：

```powershell
python scripts\sync_data.py --current --city 臺北市 --city 新北市
```

重複匯入會依官方案件編號更新，不會重複累加。

## Render 公開 PWA（六都展示版）

Repository 已附 `render.yaml` 與 `Dockerfile`。在 Render 建立 Web Service 並連接此 repository 後，選擇 Free 方案；建置時會下載並匯入臺北市、新北市、桃園市、臺中市、臺南市、高雄市的當期官方資料，完成後 Render 會提供 HTTPS 網址，可由手機開啟並安裝為 PWA。

Render 免費服務閒置 15 分鐘後會休眠，首次重新開啟約需一分鐘；每次重新部署都會重新下載六都資料。此公開展示版不提供 MCP endpoint，MCP 與完整本機資料庫仍於個人電腦使用。

## MCP server

```powershell
python mcp_server.py
```

預設以 Streamable HTTP 提供 `http://127.0.0.1:8001/mcp`。可先用 MCP Inspector 檢查：

```powershell
npx @modelcontextprotocol/inspector@latest
```

ChatGPT 開發者模式不能直接連線到一般的 `localhost`；依 OpenAI 官方文件，個人本機測試應使用 Secure MCP Tunnel，或將 `/mcp` 部署到可公開連線的 HTTPS endpoint。第一階段不包含公開部署與驗證。

## 測試

```powershell
python -m pytest
```

## 資料來源與限制

主要資料源為內政部地政司「不動產成交案件實際資訊」Open Data。當期靜態資料通常於每月 1、11、21 日發布，動態查詢網可能較新。資料為申報與去識別化後內容，地址可能只到路段、號碼區間或地號；既有成屋資料沒有可靠、統一的社區名稱欄位，因此社區/建物名稱查詢採地址與備註文字比對，可能漏查或同名誤配。屋齡由可用的建築完成年月估算；缺值時顯示未知。單價以官方每平方公尺欄位換算為每坪，含車位與特殊交易時仍應閱讀備註，不應視為估價或投資建議。

官方來源：

- https://data.gov.tw/dataset/25119
- https://plvr.land.moi.gov.tw/DownloadOpenData
