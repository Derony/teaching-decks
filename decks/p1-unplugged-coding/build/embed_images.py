#!/usr/bin/env python3
"""把圖片壓縮 + base64 內嵌進 slides.template.html → slides.html。
路徑全部相對於本檔所在的 deck 資料夾，可在任何機器重跑。
卡通圖 JPEG、線稿圖 PNG；無 Pillow 時退回原始位元組。
用法：python build/embed_images.py"""
import os, glob, base64, io, re

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.dirname(HERE)                       # decks/p1-unplugged-coding
GEN = os.path.join(DECK, "slides", "generated")    # AI 生成圖
SRC = os.path.join(DECK, "slides", "source")       # 沿用原 PPT 的圖

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

def latest(prefix):
    fs = sorted(glob.glob(os.path.join(GEN, prefix + "_*.png")))
    if not fs:
        raise FileNotFoundError(prefix)
    return fs[-1]

# token -> (path, kind, maxwidth)  kind: 'jpg' 卡通照片風 / 'png' 線稿
SPEC = {
    "__IMG_COVER__":     (latest("cover"),     "jpg", 1280),
    "__IMG_MASCOT__":    (latest("mascot"),    "jpg", 680),
    "__IMG_CELEBRATE__": (latest("celebrate"), "jpg", 1280),
    "__IMG_MAP__":       (os.path.join(SRC, "map.png"),           "png", 900),
    "__IMG_BLDG1__":     (os.path.join(SRC, "bldg-peizheng.png"), "png", 520),
    "__IMG_BLDG2__":     (os.path.join(SRC, "bldg-teaching.png"), "png", 520),
    "__IMG_BLDG3__":     (os.path.join(SRC, "bldg-activity.png"), "png", 520),
}

def data_uri(path, kind, maxw):
    raw = open(path, "rb").read()
    if not HAVE_PIL:
        mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        return f"data:{mime};base64,{base64.b64encode(raw).decode()}", len(raw)
    img = Image.open(io.BytesIO(raw))
    w, h = img.size
    if w > maxw:
        img = img.resize((maxw, round(h * maxw / w)), Image.LANCZOS)
    buf = io.BytesIO()
    if kind == "jpg":
        img.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    else:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img).convert("RGB")
        else:
            img = img.convert("RGB")
        img.save(buf, "PNG", optimize=True)
        mime = "image/png"
    b = buf.getvalue()
    return f"data:{mime};base64,{base64.b64encode(b).decode()}", len(b)

html = open(os.path.join(DECK, "slides.template.html"), encoding="utf-8").read()
print(f"Pillow: {'yes' if HAVE_PIL else 'no (raw bytes)'}")
total = 0
for token, (path, kind, maxw) in SPEC.items():
    uri, sz = data_uri(path, kind, maxw)
    html = html.replace(token, uri)
    total += sz
    print(f"  {token:18} {os.path.basename(path):22} {kind} -> {sz/1024:7.1f} KB")

leftover = set(re.findall(r"__IMG_[A-Z0-9_]+__", html))
if leftover:
    print("!! leftover tokens:", leftover)

out = os.path.join(DECK, "slides.html")
open(out, "w", encoding="utf-8").write(html)
print(f"\nimages total {total/1024/1024:.2f} MB")
print(f"-> {out}  ({len(html.encode('utf-8'))/1024/1024:.2f} MB)")
