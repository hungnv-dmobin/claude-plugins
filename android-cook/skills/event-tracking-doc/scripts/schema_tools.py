#!/usr/bin/env python3
"""Suy ra schema (map cột + style id) từ một workbook mẫu bất kỳ.

Đây là "rule chuẩn" để skill dùng được cho mọi app: thay vì hardcode cột nào chứa gì
và style id nào là header/body, ta ĐỌC từ chính workbook mẫu của app đó.
"""
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NSR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Tên cột -> vai trò. So khớp sau khi bỏ dấu, bỏ khoảng trắng thừa, hạ chữ thường,
# nên "Param/ Property Name" và "param property name" là một.
ROLE_ALIASES = {
    "event":         ["event name", "ten event"],
    "display":       ["event display name", "display name"],
    "kpi":           ["kpi"],
    "definition":    ["event definition", "dinh nghia"],
    "trigger":       ["trigger", "dieu kien trigger"],
    "param":         ["param property name", "param name", "property name", "parameter name"],
    "param_display": ["param property display name", "param display name"],
    "param_defi":    ["param property definition", "param definition"],
    "values":        ["values", "value", "gia tri"],
    "value_note":    ["value definition note", "value definition", "value note"],
    "dtype":         ["data type", "kieu du lieu"],
    "ptype":         ["param property type", "param type", "property type"],
    "dev":           ["trang thai gan dev", "trang thai gan", "dev status"],
    "note":          ["note", "ghi chu"],
}
# Cột do QA điền — đánh dấu để tô màu khác, không phải vai trò dữ liệu
QA_ALIASES = ["status", "actual result", "log ios", "trang thai test ios qa tester",
              "trang thai test ios", "ket qua thuc te", "ver"]


def norm(s):
    """Bỏ dấu tiếng Việt, bỏ ký tự lạ, gộp khoảng trắng, hạ chữ thường."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-zA-Z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def infer_map(header):
    """header -> {vai trò: chỉ số cột}. Cột đầu trống nhưng chứa event name cũng bắt được."""
    normed = [norm(h) for h in header]
    m = {}
    for role, aliases in ROLE_ALIASES.items():
        for i, h in enumerate(normed):
            if not h:
                continue
            if h in aliases or any(h.startswith(a) for a in aliases):
                if role not in m:
                    m[role] = i
                break
    # Sheet IAP: cột 0 header RỖNG nhưng vẫn là cột Event Name
    if "event" not in m and header and not str(header[0]).strip():
        m["event"] = 0
    return m


def infer_qa_from(header):
    """Chỉ số cột QA đầu tiên (Status / Actual Result / Log iOS ...)."""
    normed = [norm(h) for h in header]
    hits = [i for i, h in enumerate(normed)
            if h and any(h == a or h.startswith(a) for a in QA_ALIASES)]
    return min(hits) if hits else None


# ------------------------------------------------------------------ đọc workbook
def sheet_paths(z):
    rels = {}
    for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
        t = rel.get("Target").lstrip("/")
        rels[rel.get("Id")] = t if t.startswith("xl/") else "xl/" + t
    return {sh.get("name"): rels.get(sh.get(f"{NSR}id"))
            for sh in ET.fromstring(z.read("xl/workbook.xml")).find(f"{NS}sheets")}


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def row_styles(sheet_xml, rownum):
    m = re.search(rf'<row r="{rownum}"[^>]*>(.*?)</row>', sheet_xml, re.S)
    if not m:
        return {}
    return {col_index(a): int(s)
            for a, s in re.findall(rf'<c r="([A-Z]+){rownum}" s="(\d+)"', m.group(1))}


def sheet_grid(z, path, shared):
    """Dùng lại bộ parse đã kiểm chứng của xlsx2csv thay vì viết regex mới."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from xlsx2csv import read_sheet as _read
    return _read(z, path, shared)


def row_texts(grid, rownum):
    """rownum 1-based -> {chỉ số cột: text} (chỉ ô có chữ)."""
    if rownum - 1 >= len(grid):
        return {}
    return {i: v for i, v in enumerate(grid[rownum - 1]) if str(v).strip()}


def shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{NS}t")) for si in root.findall(f"{NS}si")]


def detect_styles(sheet_xml, grid, ncol, map_):
    """Đoán body_xf và section_xf từ chính sheet mẫu.

    - body_xf : style xuất hiện nhiều nhất ở cột Values trong các dòng dữ liệu
    - section_xf: dòng nào CHỈ có cột 0 có chữ -> đó là dòng section
    """
    rows = [int(r) for r in re.findall(r'<row r="(\d+)"', sheet_xml)]
    vcol = map_.get("values", 7)

    counts = {}
    section = None
    for r in rows[1:60]:
        texts = row_texts(grid, r)
        styles = row_styles(sheet_xml, r)
        if not texts:
            continue
        if set(texts) == {0} and section is None and r > 1:
            section = [styles.get(0), styles.get(1)]
            continue
        if vcol in texts and vcol in styles:
            counts[styles[vcol]] = counts.get(styles[vcol], 0) + 1

    body = max(counts, key=counts.get) if counts else None
    if section and all(x is not None for x in section):
        pass
    else:
        section = None
    return body, section


def learn(path, sheet_name):
    """-> dict schema cho một sheet của workbook mẫu."""
    z = zipfile.ZipFile(path)
    paths = sheet_paths(z)
    if sheet_name not in paths:
        raise SystemExit(f"Workbook không có sheet {sheet_name!r}. Có: {list(paths)}")
    x = z.read(paths[sheet_name]).decode("utf-8")
    shared = shared_strings(z)
    grid = sheet_grid(z, paths[sheet_name], shared)

    header = [str(c) for c in (grid[0] if grid else [])]
    while header and not header[-1].strip():
        header.pop()
    ncol = len(header)

    m = infer_map(header)
    qa = infer_qa_from(header)
    hstyles = row_styles(x, 1)
    body, section = detect_styles(x, grid, ncol, m)

    widths = [12.63] * ncol
    cm = re.search(r"<cols>.*?</cols>", x, re.S)
    if cm:
        for mn, mx, v in re.findall(r'<col[^>]*min="(\d+)"[^>]*max="(\d+)"[^>]*width="([\d.]+)"', cm.group(0)):
            for i in range(int(mn) - 1, min(int(mx), ncol)):
                widths[i] = float(v)

    sc = {"sheet_name": sheet_name, "header": header, "map": m, "widths": widths}
    if qa is not None:
        sc["qa_from"] = qa
    style = {"source_sheet": sheet_name}
    if body is not None:
        style["body_xf"] = body
    if section:
        style["section_xf"] = section
    sc["style"] = style
    sc["_header_xf"] = [hstyles.get(i, 0) for i in range(ncol)]
    return sc
