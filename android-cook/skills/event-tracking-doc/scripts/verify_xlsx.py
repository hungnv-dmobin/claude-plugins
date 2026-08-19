#!/usr/bin/env python3
"""Kiểm tra file .xlsx vừa sinh trước khi giao cho user.

Ba lỗi hay gặp mà mắt thường không thấy:
  1. Part XML không well-formed  -> Excel báo file hỏng
  2. Vùng merge chồng nhau       -> Excel báo file hỏng
  3. Ô bị cắt chữ                -> user phải kéo tay từng dòng (Excel KHÔNG
                                     auto-fit chiều cao ô đã merge dọc)

Usage:
  verify_xlsx.py out.xlsx [--compare goc.xlsx --sheet-map "Sheet cua toi=Sheet goc,..."]

Exit code 0 = đạt, 1 = có lỗi.
"""
import argparse
import csv
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_event_xlsx import parse_widths, wrap_lines, LINE_H, PAD_H  # noqa: E402

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(x):
    """-> (heights, grid, merges, ncol, cols_xml)"""
    heights, grid = {}, {}
    for rm in re.finditer(r'<row r="(\d+)"(?: ht="([\d.]+)")?[^>]*>(.*?)</row>', x, re.S):
        r = int(rm.group(1))
        heights[r] = float(rm.group(2)) if rm.group(2) else 15.75
        for cm in re.finditer(
            r'<c r="([A-Z]+)(\d+)"[^>]*?(?:/>|><is><t[^>]*>(.*?)</t></is></c>)', rm.group(3), re.S
        ):
            txt = (cm.group(3) or "")
            txt = txt.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            grid[(r, col_index(cm.group(1)))] = txt
    merges = {}
    for a, r1, r2 in re.findall(r'<mergeCell ref="([A-Z]+)(\d+):[A-Z]+(\d+)"', x):
        merges[(int(r1), col_index(a))] = (int(r1), int(r2))
    hdr = re.search(r'<row r="1".*?</row>', x, re.S)
    ncol = len(re.findall(r'<c r="[A-Z]+1"', hdr.group(0))) if hdr else 0
    cm = re.search(r"<cols>.*?</cols>", x, re.S)
    return heights, grid, merges, ncol, (cm.group(0) if cm else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--compare", help="workbook gốc để so header")
    ap.add_argument("--sheet-map", help='"Sheet cua toi=Sheet goc,Sheet2=Sheet goc 2"')
    a = ap.parse_args()

    z = zipfile.ZipFile(a.xlsx)
    fails = []

    # 1. XML well-formed + zip
    bad = z.testzip()
    if bad:
        fails.append(f"zip hỏng ở {bad}")
    for n in z.namelist():
        if n.endswith((".xml", ".rels")):
            try:
                ET.fromstring(z.read(n))
            except Exception as e:
                fails.append(f"XML lỗi: {n} — {e}")
    print(f"[1/3] XML + zip: {'OK' if not fails else 'LỖI'}")

    sheet_parts = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    for part in sheet_parts:
        x = z.read(part).decode("utf-8")
        heights, grid, merges, ncol, cols_xml = read_sheet(x)
        W = parse_widths(cols_xml, ncol) if ncol else []

        # 2. merge chồng nhau
        seen, overlap = set(), []
        for (r1, c), (_, r2) in merges.items():
            cells = {(r, c) for r in range(r1, r2 + 1)}
            if cells & seen:
                overlap.append(f"{part} cột {c} dòng {r1}-{r2}")
            seen |= cells

        # 3. ô bị cắt chữ
        clipped = []
        for (r, c), txt in grid.items():
            if not txt or c >= len(W):
                continue
            need = wrap_lines(txt, max(4, int(W[c]) - 1)) * LINE_H + PAD_H
            if (r, c) in merges:
                r1, r2 = merges[(r, c)]
                avail = sum(heights.get(i, 15.75) for i in range(r1, r2 + 1))
            elif any(k[1] == c and v[0] <= r <= v[1] and k[0] != r for k, v in merges.items()):
                continue
            else:
                avail = heights.get(r, 15.75)
            if need > avail + 0.5:
                clipped.append(f"{part} ô ({r},{c}) cần {need:.0f}pt có {avail:.0f}pt: {txt[:40]}")

        name = part.rsplit("/", 1)[-1]
        print(f"      {name}: {len(heights)} dòng x {ncol} cột, {len(merges)} merge"
              f" | chồng: {len(overlap)} | cắt chữ: {len(clipped)}")
        fails += overlap + clipped

    print(f"[2/3] Merge chồng nhau: {'OK' if not any('cột' in f for f in fails) else 'LỖI'}")
    print(f"[3/3] Ô bị cắt chữ: {'OK' if not any('cắt chữ' in f or 'cần' in f for f in fails) else 'LỖI'}")

    # so header với workbook gốc
    if a.compare and a.sheet_map:
        from xlsx2csv import list_sheets, read_shared_strings, read_sheet as rs
        zg = zipfile.ZipFile(a.compare)
        gsheets = dict(list_sheets(zg))
        shared = read_shared_strings(zg)
        mine = dict(list_sheets(z))
        for pair in a.sheet_map.split(","):
            mn, gn = pair.split("=", 1)
            mn, gn = mn.strip(), gn.strip()
            if gn not in gsheets:
                fails.append(f"workbook gốc không có sheet {gn!r}")
                continue
            hg = rs(zg, gsheets[gn], shared)[0]
            hm = rs(z, mine[mn], read_shared_strings(z))[0]
            while hg and not str(hg[-1]).strip():
                hg.pop()
            while hm and not str(hm[-1]).strip():
                hm.pop()
            same = hm == hg
            print(f"      header {mn!r} vs {gn!r}: {'KHỚP' if same else 'LỆCH'} ({len(hm)} cột)")
            if not same:
                for i, (p, q) in enumerate(zip(hm, hg)):
                    if p != q:
                        fails.append(f"header lệch cột {i}: {p!r} != {q!r}")

    print()
    if fails:
        print(f"❌ {len(fails)} vấn đề:")
        for f in fails[:15]:
            print("   -", f)
        sys.exit(1)
    print("✅ Đạt — file sẵn sàng giao")


if __name__ == "__main__":
    main()
