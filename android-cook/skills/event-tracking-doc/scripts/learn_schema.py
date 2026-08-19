#!/usr/bin/env python3
"""Học schema từ workbook mẫu của BẤT KỲ app nào.

Đọc header của từng sheet, suy ra cột nào chứa gì (event/param/values/...), cột QA
bắt đầu từ đâu, độ rộng cột, và style id dùng cho header/body/section. Xuất ra JSON
để dùng làm `schema` trong spec.

Usage:
  learn_schema.py wb.xlsx                      # học tất cả sheet, in ra stdout
  learn_schema.py wb.xlsx --sheet "Event tracking"
  learn_schema.py wb.xlsx -o docs/event-tracking/schemas.json
  learn_schema.py wb.xlsx -o schemas.json --merge      # gộp vào file có sẵn
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema_tools import learn, sheet_paths  # noqa: E402


def slug(name):
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "sheet"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--sheet", action="append", help="chỉ học sheet này (lặp lại được)")
    ap.add_argument("-o", "--out", help="ghi ra file JSON")
    ap.add_argument("--merge", action="store_true", help="gộp vào file -o đã có")
    ap.add_argument("--prefix", default="", help="tiền tố cho key schema")
    a = ap.parse_args()

    z = zipfile.ZipFile(a.xlsx)
    names = a.sheet or list(sheet_paths(z))

    out = {}
    if a.merge and a.out and os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as f:
            out = json.load(f)

    for n in names:
        sc = learn(a.xlsx, n)
        hxf = sc.pop("_header_xf", None)
        key = a.prefix + slug(n)
        missing = [r for r in ("event", "param", "values", "dev") if r not in sc["map"]]
        sc["_mo_ta"] = (f"Học từ {os.path.basename(a.xlsx)} — sheet {n!r}, {len(sc['header'])} cột"
                        + (f". THIẾU vai trò: {missing} — kiểm tra lại header." if missing else ""))
        out[key] = sc
        star = "  ⚠ " if missing else "  ✓ "
        print(f"{star}{key:<28} {len(sc['header']):>2} cột | map {len(sc['map'])} vai trò"
              f" | qa_from={sc.get('qa_from')} | style={sc['style']}", file=sys.stderr)
        if missing:
            print(f"      thiếu: {missing} — header có thể đặt tên lạ, khai 'map' tay trong spec",
                  file=sys.stderr)
        if hxf:
            print(f"      header_xf: {hxf}", file=sys.stderr)

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\n-> {a.out} ({len(out)} schema)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
