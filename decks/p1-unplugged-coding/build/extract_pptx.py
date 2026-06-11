#!/usr/bin/env python3
"""把 .pptx 的文字（依正確頁序）萃取成 UTF-8 檔，並抽出 png/jpeg 媒體。零外部套件。"""
import sys, os, zipfile, re
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

src = sys.argv[1]
outdir = sys.argv[2]
os.makedirs(outdir, exist_ok=True)
mediadir = os.path.join(outdir, "media")
os.makedirs(mediadir, exist_ok=True)

z = zipfile.ZipFile(src)
names = z.namelist()

pres = ET.fromstring(z.read("ppt/presentation.xml"))
rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
rid_to_target = {rel.get("Id"): rel.get("Target") for rel in rels}
ordered = []
sldlst = pres.find("p:sldIdLst", NS)
if sldlst is not None:
    for sld in sldlst.findall("p:sldId", NS):
        tgt = rid_to_target.get(sld.get(RID), "")
        ordered.append("ppt/" + tgt.lstrip("/").replace("../", ""))
if not ordered:
    ordered = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                     key=lambda x: int(re.search(r"(\d+)", x).group()))

def slide_text(xml_bytes):
    root = ET.fromstring(xml_bytes)
    lines = []
    for sp in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}p"):
        runs = [t.text for t in sp.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t") if t.text]
        line = "".join(runs).strip()
        if line:
            lines.append(line)
    return lines

out = []
for i, slide_path in enumerate(ordered, 1):
    if slide_path not in names:
        continue
    out.append(f"\n===== 投影片 {i} =====")
    lines = slide_text(z.read(slide_path))
    out.extend(lines if lines else ["(本頁無文字，可能是純圖)"])

txt_path = os.path.join(outdir, "content.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

# 抽出 png/jpeg 媒體（wdp/svg 跳過）
extracted = []
for m in sorted(names):
    if m.startswith("ppt/media/") and m.lower().endswith((".png", ".jpeg", ".jpg")):
        data = z.read(m)
        fn = os.path.basename(m)
        with open(os.path.join(mediadir, fn), "wb") as f:
            f.write(data)
        extracted.append((fn, len(data)))

print(f"頁數={len(ordered)}")
print(f"文字檔 -> {txt_path}")
print(f"抽出媒體 {len(extracted)} 個 -> {mediadir}")
for fn, sz in sorted(extracted, key=lambda x: -x[1]):
    print(f"  {fn:16} {sz:>9,} bytes")
