#!/usr/bin/env python3
"""組裝 1:1 復刻版 slides.html：
- 每頁基底 = 第 0 畫格（JPEG）
- 每個動畫效果 = 相鄰畫格差異區塊 PNG（像素級對齊），效果類型取自 anim.json
- P3 飛行建築 = 透明原圖精靈（淡入＋路徑位移）
"""
import os, io, json, base64, zipfile, re
from PIL import Image, ImageChops

ROOT = r"G:\我的雲端硬碟\teaching-decks"
EXT = os.path.join(ROOT, "extracted", "P1_培正地圖_不插電編程")
FRAMES = os.path.join(EXT, "frames")
DECK = os.path.join(ROOT, "decks", "p1-unplugged-coding")
W, H = 1280, 720

anim = json.load(open(os.path.join(EXT, "anim.json"), encoding="utf-8"))
pics3 = json.load(open(os.path.join(EXT, "slide3_pics.json"), encoding="utf-8"))
zsrc = zipfile.ZipFile(os.path.join(ROOT, "input", "P1_培正地圖_不插電編程.pptx"))

def jpeg_uri(img, q=82):
    buf = io.BytesIO(); img.convert("RGB").save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())

def png_uri(img):
    buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64,", buf.getvalue()

def png_uri_full(img):
    buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())

WIPE_DIR = {1: "top", 2: "right", 4: "bottom", 8: "left"}
FLY_DIR = {1: "top", 2: "right", 4: "bottom", 8: "left"}

def effect_anim(e):
    cls, pid, sub = e["cls"], e["pid"], e.get("sub", 0)
    if cls == "entr":
        if pid == 2:  return {"anim": "flyin", "dir": FLY_DIR.get(sub, "bottom")}
        if pid == 22: return {"anim": "wipe", "dir": WIPE_DIR.get(sub, "left")}
        return {"anim": "fade"}
    if cls == "path":
        m = re.findall(r"[-+0-9.Ee]+", e.get("path", "") or "")
        dx, dy = (float(m[-2]), float(m[-1])) if len(m) >= 4 else (0, 0)
        return {"anim": "fly", "dx": dx, "dy": dy}
    return {"anim": "fade"}

slides_out = []
total_bytes = 0
for sl in anim:
    n = sl["slide"]
    base = Image.open(os.path.join(FRAMES, f"slide{n}_e000.png"))
    uri, sz = jpeg_uri(base)
    total_bytes += sz
    entry = {"base": uri, "steps": []}

    flat = 0
    prev = base
    for step in sl["steps"]:
        out_step = []
        for e in step:
            flat += 1
            meta = effect_anim(e)
            if meta["anim"] == "fly":
                # 飛行精靈：透明原圖 + 幾何 + 位移（與前一個 fade 效果同屬一擊）
                g = pics3[str(e["spid"])]
                img = Image.open(io.BytesIO(zsrc.read("ppt/media/" + g["media"])))
                tw = max(1, round(g["w"] * W * 1.5))  # 1.5x 供高解析顯示
                img = img.resize((tw, round(tw * img.height / img.width)), Image.LANCZOS)
                uri, sz = png_uri_full(img)
                total_bytes += sz
                out_step.append({"t": "fly", "img": uri,
                                 "x": g["x"], "y": g["y"], "w": g["w"], "h": g["h"],
                                 "dx": meta["dx"], "dy": meta["dy"], "spid": e["spid"]})
                prev = Image.open(os.path.join(FRAMES, f"slide{n}_e{flat:03d}.png"))
                continue
            cur = Image.open(os.path.join(FRAMES, f"slide{n}_e{flat:03d}.png"))
            if n == 3 and e["cls"] == "entr" and str(e["spid"]) in pics3:
                # P3 建築的 fade：交給精靈處理，畫格略過
                out_step.append({"t": "spritefade", "spid": e["spid"]})
                prev = cur
                continue
            diff = ImageChops.difference(prev.convert("RGB"), cur.convert("RGB"))
            bbox = diff.convert("L").point(lambda p: 255 if p > 12 else 0).getbbox()
            prev = cur
            if not bbox:
                continue
            pad = 3
            x0, y0 = max(0, bbox[0]-pad), max(0, bbox[1]-pad)
            x1, y1 = min(W, bbox[2]+pad), min(H, bbox[3]+pad)
            patch = cur.crop((x0, y0, x1, y1))
            uri, sz = png_uri_full(patch)
            total_bytes += sz
            out_step.append({"t": "patch", "img": uri,
                             "x": x0/W, "y": y0/H, "w": (x1-x0)/W, "h": (y1-y0)/H,
                             "anim": meta["anim"], "dir": meta.get("dir", "")})
        if out_step:
            entry["steps"].append(out_step)
    slides_out.append(entry)
    print(f"slide {n}: {len(entry['steps'])} 擊, 累計 {total_bytes/1024:.0f} KB")

manifest = json.dumps(slides_out, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>不插電編程 — 我們的培正地圖（1:1 復刻）</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;background:#111;overflow:hidden}
#stage{position:absolute;width:1280px;height:720px;left:50%;top:50%;
  transform-origin:center;background:#fff}
.layer{position:absolute;left:0;top:0;width:100%;height:100%}
.base{width:100%;height:100%;display:block}
.el{position:absolute}
.el img{width:100%;height:100%;display:block}
/* 動畫（時長貼近 PPT 預設 0.5s） */
.fade{animation:fade .5s ease both}
@keyframes fade{from{opacity:0}to{opacity:1}}
.flyin-bottom{animation:flyB .5s cubic-bezier(.2,.7,.3,1) both}
@keyframes flyB{from{transform:translateY(740px)}to{transform:none}}
.flyin-top{animation:flyT .5s cubic-bezier(.2,.7,.3,1) both}
@keyframes flyT{from{transform:translateY(-740px)}to{transform:none}}
.flyin-left{animation:flyL .5s cubic-bezier(.2,.7,.3,1) both}
@keyframes flyL{from{transform:translateX(-1300px)}to{transform:none}}
.flyin-right{animation:flyR .5s cubic-bezier(.2,.7,.3,1) both}
@keyframes flyR{from{transform:translateX(1300px)}to{transform:none}}
.wipe-left{animation:wL .5s linear both}
@keyframes wL{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
.wipe-right{animation:wR .5s linear both}
@keyframes wR{from{clip-path:inset(0 0 0 100%)}to{clip-path:inset(0 0 0 0)}}
.wipe-top{animation:wT .5s linear both}
@keyframes wT{from{clip-path:inset(0 0 100% 0)}to{clip-path:inset(0 0 0 0)}}
.wipe-bottom{animation:wB .5s linear both}
@keyframes wB{from{clip-path:inset(100% 0 0 0)}to{clip-path:inset(0 0 0 0)}}
.sprite{transition:transform 1.1s ease-in-out;will-change:transform}
.instant{animation:none!important;transition:none!important}
#hud{position:fixed;right:14px;bottom:10px;color:#888;font:13px/1.4 system-ui;z-index:9;
  background:rgba(0,0,0,.35);padding:3px 10px;border-radius:12px}
</style>
</head>
<body>
<div id="stage"></div>
<div id="hud"></div>
<script>
const DATA = __MANIFEST__;
const stage = document.getElementById('stage');
const hud = document.getElementById('hud');
let s = 0;            // 目前頁
let k = 0;            // 目前頁已播放的擊數
let busy = false;

function fit(){
  const sc = Math.min(innerWidth/1280, innerHeight/720);
  stage.style.transform = `translate(-50%,-50%) scale(${sc})`;
}
addEventListener('resize', fit); fit();

function el(step, instant){
  // 建立一擊的所有元素（instant=true 時不播動畫）
  const frag = document.createDocumentFragment();
  step.forEach((e, i) => {
    if (e.t === 'spritefade'){
      const sp = stage.querySelector(`[data-spid="${e.spid}"]`);
      if (sp){ sp.style.opacity = 1; }
      return;
    }
    const d = document.createElement('div');
    d.className = 'el';
    d.style.left = (e.x*100)+'%';
    d.style.top = (e.y*100)+'%';
    d.style.width = (e.w*100)+'%';
    d.style.height = (e.h*100)+'%';
    const img = new Image(); img.src = e.img; d.appendChild(img);
    if (e.t === 'fly'){
      d.dataset.spid = e.spid;
      d.classList.add('sprite');
      d.style.opacity = instant ? 1 : 0;
      if (instant){
        d.style.transform = `translate(${e.dx*1280}px, ${e.dy*720}px)`;
      } else {
        // 先淡入（前一個 spritefade 已把 opacity 設 1，這裡保險再設）
        setTimeout(()=>{ d.style.opacity = 1; }, 30);
        setTimeout(()=>{ d.style.transform = `translate(${e.dx*1280}px, ${e.dy*720}px)`; }, 480);
      }
      d.style.transitionProperty = 'transform';
      d.style.opacity = instant ? 1 : d.style.opacity;
    } else {
      if (!instant){
        const cls = e.anim === 'fade' ? 'fade'
          : e.anim === 'flyin' ? 'flyin-'+(e.dir||'bottom')
          : e.anim === 'wipe' ? 'wipe-'+(e.dir||'left') : 'fade';
        d.classList.add(cls);
        d.style.animationDelay = (i*0.45)+'s';
      }
    }
    frag.appendChild(d);
  });
  stage.appendChild(frag);
}

function renderSlide(idx, stepCount){
  stage.innerHTML = '';
  const sl = DATA[idx];
  const layer = document.createElement('img');
  layer.className = 'base'; layer.src = sl.base;
  stage.appendChild(layer);
  for (let i = 0; i < stepCount; i++) el(sl.steps[i], true);
  hud.textContent = (idx+1)+' / '+DATA.length+(sl.steps.length? '　'+stepCount+'/'+sl.steps.length+' 擊':'');
}

function next(){
  const sl = DATA[s];
  if (k < sl.steps.length){ el(sl.steps[k], false); k++; }
  else if (s < DATA.length-1){ s++; k = 0; renderSlide(s, 0); }
  hud.textContent = (s+1)+' / '+DATA.length+(sl.steps.length? '　'+k+'/'+DATA[s].steps.length+' 擊':'');
}
function prev(){
  if (k > 0){ k--; renderSlide(s, k); }
  else if (s > 0){ s--; k = DATA[s].steps.length; renderSlide(s, k); }
}
addEventListener('keydown', e=>{
  if (e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();next();}
  else if (e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prev();}
  else if (e.key==='f'||e.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}
});
addEventListener('click', e=>{
  (e.clientX > innerWidth*0.3) ? next() : prev();
});
renderSlide(0, 0);
</script>
</body>
</html>"""

html = html.replace("__MANIFEST__", manifest)
out = os.path.join(DECK, "slides.html")
open(out, "w", encoding="utf-8").write(html)
print(f"\n輸出 -> {out}  ({len(html.encode('utf-8'))/1024/1024:.2f} MB)")
