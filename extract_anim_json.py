#!/usr/bin/env python3
"""輸出結構化動畫 JSON：每頁每擊 → [{spid, name, effect, subtype, para, path}]。"""
import sys, json, zipfile
from xml.etree import ElementTree as ET

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
def q(ns, tag): return f"{{{ns}}}{tag}"

src, out_path = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(src)

pres = ET.fromstring(z.read("ppt/presentation.xml"))
rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
rid = {rel.get("Id"): rel.get("Target") for rel in rels}
ordered = ["ppt/" + rid[s.get(q(R,"id"))].lstrip("/").replace("../","")
           for s in pres.find(q(P,"sldIdLst")).findall(q(P,"sldId"))]

result = []
for idx, sp_path in enumerate(ordered, 1):
    root = ET.fromstring(z.read(sp_path))
    shapes = {}
    for nv in root.iter(q(P,"cNvPr")):
        shapes[nv.get("id")] = nv.get("name") or ""

    slide = {"slide": idx, "steps": []}
    timing = root.find(q(P,"timing"))
    if timing is not None:
        cur = None
        for ctn in timing.iter(q(P,"cTn")):
            pcls = ctn.get("presetClass")
            if not pcls:
                continue
            ntype = ctn.get("nodeType") or ""
            tgt = ctn.find(".//" + q(P,"spTgt"))
            spid = tgt.get("spid") if tgt is not None else None
            # 段落範圍（同一文字框分段動畫）
            para = None
            if tgt is not None:
                prg = tgt.find(".//" + q(P,"pRg"))
                if prg is not None:
                    para = [int(prg.get("st")), int(prg.get("end"))]
            # 路徑動畫的 path 字串
            path = None
            if pcls == "path":
                am = ctn.find(".//" + q(P,"animMotion"))
                if am is None:
                    parent_map = {c: p for p in timing.iter() for c in p}
                    node = ctn
                    while node is not None and node.tag != q(P,"animMotion"):
                        node = parent_map.get(node)
                    am = node
                if am is not None:
                    path = am.get("path")
            eff = {"spid": spid, "name": shapes.get(spid, ""),
                   "cls": pcls, "pid": int(ctn.get("presetID") or 0),
                   "sub": int(ctn.get("presetSubtype") or 0)}
            if para: eff["para"] = para
            if path: eff["path"] = path
            if ntype == "clickEffect" or cur is None:
                cur = [eff]
                slide["steps"].append(cur)
            else:
                cur.append(eff)
    result.append(slide)

json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"OK {len(result)} slides -> {out_path}")
for s in result:
    print(f"  slide {s['slide']}: {len(s['steps'])} 擊")
