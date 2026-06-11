def _attrs(fill, stroke, stroke_w):
    a = f'fill="{fill}"'
    if stroke is not None:
        a += f' stroke="{stroke}" stroke-width="{stroke_w}"'
    return a


def _darken(color, factor=0.82):
    """#rrggbb 各通道 ×factor 變暗；非 6 位 hex（如 none）回中性灰。"""
    c = (color or "").lstrip("#")
    if len(c) != 6:
        return "#cccccc"
    try:
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#cccccc"
    r, g, b = (max(0, min(255, round(v * factor))) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _leftRightArrowCallout(w, h, fill, stroke, stroke_w):
    # 箭頭一定要比箭桿寬，否則中間鼓成菱形（ARROW_H > BAR_H）
    ARROW_H = 0.95  # 箭頭三角形高佔總高
    BAR_H = 0.40     # 中間箭桿高佔總高
    ARROW_W = 0.22   # 箭頭水平長佔總寬
    BOX_W = 0.30     # 中間方框寬佔總寬

    ah = ARROW_H * h
    bh = BAR_H * h
    bw = BOX_W * w
    aw = ARROW_W * w

    # 左右間距
    side = (w - bw - 2 * aw) / 2
    # 中間方框左/右 x
    box_l = side + aw
    box_r = w - side - aw

    # 左箭尖、上、下
    ly = (h - ah) / 2
    ry = (h + ah) / 2

    # 中間 bar 上下
    by = (h - bh) / 2
    by2 = (h + bh) / 2

    # 繞一圈：從左箭尖開始
    pts = [
        (0, h / 2),          # 左箭尖
        (box_l, ly),         # 左上箭桿轉折
        (box_l, by),         # 方框左上（箭桿上緣）
        (box_r, by),         # 方框右上
        (w, h / 2),          # 右箭尖
        (box_r, by2),        # 方框右下（箭桿下緣）
        (box_l, by2),        # 方框左下
        (box_l, ry),         # 左下箭桿轉折
    ]
    d = f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"
    for x, y in pts[1:]:
        d += f" L {x:.2f} {y:.2f}"
    d += " Z"
    return f'<path d="{d}" {_attrs(fill,stroke,stroke_w)}/>'


def _wedgeEllipseCallout(w, h, fill, stroke, stroke_w):
    margin = stroke_w / 2
    cx = w / 2
    cy = h * 0.44
    rx = w / 2 - margin
    ry = h * 0.40 - margin
    ell = f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" {_attrs(fill,stroke,stroke_w)}/>'
    # 尾巴指右上（朝畫面右上角，忠於原檔語音泡泡方向）
    pts = [(w * 0.66, h * 0.16), (w * 0.80, h * 0.28), (w * 0.99, h * 0.00)]
    poly_pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    poly = f'<polygon points="{poly_pts}" {_attrs(fill,stroke,stroke_w)}/>'
    return ell + "\n" + poly


def _horizontalScroll(w, h, fill, stroke, stroke_w):
    gap = h * 0.18
    x = gap
    y = gap
    rw = w - h * 0.36
    rh = h - h * 0.36
    rx = h * 0.12
    a = _attrs(fill, stroke, stroke_w)
    rect = f'<rect x="{x:.2f}" y="{y:.2f}" width="{rw:.2f}" height="{rh:.2f}" rx="{rx:.2f}" {a}/>'
    darker_fill = _darken(fill, 0.82)   # 卷角＝主體填色加深，做出捲紙陰影
    ad = _attrs(darker_fill, stroke, stroke_w)
    c1 = f'<circle cx="{gap:.2f}" cy="{h*0.30:.2f}" r="{h*0.16:.2f}" {ad}/>'
    c2 = f'<circle cx="{w-gap:.2f}" cy="{h-h*0.30:.2f}" r="{h*0.16:.2f}" {ad}/>'
    return rect + "\n" + c1 + "\n" + c2


_PRESETS = {
    "leftRightArrowCallout": _leftRightArrowCallout,
    "wedgeEllipseCallout": _wedgeEllipseCallout,
    "horizontalScroll": _horizontalScroll,
}


def preset_svg(prst, w, h, fill="#cfe2ff", stroke=None, stroke_w=0):
    fn = _PRESETS.get(prst)
    if fn is None:
        return ""
    return fn(w, h, fill, stroke, stroke_w)


if __name__ == "__main__":
    tests = [
        ("leftRightArrowCallout", 200, 120),
        ("wedgeEllipseCallout", 200, 160),
        ("horizontalScroll", 300, 100),
    ]
    for prst, w, h in tests:
        r = preset_svg(prst, w, h, fill="#cfe2ff", stroke="#7030A0", stroke_w=3)
        assert isinstance(r, str) and "<" in r, f"{prst} failed"
    assert preset_svg("foobar", 100, 100) == ""

    demo = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>preset_svg demo</title>
<style>body{display:flex;flex-wrap:wrap;gap:12px;padding:24px;font-family:sans-serif}
svg{background:#eee;margin:8px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
figcaption{text-align:center;font-size:14px;color:#555}
figure{margin:0}</style></head><body>
"""
    for prst, w, h in tests:
        content = preset_svg(prst, w, h, fill="#cfe2ff", stroke="#7030A0", stroke_w=3)
        demo += f'<figure><svg viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
        demo += content
        demo += f'\n</svg><figcaption>{prst}</figcaption></figure>\n'

    demo += "</body></html>"
    import os
    d = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(d, "preset_svg_demo.html"), "w", encoding="utf-8") as f:
        f.write(demo)
    print("preset_svg OK: 3 presets + demo written")