#!/usr/bin/env python3
"""P6 強化後處理：把 slides_editable.html 第 6 頁的「靜態答案圖」換成甲案互動
（乾淨地圖＋5×5 草稿格＋建築鈕：點一座→地圖圈出格中心＋5×5 對應格浮字）。

設計：保留外框 chrome（背景/視窗框/標題列/第4步標題 spid 2,3,4,25），移除靜態
答案物件（地圖 image6、彩色答案格、座標籤、建築圖），注入 #p6lab 互動元件。
Idempotent：重跑先移除舊的 #p6lab 再注入。原檔在 git，可還原。
用法：python build/enhance_p6.py
"""
import os, re, io, base64
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.dirname(HERE)
HTML = os.path.join(DECK, "slides_editable.html")
MAP = os.path.join(DECK, "slides", "source", "map.png")

# 乾淨地圖 base64（壓一下）
im = Image.open(MAP).convert("RGB")
im.thumbnail((680, 680), Image.LANCZOS)
buf = io.BytesIO(); im.save(buf, "JPEG", quality=86, optimize=True)
MAP_URI = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

# 答案格（座→[row,col]）：使用者校對過的正解
ANS = {"H": (1, 1), "A": (3, 3), "C": (2, 5), "E": (4, 1)}
COL = {"H": "#2ec97a", "A": "#ff5d6c", "C": "#15c0c9", "E": "#1e9bff"}

# ---- 互動元件（scoped #p6lab，鋪滿 .slide 內容區，畫布 1440x810）----
COMPONENT = """
<div id="p6lab">
  <div class="p6-hint">看地圖找出每座的方格 → 在 5×5 草稿格寫下字母（相同字母只選 1 格）</div>
  <div class="p6-map">
    <img src="__MAP__" alt="培正校園地圖">
    <div class="p6-ring" data-r="H"></div><div class="p6-ring" data-r="A"></div>
    <div class="p6-ring" data-r="C"></div><div class="p6-ring" data-r="E"></div>
  </div>
  <div class="p6-grid">
    <div class="p6-corner"></div>
    <div class="p6-col">一</div><div class="p6-col">二</div><div class="p6-col">三</div><div class="p6-col">四</div><div class="p6-col">五</div>
    __ROWS__
  </div>
  <div class="p6-btns">
    <span class="p6-pick">點一座：</span>
    <button class="p6-b" data-b="H" style="background:#2ec97a" disabled>H</button>
    <button class="p6-b" data-b="A" style="background:#ff5d6c">A</button>
    <button class="p6-b" data-b="C" style="background:#15c0c9">C</button>
    <button class="p6-b" data-b="E" style="background:#1e9bff">E</button>
    <button class="p6-b p6-reset" data-b="_reset">↺ 重來</button>
  </div>
  <div class="p6-note">H 座是起點，已填在 甲一（左上）。點 A／C／E 看老師示範怎麼讀地圖、填格子。</div>
</div>
<style>
#p6lab{position:absolute;inset:0;font-family:"Microsoft JhengHei","Noto Sans TC",sans-serif;color:#222;z-index:30}
#p6lab .p6-hint{position:absolute;left:70px;top:150px;width:1300px;font-size:26px;font-weight:700;color:#1a6}
#p6lab .p6-map{position:absolute;left:70px;top:200px;width:560px;height:560px;border:3px solid #1a1a1a;border-radius:8px;background:#fff;overflow:hidden}
#p6lab .p6-map img{width:100%;height:100%;display:block}
#p6lab .p6-ring{position:absolute;width:18%;height:18%;border:7px solid #f33;border-radius:50%;
  transform:translate(-50%,-50%);opacity:0;transition:opacity .25s;pointer-events:none;box-shadow:0 0 0 4px rgba(255,60,60,.2)}
#p6lab .p6-ring.show{opacity:1}
#p6lab .p6-grid{position:absolute;left:760px;top:208px;display:grid;
  grid-template-columns:40px repeat(5,78px);grid-template-rows:40px repeat(5,78px);gap:6px}
#p6lab .p6-corner{}
#p6lab .p6-col,#p6lab .p6-row{display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:#999}
#p6lab .p6-cell{border:3px solid #cfd6e4;border-radius:9px;background:#f6f8fc;display:flex;align-items:center;justify-content:center;
  font-family:Arial;font-weight:700;font-size:40px;color:#fff}
#p6lab .p6-cell.filled{box-shadow:inset 0 0 0 4px #fff}
#p6lab .p6-btns{position:absolute;left:760px;top:690px;display:flex;align-items:center;gap:14px}
#p6lab .p6-pick{font-size:22px;color:#666}
#p6lab .p6-b{border:none;cursor:pointer;color:#fff;font-weight:700;font-size:30px;width:74px;height:64px;border-radius:12px;
  box-shadow:0 5px 0 rgba(0,0,0,.18)}
#p6lab .p6-b:active{transform:translateY(2px);box-shadow:0 3px 0 rgba(0,0,0,.18)}
#p6lab .p6-b:disabled{opacity:.45;cursor:default}
#p6lab .p6-reset{background:#e7eaf0;color:#555;font-size:20px;width:auto;padding:0 18px}
#p6lab .p6-note{position:absolute;left:760px;top:762px;width:620px;font-size:21px;color:#a36b00}
</style>
<script>
(function(){
  var ANS=__ANS__, COL=__COL__;
  var lab=document.getElementById('p6lab');
  function fill(k){
    var rc=ANS[k], r=rc[0], c=rc[1];
    var cell=lab.querySelector('.p6-cell[data-rc="'+r+'-'+c+'"]');
    cell.textContent=k; cell.style.background=COL[k]; cell.classList.add('filled');
    var ring=lab.querySelector('.p6-ring[data-r="'+k+'"]');
    ring.style.left=((c-0.5)*20)+'%'; ring.style.top=((r-0.5)*20)+'%';
    ring.style.borderColor=COL[k]; ring.classList.add('show');
    lab.querySelector('.p6-note').textContent=(k==='H'?'H 座起點，甲一。':k+' 座跨多格、只選 1 個 → 填在 '+rowName(r)+colName(c)+'。');
  }
  function rowName(r){return ['','甲','乙','丙','丁','戊'][r];}
  function colName(c){return ['','一','二','三','四','五'][c];}
  function reset(){
    lab.querySelectorAll('.p6-cell.filled').forEach(function(c){ if(c.dataset.rc!=='1-1'){c.textContent='';c.style.background='#f6f8fc';c.classList.remove('filled');} });
    lab.querySelectorAll('.p6-ring').forEach(function(rg){ if(rg.dataset.r!=='H')rg.classList.remove('show'); });
    lab.querySelectorAll('.p6-b[data-b]').forEach(function(b){ if(b.dataset.b!=='H'&&b.dataset.b!=='_reset')b.disabled=false; });
    lab.querySelector('.p6-note').textContent='H 座是起點，已填在 甲一（左上）。點 A／C／E 看老師示範怎麼讀地圖、填格子。';
  }
  lab.querySelectorAll('.p6-b').forEach(function(btn){
    btn.addEventListener('click',function(ev){ ev.stopPropagation();
      var k=btn.dataset.b;
      if(k==='_reset'){reset();return;}
      fill(k); btn.disabled=true;
    });
  });
  fill('H');
})();
</script>
"""

# 組 5×5 cell（含列標）
rows = []
rowlabel = ["甲", "乙", "丙", "丁", "戊"]
for r in range(1, 6):
    rows.append(f'<div class="p6-row">{rowlabel[r-1]}</div>')
    for c in range(1, 6):
        rows.append(f'<div class="p6-cell" data-rc="{r}-{c}"></div>')
ROWS_HTML = "\n    ".join(rows)

import json
comp = (COMPONENT.replace("__MAP__", MAP_URI).replace("__ROWS__", ROWS_HTML)
        .replace("__ANS__", json.dumps(ANS)).replace("__COL__", json.dumps(COL)))

html = open(HTML, encoding="utf-8").read()

# idempotent：先移除舊的 #p6lab 元件（含其 style/script）
html = re.sub(r'\n?<div id="p6lab">.*?</script>\s*', "", html, flags=re.S)

# 取第 6 頁
m = re.search(r'(<section class="slide" data-n="6">)(.*?)(</section>)', html, flags=re.S)
if not m:
    raise SystemExit("找不到第 6 頁")
KEEP = {"2", "3", "4", "25"}  # 背景/視窗框/標題列/第4步標題
kept = []
for line in m.group(2).splitlines():
    sp = re.search(r'data-spid="(\d+)"', line)
    if sp and sp.group(1) not in KEEP:
        continue
    kept.append(line)
new_body = "\n".join(kept) + "\n" + comp
new_section = m.group(1) + new_body + m.group(3)
html = html[:m.start()] + new_section + html[m.end():]

open(HTML, "w", encoding="utf-8").write(html)
removed = len(m.group(2).splitlines()) - len([k for k in kept if k.strip()])
print(f"OK：第 6 頁注入甲案互動；保留 chrome {len(KEEP)} 物件、移除靜態答案物件、map {len(MAP_URI)//1024}KB base64")
