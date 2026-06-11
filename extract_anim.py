#!/usr/bin/env python3
"""解析 pptx 每頁動畫時序：哪個形狀、什麼效果、第幾個點擊。零外部套件。"""
import sys, zipfile, re
from xml.etree import ElementTree as ET

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ENTR = {1:"出現Appear",2:"飛入FlyIn",3:"百葉窗",4:"盒狀",5:"棋盤",6:"圓形擴展",8:"菱形",
        9:"溶解",10:"淡入Fade",12:"切入PeekIn",13:"加號",14:"隨機線條",16:"分割Split",
        17:"階梯",18:"楔形",19:"輪狀Wheel",20:"擦去Wipe",21:"縮放Zoom",22:"隨機",
        23:"彈跳Bounce?",26:"升起RiseUp",30:"飛旋?",31:"浮入Float?",53:"基本縮放",56:"上浮FloatUp"}
EMPH = {1:"填色變化",2:"字體色",3:"放大縮小?",6:"放大/縮小Grow",8:"線條色",9:"字體樣式?",
        10:"閃爍?",14:"變色?",15:"垂直反白?",16:"輕搖Teeter",18:"波浪?",19:"旋轉Spin",
        26:"閃現Flicker?",27:"彩色脈衝?",32:"脈衝Pulse",35:"亮度?",36:"透明度"}
EXIT = dict(ENTR)
CLASSNAME = {"entr":"進場","emph":"強調","exit":"離場","path":"路徑","mediacall":"媒體","verb":"動作"}
NODETYPE = {"clickEffect":"【點擊】","withEffect":"（同時）","afterEffect":"（接著）"}

def q(ns, tag): return f"{{{ns}}}{tag}"

src = sys.argv[1]
out_path = sys.argv[2]
z = zipfile.ZipFile(src)
names = z.namelist()

pres = ET.fromstring(z.read("ppt/presentation.xml"))
rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
rid = {rel.get("Id"): rel.get("Target") for rel in rels}
ordered = []
for sld in pres.find(q(P,"sldIdLst")).findall(q(P,"sldId")):
    ordered.append("ppt/" + rid[sld.get(q(R,"id"))].lstrip("/").replace("../",""))

lines = []
for idx, sp_path in enumerate(ordered, 1):
    root = ET.fromstring(z.read(sp_path))
    # 形狀目錄：id -> (名稱, 文字摘要)
    shapes = {}
    for sp in root.iter():
        if sp.tag in (q(P,"sp"), q(P,"pic"), q(P,"grpSp"), q(P,"graphicFrame"), q(P,"cxnSp")):
            nv = sp.find(".//" + q(P,"cNvPr"))
            if nv is None:
                for child in sp:
                    nv = child.find(q(P,"cNvPr")) if child.tag.endswith("}nvSpPr") or "nv" in child.tag else None
                    if nv is not None: break
            nv = sp.find(".//" + q(P,"cNvPr"))
            if nv is None: continue
            sid = nv.get("id"); name = nv.get("name") or ""
            txts = [t.text for t in sp.iter(q(A,"t")) if t.text]
            txt = "".join(txts)[:24]
            shapes[sid] = (name, txt)

    lines.append(f"\n========== 投影片 {idx} ==========")
    # 換頁切換效果
    trans = root.find(".//" + q(P,"transition"))
    if trans is not None:
        kids = [t.tag.split('}')[1] for t in trans]
        lines.append(f"[換頁切換] {','.join(kids) if kids else '(預設)'} 屬性={dict(trans.attrib)}")

    timing = root.find(q(P,"timing"))
    if timing is None:
        lines.append("(本頁無動畫)")
        continue

    # 走訪時序樹：找出帶 presetClass 的 cTn（每個＝一個動畫效果）
    step = 0
    found = 0
    for ctn in timing.iter(q(P,"cTn")):
        pcls = ctn.get("presetClass")
        if not pcls: continue
        pid = int(ctn.get("presetID") or 0)
        # nodeType 在自己或上層——這裡直接用自身屬性
        ntype = ctn.get("nodeType") or ""
        tgt = ctn.find(".//" + q(P,"spTgt"))
        spid = tgt.get("spid") if tgt is not None else "?"
        nm, tx = shapes.get(spid, ("?",""))
        if ntype == "clickEffect":
            step += 1
        label = NODETYPE.get(ntype, f"({ntype})" if ntype else "")
        if pcls == "entr": eff = ENTR.get(pid, f"entr#{pid}")
        elif pcls == "emph": eff = EMPH.get(pid, f"emph#{pid}")
        elif pcls == "exit": eff = EXIT.get(pid, f"exit#{pid}") + "(離場)"
        else: eff = f"{pcls}#{pid}"
        sub = ctn.get("presetSubtype")
        found += 1
        lines.append(f"  第{step}擊 {label} {CLASSNAME.get(pcls,pcls)}:{eff}"
                     f"{' 方向'+sub if sub and sub!='0' else ''}"
                     f"  → [{spid}] {nm} 「{tx}」")
    if not found:
        lines.append("(timing 存在但無效果節點)")

open(out_path, "w", encoding="utf-8").write("\n".join(lines))
print(f"OK -> {out_path}")
