#!/usr/bin/env python3
"""Đọc file .xlsx bằng thư viện chuẩn Python — không cần cài openpyxl/pandas.

.xlsx là file zip chứa XML, nên chỉ cần zipfile + xml.etree.

Usage:
  xlsx2csv.py <file.xlsx> --list              # liệt kê tên các sheet
  xlsx2csv.py <file.xlsx>                     # in sheet đầu ra stdout (CSV)
  xlsx2csv.py <file.xlsx> --sheet "Tên sheet" # chọn sheet theo tên hoặc số thứ tự (1-based)
  xlsx2csv.py <file.xlsx> -o out.csv          # ghi ra file
  xlsx2csv.py <file.xlsx> --unmerge           # điền giá trị ô merge xuống mọi ô trong vùng
"""
import argparse
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def col_to_index(ref):
    """A1 -> 0, B2 -> 1, AA10 -> 26"""
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def read_shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall(f"{NS}si"):
        # <si><t>x</t></si> hoặc <si><r><t>a</t></r><r><t>b</t></r></si> (rich text)
        out.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    return out


def list_sheets(z):
    """[(tên sheet, đường dẫn xml)] theo đúng thứ tự trong workbook."""
    rels = {}
    root = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for rel in root:
        target = rel.get("Target").lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        rels[rel.get("Id")] = target

    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = []
    for sh in wb.find(f"{NS}sheets"):
        sheets.append((sh.get("name"), rels.get(sh.get(f"{NS_R}id"))))
    return sheets


def read_sheet(z, path, shared, unmerge=False):
    root = ET.fromstring(z.read(path))
    grid = {}
    max_col = -1

    for row in root.iter(f"{NS}row"):
        r = int(row.get("r")) - 1
        for c in row.findall(f"{NS}c"):
            ref = c.get("r")
            ci = col_to_index(ref) if ref else 0
            ctype = c.get("t")

            if ctype == "inlineStr":
                is_el = c.find(f"{NS}is")
                val = "".join(t.text or "" for t in is_el.iter(f"{NS}t")) if is_el is not None else ""
            else:
                v = c.find(f"{NS}v")
                raw = v.text if v is not None and v.text is not None else ""
                if ctype == "s":
                    val = shared[int(raw)] if raw != "" else ""
                elif ctype == "b":
                    val = "TRUE" if raw == "1" else "FALSE"
                else:
                    val = raw

            grid[(r, ci)] = val
            max_col = max(max_col, ci)

    if unmerge:
        merges = root.find(f"{NS}mergeCells")
        if merges is not None:
            for mc in merges.findall(f"{NS}mergeCell"):
                a, b = mc.get("ref").split(":")
                r1, c1 = int(re.search(r"\d+", a).group()) - 1, col_to_index(a)
                r2, c2 = int(re.search(r"\d+", b).group()) - 1, col_to_index(b)
                val = grid.get((r1, c1), "")
                for r in range(r1, r2 + 1):
                    for c in range(c1, c2 + 1):
                        grid[(r, c)] = val
                        max_col = max(max_col, c)

    if not grid:
        return []
    max_row = max(r for r, _ in grid)
    return [[grid.get((r, c), "") for c in range(max_col + 1)] for r in range(max_row + 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--sheet", help="tên sheet hoặc số thứ tự 1-based (mặc định: sheet đầu)")
    ap.add_argument("--list", action="store_true", help="chỉ liệt kê tên sheet")
    ap.add_argument("--unmerge", action="store_true", help="điền giá trị ô merge ra toàn vùng")
    ap.add_argument("-o", "--out", help="ghi ra file CSV (mặc định: stdout)")
    a = ap.parse_args()

    with zipfile.ZipFile(a.xlsx) as z:
        sheets = list_sheets(z)
        if a.list:
            for i, (name, _) in enumerate(sheets, 1):
                print(f"{i}. {name}")
            return

        path = sheets[0][1]
        if a.sheet:
            if a.sheet.isdigit():
                path = sheets[int(a.sheet) - 1][1]
            else:
                match = [p for n, p in sheets if n == a.sheet]
                if not match:
                    sys.exit(f"Khong tim thay sheet {a.sheet!r}. Co: {[n for n, _ in sheets]}")
                path = match[0]

        rows = read_sheet(z, path, read_shared_strings(z), a.unmerge)

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        print(f"OK: {a.out} — {len(rows)} dòng", file=sys.stderr)
    else:
        csv.writer(sys.stdout).writerows(rows)


if __name__ == "__main__":
    main()
