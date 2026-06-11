#!/usr/bin/env python3
"""解析 .pptx 每頁 spTree → layout.json：抽每個物件的幾何/文字/字型/圖片參照/形狀類型，
供「可編輯 HTML」重建使用（對照圖片化管線的 render_frames.ps1，這條走真 HTML 元素）。零外部套件。

用法：python extract_layout.py <in.pptx> <out_layout.json>
"""
import sys, zipfile, json, re
from xml.etree import ElementTree as ET

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
def a(t): return f"{{{A}}}{t}"
def p(t): return f"{{{P}}}{t}"
def mc(t): return f"{{{MC}}}{t}"
RID_EMBED = f"{{{R}}}embed"


def ix(v, d=0):
    return int(v) if v not in (None, "") else d


def parse_xfrm(spPr):
    """位置/尺寸/旋轉。回傳 EMU。找不到回 None。"""
    if spPr is None:
        return None
    xfrm = spPr.find(a("xfrm"))
    if xfrm is None:
        return None
    off, ext = xfrm.find(a("off")), xfrm.find(a("ext"))
    return {
        "x": ix(off.get("x")) if off is not None else 0,
        "y": ix(off.get("y")) if off is not None else 0,
        "cx": ix(ext.get("cx")) if ext is not None else 0,
        "cy": ix(ext.get("cy")) if ext is not None else 0,
        "rot": ix(xfrm.get("rot")),            # 60000 = 1 度
        "flipH": xfrm.get("flipH") == "1",
        "flipV": xfrm.get("flipV") == "1",
    }


def first_srgb(node):
    """node 底下第一個 srgbClr 的 val（六位 hex），沒有回 None。"""
    if node is None:
        return None
    c = node.find(f".//{a('srgbClr')}")
    return c.get("val") if c is not None else None


def parse_ln(spPr):
    """線框/連接線：{w(EMU), color(hex), head, tail(箭頭型別)}。無 a:ln 回 None。"""
    if spPr is None:
        return None
    ln = spPr.find(a("ln"))
    if ln is None:
        return None
    he, te = ln.find(a("headEnd")), ln.find(a("tailEnd"))
    return {
        "w": ix(ln.get("w")) or None,
        "color": first_srgb(ln),
        "head": he.get("type") if he is not None else None,
        "tail": te.get("type") if te is not None else None,
        "nofill": ln.find(a("noFill")) is not None,
    }


def parse_text(txBody):
    """txBody → 段落陣列。每段 {algn, lvl, runs:[{t,sz,b,i,color,face}]}。無文字回 []。"""
    if txBody is None:
        return []
    paras = []
    for para in txBody.findall(a("p")):
        pPr = para.find(a("pPr"))
        algn = pPr.get("algn") if pPr is not None else None
        lvl = ix(pPr.get("lvl")) if pPr is not None else 0
        lnspc = None
        lnSpc = pPr.find(a("lnSpc")) if pPr is not None else None
        if lnSpc is not None:
            pts, pct = lnSpc.find(a("spcPts")), lnSpc.find(a("spcPct"))
            if pts is not None:
                lnspc = ["pts", int(pts.get("val"))]    # /100 = pt（固定行距）
            elif pct is not None:
                lnspc = ["pct", int(pct.get("val"))]    # /100000 = 倍數
        runs = []
        for r in para.findall(a("r")):
            rPr = r.find(a("rPr"))
            t = r.find(a("t"))
            run = {"t": t.text if (t is not None and t.text) else ""}
            if rPr is not None:
                if rPr.get("sz"):
                    run["sz"] = int(rPr.get("sz"))          # 100 = 1pt
                if rPr.get("b") == "1":
                    run["b"] = True
                if rPr.get("i") == "1":
                    run["i"] = True
                col = first_srgb(rPr.find(a("solidFill")))
                if col:
                    run["color"] = col
                latin = rPr.find(a("latin"))
                if latin is not None and latin.get("typeface"):
                    run["face"] = latin.get("typeface")
            runs.append(run)
        # 整段皆空白 run 也保留（占位/空行），但去掉全無 run 的段
        if runs:
            paras.append({"algn": algn, "lvl": lvl, "lnspc": lnspc, "runs": runs})
    return paras


def blip_rid(node):
    """node 下第一個 a:blip 的 r:embed（圖片 rId）。"""
    b = node.find(f".//{a('blip')}")
    return b.get(RID_EMBED) if b is not None else None


def geom_info(spPr):
    """形狀幾何種類：('preset', prstName) / ('custom', None) / (None, None)。"""
    if spPr is None:
        return (None, None)
    prst = spPr.find(a("prstGeom"))
    if prst is not None:
        return ("preset", prst.get("prst"))
    if spPr.find(a("custGeom")) is not None:
        return ("custom", None)
    return (None, None)


def parse_sp(sp):
    """<p:sp> → 物件 dict。可能同時帶 形狀幾何＋圖片填充＋文字。"""
    nv = sp.find(a_or_p(sp, "nvSpPr"))
    cNvPr = sp.find(f"{p('nvSpPr')}/{p('cNvPr')}")
    spPr = sp.find(p("spPr"))
    gtype, prst = geom_info(spPr)
    txBody = sp.find(p("txBody"))
    bodyPr = txBody.find(a("bodyPr")) if txBody is not None else None
    obj = {
        "kind": "sp",
        "id": cNvPr.get("id") if cNvPr is not None else None,
        "name": cNvPr.get("name") if cNvPr is not None else None,
        "xfrm": parse_xfrm(spPr),
        "geom": gtype,
        "prst": prst,
        "fill": first_srgb(spPr.find(a("solidFill"))) if spPr is not None else None,
        "nofill": spPr is not None and spPr.find(a("noFill")) is not None,
        "ln": parse_ln(spPr),
        "anchor": bodyPr.get("anchor") if bodyPr is not None else None,  # t/ctr/b 垂直對齊
        "image": blip_rid(spPr) if spPr is not None else None,  # blipFill 的 rId
        "text": parse_text(txBody),
    }
    return obj


def parse_pic(pic):
    cNvPr = pic.find(f"{p('nvPicPr')}/{p('cNvPr')}")
    spPr = pic.find(p("spPr"))
    return {
        "kind": "pic",
        "id": cNvPr.get("id") if cNvPr is not None else None,
        "name": cNvPr.get("name") if cNvPr is not None else None,
        "xfrm": parse_xfrm(spPr),
        "image": blip_rid(pic.find(p("blipFill"))),
        "geom": geom_info(spPr)[0],
    }


def parse_cxn(cxn):
    cNvPr = cxn.find(f"{p('nvCxnSpPr')}/{p('cNvPr')}")
    spPr = cxn.find(p("spPr"))
    gtype, prst = geom_info(spPr)
    return {
        "kind": "cxn",
        "id": cNvPr.get("id") if cNvPr is not None else None,
        "name": cNvPr.get("name") if cNvPr is not None else None,
        "xfrm": parse_xfrm(spPr),
        "prst": prst,
        "ln": parse_ln(spPr),
    }


def a_or_p(*_):
    # 占位：spTree 子節點用 p: 命名空間，這函式僅為可讀性保留
    return p("nvSpPr")


def parse_grp(grp):
    """群組：記其外框 xfrm 與子座標系（chOff/chExt），子物件先淺層收集（PoC 不展開變換）。"""
    cNvPr = grp.find(f"{p('nvGrpSpPr')}/{p('cNvPr')}")
    grpSpPr = grp.find(p("grpSpPr"))
    xfrm = grpSpPr.find(a("xfrm")) if grpSpPr is not None else None
    chOff = xfrm.find(a("chOff")) if xfrm is not None else None
    chExt = xfrm.find(a("chExt")) if xfrm is not None else None
    children = []
    for child in list(grp):
        dispatch(child, children)
    return {
        "kind": "grp",
        "id": cNvPr.get("id") if cNvPr is not None else None,
        "name": cNvPr.get("name") if cNvPr is not None else None,
        "xfrm": parse_xfrm(grpSpPr),
        "chOff": {"x": ix(chOff.get("x")), "y": ix(chOff.get("y"))} if chOff is not None else None,
        "chExt": {"cx": ix(chExt.get("cx")), "cy": ix(chExt.get("cy"))} if chExt is not None else None,
        "children": children,
    }


def dispatch(node, out):
    """解析一個 spTree 子節點並 append 到 out。AlternateContent（Ink 等）取 Fallback 的光柵 pic。"""
    tag = node.tag
    if tag == p("sp"):
        out.append(parse_sp(node))
    elif tag == p("pic"):
        out.append(parse_pic(node))
    elif tag == p("cxnSp"):
        out.append(parse_cxn(node))
    elif tag == p("grpSp"):
        out.append(parse_grp(node))
    elif tag == mc("AlternateContent"):
        fb = node.find(mc("Fallback"))
        if fb is not None:
            for ch in list(fb):
                dispatch(ch, out)
    # nvGrpSpPr / grpSpPr 等 spTree 自身屬性略過


def parse_slide(xml_bytes):
    root = ET.fromstring(xml_bytes)
    spTree = root.find(f"{p('cSld')}/{p('spTree')}")
    shapes = []
    for node in list(spTree):           # 順序＝z-order（先畫在底）
        dispatch(node, shapes)
    return shapes


def slide_rels(z, idx):
    """slideN 的 rId → media 相對路徑（去掉 ../，僅留 media/xxx）。"""
    name = f"ppt/slides/_rels/slide{idx}.xml.rels"
    out = {}
    if name not in z.namelist():
        return out
    rels = ET.fromstring(z.read(name))
    for rel in rels:
        tgt = rel.get("Target", "")
        if "media/" in tgt:
            out[rel.get("Id")] = "media/" + tgt.split("media/")[-1]
    return out


def main():
    src, outp = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(src)
    names = z.namelist()

    # 頁面尺寸
    pres = z.read("ppt/presentation.xml").decode("utf-8")
    m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', pres)
    slide_size = {"cx": int(m.group(1)), "cy": int(m.group(2))}

    slide_files = sorted(
        [n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)],
        key=lambda s: int(re.search(r"(\d+)", s).group()),
    )

    slides = []
    for n in slide_files:
        idx = int(re.search(r"slide(\d+)\.xml", n).group(1))
        slides.append({
            "slide": idx,
            "rels": slide_rels(z, idx),
            "shapes": parse_slide(z.read(n)),
        })

    out = {"slideSize": slide_size, "slides": slides}
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 摘要
    print(f"頁面 EMU: {slide_size['cx']} x {slide_size['cy']}")
    for s in slides:
        kinds = {}
        txt = 0
        for sh in s["shapes"]:
            kinds[sh["kind"]] = kinds.get(sh["kind"], 0) + 1
            if sh.get("text"):
                txt += 1
        print(f"  slide{s['slide']}: {dict(kinds)} 含文字物件={txt} rels={len(s['rels'])}")
    print(f"-> {outp}")


if __name__ == "__main__":
    main()
