#!/usr/bin/env python3
"""layout.json → 可編輯 HTML：每物件重建成絕對定位的真 HTML 元素（文字可選取可編輯）。
設計畫布 1440x810px（EMU/12700，1pt=1px），整體 CSS scale 適配視窗。圖片 base64 內嵌單檔。

用法：python build_editable.py <layout.json> <media_dir> <out.html>
PoC 階段：A 文字(div) + B 圖片(img) 完整渲染；C 類 preset 形狀先畫占位框（之後補 SVG）。
"""
import sys, json, base64, os, html, io
try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

EMU_PX = 12700.0          # 1px = 12700 EMU（=1pt，設計畫布 1pt=1px）
JH = '"Microsoft JhengHei","微軟正黑體","PingFang TC","Heiti TC","Noto Sans TC",sans-serif'


def px(emu):
    return round((emu or 0) / EMU_PX, 2)


def compress_b64(path, maxw=1280):
    """壓縮成 data URI：照片→JPEG q82；線稿/箭頭/Ink PNG 保留透明；過寬縮到 maxw。"""
    raw = open(path, "rb").read()
    ext = os.path.splitext(path)[1].lower()
    if not HAVE_PIL or ext == ".svg":
        mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".svg": "svg+xml"}.get(ext, "png")
        return f"data:image/{mime};base64," + base64.b64encode(raw).decode()
    img = Image.open(io.BytesIO(raw))
    w, h = img.size
    if w > maxw:
        img = img.resize((maxw, round(h * maxw / w)), Image.LANCZOS)
    buf = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    else:
        if img.mode == "P":
            img = img.convert("RGBA")
        img.save(buf, "PNG", optimize=True)   # 保留透明（疊在底圖上的線稿/箭頭/Ink）
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


class ImagePool:
    """登記用到的圖片並去重（同檔名只存一份），最後統一壓縮成 {key: dataURI} 供 JS 還原。"""
    def __init__(self, media_dir):
        self.media_dir = media_dir
        self.used = {}      # key(basename) -> 相對路徑

    def ref(self, rel):
        key = os.path.basename(rel)
        self.used.setdefault(key, rel)
        return key

    def build_dict(self):
        return {k: compress_b64(os.path.join(self.media_dir, os.path.basename(r)))
                for k, r in self.used.items()}


def rot_style(xfrm):
    rot = (xfrm or {}).get("rot", 0)
    parts = []
    if rot:
        parts.append(f"rotate({round(rot/60000, 2)}deg)")
    if (xfrm or {}).get("flipH"):
        parts.append("scaleX(-1)")
    if (xfrm or {}).get("flipV"):
        parts.append("scaleY(-1)")
    return f"transform:{' '.join(parts)};" if parts else ""


def box_style(xfrm):
    x = xfrm or {}
    return (f"left:{px(x.get('x'))}px;top:{px(x.get('y'))}px;"
            f"width:{px(x.get('cx'))}px;height:{px(x.get('cy'))}px;")


def render_text(shape):
    """A 類：文字框 → contenteditable div，逐段逐 run 還原字型/字級/粗體/顏色/對齊。"""
    paras = shape.get("text") or []
    body = []
    for pi, para in enumerate(paras):
        algn = {"ctr": "center", "r": "right", "just": "justify"}.get(para.get("algn"), "left")
        ls = ""
        lnspc = para.get("lnspc")
        if lnspc:
            if lnspc[0] == "pts":
                ls = f";line-height:{round(lnspc[1] / 100, 1)}px"   # 固定行距(pt→px)
            elif lnspc[0] == "pct":
                ls = f";line-height:{round(lnspc[1] / 100000, 2)}"  # 倍數
        spans = []
        for run in para["runs"]:
            t = html.escape(run.get("t", ""))
            if not t:
                continue
            st = []
            if run.get("sz"):
                st.append(f"font-size:{run['sz']/100}px")
            if run.get("b"):
                st.append("font-weight:700")
            if run.get("i"):
                st.append("font-style:italic")
            if run.get("color"):
                st.append(f"color:#{run['color']}")
            if run.get("face"):
                st.append(f'font-family:"{run["face"]}",{JH}')
            spans.append(f'<span style="{";".join(st)}">{t}</span>')
        body.append(f'<div class="para" data-pi="{pi}" style="text-align:{algn}{ls}">{"".join(spans) or "<br>"}</div>')
    return "".join(body)


def shape_decoration(shape):
    """形狀填色/邊框 → (background, border) CSS。nofill 或無 fill 視為透明。"""
    fill = shape.get("fill")
    ln = shape.get("ln") or {}
    bg = "transparent" if (shape.get("nofill") or not fill) else f"#{fill}"
    border = ""
    if ln.get("color"):
        w = round((ln.get("w") or 12700) / 12700, 1)
        border = f"{w}px solid #{ln['color']}"
    return bg, border


def render_connector(shape):
    """cxn 連接線 → SVG line + 三角箭頭，依 flipH/flipV 定方向。"""
    x = shape.get("xfrm")
    if not x:
        return ""
    left, top, w, h = px(x["x"]), px(x["y"]), px(x["cx"]), px(x["cy"])
    ln = shape.get("ln") or {}
    color = f"#{ln.get('color') or '333333'}"
    sw = round((ln.get("w") or 25400) / 12700, 1)   # 預設 2pt
    x1, y1, x2, y2 = 0.0, 0.0, w, h
    if x.get("flipH"):
        x1, x2 = w, 0.0
    if x.get("flipV"):
        y1, y2 = h, 0.0
    mk, end = "", ""
    if ln.get("tail"):
        mid = f"ar{shape.get('id')}"
        mk = (f'<defs><marker id="{mid}" markerWidth="9" markerHeight="9" refX="7" refY="3" '
              f'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{color}"/></marker></defs>')
        end = f'marker-end="url(#{mid})"'
    return (f'<svg class="obj cxn" data-spid="{shape.get("id")}" style="left:{left}px;top:{top}px;overflow:visible" '
            f'width="{max(w,1)}" height="{max(h,1)}">{mk}'
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" {end}/></svg>')


def render_shape(shape, pool):
    k = shape["kind"]
    if k == "cxn":
        return render_connector(shape)
    xfrm = shape.get("xfrm")
    if not xfrm:
        return ""  # 無幾何（如純背景群組屬性）跳過
    style = box_style(xfrm) + rot_style(xfrm)
    sid = f' data-spid="{shape.get("id")}"'

    # B 類：任何帶 image 的（pic 或 blipFill sp），image 已由 resolve_images 解成 _img
    if shape.get("_img"):
        return (f'<img class="obj img"{sid} style="{style}" data-k="{pool.ref(shape["_img"])}" '
                f'alt="{html.escape(shape.get("name") or "")}" draggable="false">')

    # 形狀填色/邊框（ellipse 再加圓角）
    bg, border = shape_decoration(shape)
    deco = ""
    if bg != "transparent":
        deco += f"background:{bg};"
    if border:
        deco += f"border:{border};box-sizing:border-box;"
    if shape.get("prst") == "ellipse":
        deco += "border-radius:50%;"

    # A 類：有文字 → 真文字 div（可同時帶色塊/邊框）；anchor 控垂直對齊
    if shape.get("text"):
        anc = {"ctr": "center", "b": "flex-end"}.get(shape.get("anchor"), "flex-start")
        return (f'<div class="obj txt"{sid} style="{style}{deco}'
                f'display:flex;flex-direction:column;justify-content:{anc}">{render_text(shape)}</div>')

    # C 類：preset 形狀——有填色/邊框就畫，否則淡占位（如 callout 走主題色，待優化）
    if shape.get("geom") == "preset":
        if deco:
            return f'<div class="obj shape"{sid} style="{style}{deco}"></div>'
        return (f'<div class="obj shape-ph"{sid} data-prst="{shape.get("prst")}" style="{style}" '
                f'title="{html.escape(shape.get("name") or "")} [{shape.get("prst")}]"></div>')

    # D 類 custom / 其他：有裝飾就畫，否則淡占位
    if deco:
        return f'<div class="obj shape"{sid} style="{style}{deco}"></div>'
    return (f'<div class="obj other-ph"{sid} style="{style}" '
            f'title="{html.escape(shape.get("name") or "")}"></div>')


def resolve_images(shape, rels):
    """把 shape 的 image(rId) 解成 media 路徑，存到 _img；群組遞迴。"""
    if shape.get("image") and shape["image"] in rels:
        shape["_img"] = rels[shape["image"]]
    for ch in shape.get("children", []) or []:
        resolve_images(ch, rels)


def flatten_group(grp, ox=0, oy=0):
    """把群組子物件依 chOff/chExt → 外框 xfrm 做座標變換後攤平。PoC：線性縮放平移。"""
    gx = grp.get("xfrm") or {}
    ch_off = grp.get("chOff") or {"x": 0, "y": 0}
    ch_ext = grp.get("chExt") or {"cx": gx.get("cx", 1), "cy": gx.get("cy", 1)}
    sx = (gx.get("cx", 0) / ch_ext["cx"]) if ch_ext["cx"] else 1
    sy = (gx.get("cy", 0) / ch_ext["cy"]) if ch_ext["cy"] else 1
    base_x = gx.get("x", 0)
    base_y = gx.get("y", 0)
    out = []
    for ch in grp.get("children", []) or []:
        if ch["kind"] == "grp":
            out.extend(flatten_group(ch))  # 巢狀：PoC 先淺層
            continue
        cx = ch.get("xfrm")
        if not cx:
            continue
        nx = dict(cx)
        nx["x"] = base_x + (cx.get("x", 0) - ch_off["x"]) * sx
        nx["y"] = base_y + (cx.get("y", 0) - ch_off["y"]) * sy
        nx["cx"] = cx.get("cx", 0) * sx
        nx["cy"] = cx.get("cy", 0) * sy
        nc = dict(ch)
        nc["xfrm"] = nx
        out.append(nc)
    return out


def main():
    layout_p, media_dir, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    data = json.load(open(layout_p, encoding="utf-8"))
    anim_path = os.path.join(os.path.dirname(layout_p), "anim.json")
    anim = json.load(open(anim_path, encoding="utf-8")) if os.path.exists(anim_path) else []
    anim_by_slide = {p["slide"]: p["steps"] for p in anim}
    pool = ImagePool(media_dir)
    sz = data["slideSize"]
    W, H = px(sz["cx"]), px(sz["cy"])

    sections = []
    for s in data["slides"]:
        rels = s.get("rels", {})
        flat = []
        for sh in s["shapes"]:
            if sh["kind"] == "grp":
                flat.extend(flatten_group(sh))
            else:
                flat.append(sh)
        for sh in flat:
            resolve_images(sh, rels)
        objs = "\n      ".join(render_shape(sh, pool) for sh in flat)
        sections.append(
            f'  <section class="slide" data-n="{s["slide"]}">\n      {objs}\n  </section>'
        )

    imgs_json = json.dumps(pool.build_dict(), ensure_ascii=True)   # 去重後的圖片字典
    anim_json = json.dumps(anim_by_slide, ensure_ascii=False)      # 每頁動畫「擊」序列
    doc = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>不插電編程（可編輯復刻版）</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{height:100%;background:#1b1b1f;overflow:hidden;font-family:{JH}}}
  #stage{{position:absolute;inset:0;display:grid;place-items:center}}
  #deck{{width:{W}px;height:{H}px;position:relative;transform-origin:center center}}
  .slide{{position:absolute;inset:0;width:{W}px;height:{H}px;overflow:hidden;
          background:#fff;display:none}}
  .slide.active{{display:block}}
  .obj{{position:absolute}}
  .img{{object-fit:fill;user-select:none}}
  .txt{{line-height:1.1;color:#1a1a1a;white-space:pre-wrap;overflow:visible}}
  .txt .para{{width:100%}}
  .shape-ph{{border:1.5px dashed #ff7a59aa;border-radius:6px;background:#ff7a5912}}
  .other-ph{{border:1px dotted #9aa;background:#9aa1}}
  #hud{{position:fixed;left:12px;bottom:10px;color:#aaa;font:13px/1.4 system-ui;
        background:#0008;padding:4px 10px;border-radius:8px}}
</style></head>
<body>
<div id="stage"><div id="deck">
{chr(10).join(sections)}
</div></div>
<div id="hud"><span id="pg"></span> · ←/→ 翻頁 · F 全螢幕</div>
<script>
const IMGS={imgs_json};
document.querySelectorAll('img[data-k]').forEach(i=>{{i.src=IMGS[i.dataset.k]||'';}});
const ANIM={anim_json};
const deck=document.getElementById('deck'),slides=[...document.querySelectorAll('.slide')];
let i=0,step=0;const W={W},H={H};
function fit(){{const s=Math.min(innerWidth/W,innerHeight/H);deck.style.transform=`scale(${{s}})`;}}
function steps(){{return ANIM[i+1]||[];}}
function tgt(o,fn){{slides[i].querySelectorAll(`[data-spid="${{o.spid}}"]`).forEach(fn);}}
function hide(o){{tgt(o,el=>{{
  if(o.para)el.querySelectorAll('.para').forEach((p,k)=>{{if(k>=o.para[0]&&k<=o.para[1])p.style.opacity=0;}});
  else el.style.opacity=0;
}});}}
function reveal(o){{tgt(o,el=>{{
  if(o.para)el.querySelectorAll('.para').forEach((p,k)=>{{if(k>=o.para[0]&&k<=o.para[1]){{p.style.transition='opacity .4s ease';p.style.opacity=1;}}}});
  else {{el.style.transition='opacity .45s ease';el.style.opacity=1;}}
}});}}
function resetAnim(){{step=0;steps().forEach(a=>a.forEach(hide));}}
function playStep(){{const s=steps();if(step>=s.length)return false;s[step].forEach(reveal);step++;return true;}}
function show(n,rev){{i=(n+slides.length)%slides.length;slides.forEach((s,k)=>s.classList.toggle('active',k===i));
  document.getElementById('pg').textContent=`第 ${{i+1}}/${{slides.length}} 頁`+(steps().length?` · 第 ${{step}}/${{steps().length}} 擊`:'');
  resetAnim();if(rev)while(playStep()){{}}}}
function advance(){{if(!playStep())show(i+1);
  else document.getElementById('pg').textContent=`第 ${{i+1}}/${{slides.length}} 頁 · 第 ${{step}}/${{steps().length}} 擊`;}}
addEventListener('resize',fit);
addEventListener('keydown',e=>{{
  if(e.key==='ArrowRight'||e.key===' ')advance();
  else if(e.key==='ArrowLeft')show(i-1,true);
  else if(e.key==='f'||e.key==='F'){{if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}}
}});
fit();show(0);
</script>
</body></html>"""
    with open(outp, "w", encoding="utf-8") as f:
        f.write(doc)
    kb = os.path.getsize(outp) / 1024
    print(f"頁數={len(sections)}  輸出={outp}  大小={kb:.0f} KB")


if __name__ == "__main__":
    main()
