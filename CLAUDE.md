# teaching-decks — 三師爸式 AI 教學簡報生產基地

## 對話開始時請先讀
- 進度與最近更動：Obsidian `2ndbrain/teaching-decks/工作筆記.md`
- 各簡報狀態：本資料夾 `進度表.md`

## 這個專案做什麼
教材／筆記／舊 PPT → 三種簡報 → 部署分享

| 輸出 | 技能 | 適合 |
|---|---|---|
| HTML 互動簡報 | `soil-html-deck` | 線上分享、課堂互動、直播 |
| 純圖片 .pptx | `soil-image-deck` | 視覺衝擊、做完不再改 |
| 可編輯 .pptx | `soil-teaching-deck` | 正式場合、要交給別人改 |

生圖引擎：`draw` 技能（gpt-image-2，預設 low ≈ NT$0.3/張）。
提示詞範本：vault `創作庫/舊PPT轉HTML簡報-提示詞工具包.md`

## 資料夾規則
- `input/`：教材原檔、舊 PPT 丟這（**不上 GitHub**，可能含校內資料）
- `extracted/`：舊 PPT 萃取的純文字（**不上 GitHub**）
- `decks/<簡報名>/`：每份成品一個資料夾（slides.html 或 .pptx ＋圖）
- `進度表.md`：所有簡報的狀態總表

## 工作模式
- **做新簡報**：「用〔教材/筆記〕做一份〔HTML／全圖／可編輯〕簡報」→ 產出到 decks/
- **翻新舊 PPT**：檔案丟 input/ → 說「翻新 input/XXX.pptx」→ 萃取到 extracted/ → SOIL 重排 → decks/
- **發佈**：收工 commit＋push 即發佈；單份網址 `https://derony.github.io/teaching-decks/decks/<簡報名>/slides.html`
- **結束工作**：說「**收工**」；**接續工作**：說「**開工**」

## 工作桌 + 三個家
- 📋 GDrive：`G:\我的雲端硬碟\teaching-decks\`
- 🐙 GitHub：`Derony/teaching-decks`（公開＋Pages）
- 📘 Obsidian：`2ndbrain/teaching-decks/工作筆記.md`
- 🔥 Firebase：簡報互動（文字雲/投票）資料；集合命名 `<簡報slug>_wordcloud`，每份簡報獨立集合

## 工作注意事項
- repo 是**公開**的：commit 前確認無 API 金鑰、無學生個資；`input/`、`extracted/` 永不上雲（已在 .gitignore）
- 學生互動資料只進 Firebase、去識別化（班級＋座號，永不存名字）
- 生圖先報價（張數 × 單價，按引擎：openai low NT$0.3／gemini NB2 NT$1.4~2.1）再動工；封面/關鍵頁才升 medium
- **每份成品完成後**：把工時、生圖 API 次數與費用、context 估算記進 `資源成本記錄.md`（量測規則見該檔；使用者若提供 /usage 前後 % 就一併記入校正）
- commit 訊息寫清楚做了什麼＋為什麼
