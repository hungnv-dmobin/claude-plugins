#!/usr/bin/env python3
"""Giải mã style của một workbook .xlsx để biết chọn body_xf / section_xf nào.

In ra từng cellXf (font, đậm, màu chữ, màu nền, viền, canh lề) và style id mà từng
dòng đầu của sheet đang dùng — để khai vào spec thay vì đoán màu.

Usage:
  dump_styles.py workbook.xlsx                 # tất cả style + sheet đầu
  dump_styles.py workbook.xlsx --sheet "Event tracking" --rows 6
  dump_styles.py workbook.xlsx --only 1,15,24  # chỉ xem vài id
"""
import argparse
import re
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NSR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--sheet", help="tên sheet muốn xem style theo dòng")
    ap.add_argument("--rows", type=int, default=4, help="xem bao nhiêu dòng đầu (mặc định 4)")
    ap.add_argument("--only", help="chỉ in các style id này, ngăn bằng dấu phẩy")
    a = ap.parse_args()

    z = zipfile.ZipFile(a.xlsx)
    r = ET.fromstring(z.read("xl/styles.xml"))
    fonts, fills = r.find(f"{NS}fonts"), r.find(f"{NS}fills")
    borders, xfs = r.find(f"{NS}borders"), r.find(f"{NS}cellXfs")

    want = {int(x) for x in a.only.split(",")} if a.only else None
    print(f"cellXfs={len(xfs)} fonts={len(fonts)} fills={len(fills)} borders={len(borders)}\n")

    for i, xf in enumerate(xfs):
        if want and i not in want:
            continue
        f = fonts[int(xf.get("fontId") or 0)]
        name = f.find(f"{NS}name")
        sz = f.find(f"{NS}sz")
        col = f.find(f"{NS}color")
        p = fills[int(xf.get("fillId") or 0)].find(f"{NS}patternFill")
        fg = p.find(f"{NS}fgColor") if p is not None else None
        b = borders[int(xf.get("borderId") or 0)]
        sides = [s for s in ("left", "right", "top", "bottom")
                 if b.find(f"{NS}{s}") is not None and b.find(f"{NS}{s}").get("style")]
        al = xf.find(f"{NS}alignment")
        alt = " ".join(f"{k}={v}" for k, v in (al.attrib.items() if al is not None else []))
        print(f"xf{i:>3} | {name.get('val') if name is not None else '?':<10}"
              f" {sz.get('val') if sz is not None else '':<5}"
              f" {'BOLD' if f.find(f'{NS}b') is not None else '    '}"
              f" chữ={col.get('rgb') if col is not None and col.get('rgb') else '-':<10}"
              f" | nền={fg.get('rgb') if fg is not None and fg.get('rgb') else 'none':<10}"
              f" | viền={','.join(sides) or 'none':<22} | {alt}")

    # style id theo dòng
    rels = {}
    for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
        t = rel.get("Target").lstrip("/")
        rels[rel.get("Id")] = t if t.startswith("xl/") else "xl/" + t
    sheets = {sh.get("name"): rels.get(sh.get(f"{NSR}id"))
              for sh in ET.fromstring(z.read("xl/workbook.xml")).find(f"{NS}sheets")}

    target = a.sheet or next(iter(sheets))
    if target not in sheets:
        print(f"\nKhông có sheet {target!r}. Có: {list(sheets)}")
        return
    x = z.read(sheets[target]).decode("utf-8")
    print(f"\n--- style id theo dòng, sheet {target!r} ---")
    for n in range(1, a.rows + 1):
        m = re.search(rf'<row r="{n}"[^>]*>(.*?)</row>', x, re.S)
        if not m:
            continue
        cells = re.findall(r'<c r="([A-Z]+)\d+" s="(\d+)"', m.group(1))
        print(f"  dòng {n}: {[(c, s) for c, s in cells[:14]]}")


if __name__ == "__main__":
    main()
