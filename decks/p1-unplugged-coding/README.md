# 不插電編程 — 我們的培正地圖（P1 HTML 互動簡報）

小一「不插電編程」活動課：讓孩子當校園小導遊，在培正方格地圖上規劃導覽路線，
再把路線「編程」成一串有順序的指令——用最直覺的方式教 **序列（把步驟排好順序）**。

- **來源**：`input/P1_培正地圖_不插電編程.pptx`（翻新）
- **格式**：單一 `slides.html`（圖片 base64 內嵌，約 1.7 MB，打開即用、可離線）
- **風格**：明亮童趣（淺色暖背景、大圓角、嚮導小機器人），10 頁
- **線上網址**（push 後生效）：
  https://derony.github.io/teaching-decks/decks/p1-unplugged-coding/slides.html

## 怎麼用

直接用瀏覽器打開 `slides.html` 即可（或上面的網址）。

| 操作 | 鍵 |
|------|----|
| 下一頁 | `→` / `空白鍵` / 點畫面右側 |
| 上一頁 | `←` / 點畫面左側 |
| 全螢幕 | `F` |

**互動頁**：
- 第 4 頁：點建築看名稱
- 第 7 頁：點地圖大樓「圈起」景點
- 第 8 頁：照順序點大樓排出路線，按 **▶ 執行** 看小機器人沿路線走
- 第 9 頁：自由排自己的路線並執行

## 檔案結構

```
p1-unplugged-coding/
├── slides.html              ← 成品（base64 內嵌，可單檔分享）
├── slides.template.html     ← 可編輯原始碼（圖片是 __IMG_*__ token）
├── slides/
│   ├── generated/           ← Gemini NB2 生成的 3 張圖（封面/嚮導/慶祝）
│   └── source/              ← 沿用原 PPT 的校園手繪圖（地圖＋3 棟建築）
├── build/
│   ├── extract_pptx.py      ← 從 .pptx 萃取文字＋媒體
│   └── embed_images.py      ← 壓縮＋base64 把圖內嵌進 template → slides.html
└── README.md
```

## 要改內容怎麼辦

1. 編輯 `slides.template.html`（文字、結構、互動邏輯都在這）
2. 重跑內嵌：`python build/embed_images.py` → 重新產生 `slides.html`
3. 要換圖：把新圖丟進 `slides/generated/`（用 `draw` 技能生），或換 `slides/source/` 裡的原圖

> 互動地圖的建築座標、顏色定義在 template 內 `const BLD = {...}`，可自行調整位置與配色。
