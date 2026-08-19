#!/usr/bin/env python3
"""Sinh file .xlsx nhiều sheet từ JSON spec — chỉ dùng thư viện chuẩn Python.

Mỗi sheet khai header + "map" riêng nên một output có thể khớp nhiều schema khác nhau
trong cùng workbook gốc (Event tracking 17 cột, IAP Tracking 15 cột, ...).

Nếu spec khai "style_source" (đường dẫn workbook mẫu), script copy nguyên xl/styles.xml
+ theme, rồi tái dùng đúng style id mà sheet mẫu đang dùng cho header/body/section, kèm
độ rộng cột, freeze pane và merge ô — nên output nhìn giống hệt sheet gốc.

Usage:
  build_event_xlsx.py spec.json out.xlsx [--csv-dir DIR]
"""
import argparse
import csv
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS, NSR = "{%s}" % MAIN, "{%s}" % RELNS

DEFAULT_MAP = {
    "event": 0, "display": 1, "definition": 2, "trigger": 3,
    "param": 4, "param_display": 5, "param_defi": 6,
    "values": 7, "value_note": 8, "dtype": 9, "ptype": 10,
    "dev": 11, "note": 16,
}
# cột được merge theo block event / theo block param
EVENT_KEYS = ("event", "display", "definition", "trigger", "kpi")
PARAM_KEYS = ("param", "param_display", "param_defi")

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def esc(s):
    return _ILLEGAL.sub("", str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def col_letter(i):
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


# ----------------------------------------------------------------- style source
class StyleSource:
    """Đọc style/cols/sheetView từ workbook mẫu."""

    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.styles = self.z.read("xl/styles.xml").decode("utf-8")
        self.theme = None
        for n in self.z.namelist():
            if n.startswith("xl/theme/"):
                self.theme = self.z.read(n).decode("utf-8")
                break
        rels = {}
        for rel in ET.fromstring(self.z.read("xl/_rels/workbook.xml.rels")):
            t = rel.get("Target").lstrip("/")
            rels[rel.get("Id")] = t if t.startswith("xl/") else "xl/" + t
        self.sheets = {
            sh.get("name"): rels.get(sh.get(f"{NSR}id"))
            for sh in ET.fromstring(self.z.read("xl/workbook.xml")).find(f"{NS}sheets")
        }

    def sheet_xml(self, name):
        return self.z.read(self.sheets[name]).decode("utf-8")

    def part(self, name, tag):
        x = self.sheet_xml(name)
        m = re.search(rf"<{tag}[ >].*?</{tag}>|<{tag}[^>]*/>", x, re.S)
        return m.group(0) if m else ""

    def header_styles(self, name):
        """style id của từng cột ở dòng 1."""
        x = self.sheet_xml(name)
        m = re.search(r'<row r="1"[^>]*>(.*?)</row>', x, re.S)
        if not m:
            return []
        out = {}
        for ref, s in re.findall(r'<c r="([A-Z]+)1"(?: s="(\d+)")?', m.group(1)):
            n = 0
            for ch in ref:
                n = n * 26 + ord(ch) - 64
            out[n - 1] = int(s) if s else 0
        return [out.get(i, 0) for i in range(max(out) + 1)] if out else []


# ----------------------------------------------------------------- schema
SCHEMAS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "templates", "schemas.json")


def load_schemas(extra_path=None):
    """Schema chung của skill + schema riêng của dự án (nếu có) đè lên.

    Nhờ vậy đặc thù của từng app nằm trong repo app đó, không lẫn vào skill.
    """
    out = {}
    for path in (SCHEMAS_PATH, extra_path):
        if not path:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                out.update(json.load(f))
        except FileNotFoundError:
            if path is extra_path:
                raise SystemExit(f"Không đọc được schemas_file: {path}")
    return out


def apply_schema(sheet, schemas):
    """Điền header/map/widths/style/name từ schema chuẩn; key khai tay trong spec thì ưu tiên.

    Nếu spec vừa khai "schema" vừa khai "header" thì hai bên PHẢI khớp — lệch là lỗi,
    vì header lệch một cột là cả file sai chỗ mà nhìn mắt không ra.
    """
    key = sheet.get("schema")
    if not key:
        if "header" not in sheet:
            raise SystemExit("Sheet thiếu cả 'schema' lẫn 'header' — phải có một trong hai")
        return sheet

    if key not in schemas or not isinstance(schemas.get(key), dict):
        avail = sorted(k for k, v in schemas.items()
                       if not k.startswith("_") and isinstance(v, dict))
        raise SystemExit(f"Không có schema {key!r}. Có: {avail}")
    sc = schemas[key]

    if "header" in sheet and sheet["header"] != sc["header"]:
        diff = [f"    cột {i}: spec={a!r} != schema={b!r}"
                for i, (a, b) in enumerate(zip(sheet["header"], sc["header"])) if a != b]
        if len(sheet["header"]) != len(sc["header"]):
            diff.append(f"    số cột: spec={len(sheet['header'])} != schema={len(sc['header'])}")
        raise SystemExit(f"Header của sheet {sheet.get('name', key)!r} lệch schema {key!r}:\n"
                         + "\n".join(diff)
                         + "\n  -> bỏ 'header' khỏi spec để dùng schema, hoặc sửa cho khớp")

    out = dict(sheet)
    out.setdefault("name", sc["sheet_name"])
    out["header"] = sc["header"]
    out.setdefault("map", sc.get("map", {}))
    out.setdefault("widths", sc.get("widths"))
    st = dict(sc.get("style", {}))
    st.setdefault("qa_from", sc.get("qa_from"))
    st.update(sheet.get("style", {}))          # style khai tay đè lên schema
    out["style"] = st
    return out


def validate_sheet(sheet):
    """Bắt các lỗi spec mà mắt không thấy nhưng làm file sai âm thầm."""
    errs = []
    m = effective_map(sheet)
    ncol = len(sheet["header"])
    name = sheet.get("name", "?")

    for k, i in m.items():
        if i >= ncol:
            errs.append(f"[{name}] map[{k}]={i} vượt quá {ncol} cột")

    for bi, b in enumerate(sheet.get("blocks", [])):
        if "section" in b:
            continue
        if not b.get("params"):
            errs.append(f"[{name}] block #{bi} ({b.get('event', '?')}) không có params nào")
        for p in b.get("params", []):
            if not p.get("values"):
                errs.append(f"[{name}] param {p.get('name', '?')!r} không có values nào")
            for v in p.get("values", []):
                if not isinstance(v, (list, tuple)) or len(v) < 2:
                    errs.append(f"[{name}] value {v!r} phải là [Values, Note, dev, Note dev]")
                    continue
                note = (list(v) + ["", "", ""])[3]
                if note and "note" not in m:
                    errs.append(f"[{name}] value {v[0]!r} có ghi chú dev nhưng sheet này KHÔNG"
                                " có cột Note -> ghi chú sẽ mất. Gộp vào 'Value Definition/"
                                " Note' hoặc khai map['note'].")
                dev = (list(v) + ["", ""])[2]
                if dev not in ("TRUE", "FALSE", ""):
                    errs.append(f"[{name}] 'Trạng thái gắn' của {v[0]!r} = {dev!r},"
                                " phải là TRUE / FALSE / rỗng")
    if errs:
        raise SystemExit("Spec sai:\n  " + "\n  ".join(errs))


# ----------------------------------------------------------------- flatten
def effective_map(sheet):
    """Sheet khai 'map' (từ schema hoặc tay) thì dùng nguyên — KHÔNG trộn DEFAULT_MAP.

    Trộn vào sẽ kéo theo vai trò mà sheet đó không có (ví dụ sheet IAP không có cột Note),
    trỏ nhầm sang cột của QA.
    """
    return dict(sheet["map"]) if sheet.get("map") else dict(DEFAULT_MAP)


def blocks_to_rows(sheet):
    """Trải blocks thành ma trận ô + danh sách vùng merge (theo chỉ số dòng dữ liệu, 0-based)."""
    m = effective_map(sheet)
    ncol = len(sheet["header"])
    rows, merges, sections = [], [], []

    for b in sheet["blocks"]:
        if "section" in b:
            r = [""] * ncol
            r[0] = b["section"]
            sections.append(len(rows))
            rows.append(r)
            continue

        block_start = len(rows)
        first_event = True
        for p in b.get("params", []):
            param_start = len(rows)
            first_param = True
            for v in p["values"]:
                v = list(v) + [""] * (4 - len(v))
                r = [""] * ncol

                def put(key, val):
                    i = m.get(key)
                    if i is not None and i < ncol and val:
                        r[i] = val

                if first_event:
                    for k in EVENT_KEYS:
                        put(k, b.get(k, ""))
                    first_event = False
                if first_param:
                    put("param", p.get("name", ""))
                    put("param_display", p.get("display", ""))
                    put("param_defi", p.get("defi", ""))
                    first_param = False
                put("values", v[0])
                put("value_note", v[1])
                put("dtype", p.get("dtype", "String"))
                put("ptype", p.get("ptype", "Parameter"))
                put("dev", v[2])
                put("note", v[3])
                rows.append(r)

            if len(rows) - param_start > 1:
                for k in PARAM_KEYS:
                    i = m.get(k)
                    if i is not None and i < ncol:
                        merges.append((param_start, len(rows) - 1, i))

        if len(rows) - block_start > 1:
            for k in EVENT_KEYS:
                i = m.get(k)
                if i is not None and i < ncol:
                    merges.append((block_start, len(rows) - 1, i))

    return rows, merges, sections


# ----------------------------------------------------------------- row height
LINE_H = 12.75      # chiều cao 1 dòng chữ Arial 10
PAD_H = 3.0         # đệm trên/dưới trong ô
MIN_H = 15.75       # defaultRowHeight của workbook mẫu
MAX_H = 409.0       # trần của Excel


def parse_widths(cols_xml, ncol):
    """Đọc độ rộng từng cột từ <cols>; cột không khai thì lấy default."""
    w = [12.63] * ncol
    for mn, mx, val in re.findall(r'<col[^>]*min="(\d+)"[^>]*max="(\d+)"[^>]*width="([\d.]+)"', cols_xml):
        for i in range(int(mn) - 1, min(int(mx), ncol)):
            w[i] = float(val)
    return w


def wrap_lines(text, cpl):
    """Đếm số dòng sau khi wrap theo từ, giống cách Excel xuống dòng."""
    if not text:
        return 1
    total = 0
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            total += 1
            continue
        n, cur = 1, 0
        for word in para.split(" "):
            wl = len(word)
            if cur == 0:
                cur = wl
            elif cur + 1 + wl <= cpl:
                cur += 1 + wl
            else:
                n += 1
                cur = wl
            while cur > cpl:          # từ dài hơn cả cột thì tự cắt
                cur -= cpl
                n += 1
        total += n
    return max(1, total)


def compute_row_heights(header, rows, merges, widths):
    """Ô merge dọc KHÔNG được Excel auto-fit -> phải tự tính ht cho từng dòng."""
    grid = [header] + rows
    nrow, ncol = len(grid), len(header)
    cpl = [max(4, int(w) - 1) for w in widths] + [10] * ncol

    def cell_h(txt, ci):
        return wrap_lines(txt, cpl[ci]) * LINE_H + PAD_H

    heights = [MIN_H] * nrow
    merged_cells = set()
    for r1, r2, c in merges:
        for r in range(r1 + 1, r2 + 2):       # +1 vì merges tính theo dòng dữ liệu
            merged_cells.add((r, c))

    # ô thường: dòng phải đủ cao cho ô cao nhất
    for ri, row in enumerate(grid):
        for ci in range(ncol):
            txt = row[ci] if ci < len(row) else ""
            if txt and (ri, ci) not in merged_cells:
                heights[ri] = max(heights[ri], cell_h(txt, ci))

    # ô merge dọc: tổng chiều cao cả vùng phải đủ, chia đều phần thiếu
    for r1, r2, c in merges:
        span = list(range(r1 + 1, r2 + 2))
        txt = grid[span[0]][c] if c < len(grid[span[0]]) else ""
        if not txt:
            continue
        need = cell_h(txt, c)
        cur = sum(heights[r] for r in span)
        if need > cur:
            extra = (need - cur) / len(span)
            for r in span:
                heights[r] += extra

    return [round(min(h, MAX_H), 2) for h in heights]


# ----------------------------------------------------------------- sheet xml
def render_sheet(header, rows, merges, sections, st):
    widths = parse_widths(st["cols"], len(header))
    heights = compute_row_heights(header, rows, merges, widths)
    hdr_xf = st["header_xf"]
    body_xf, sec_a, sec_rest = st["body_xf"], st["section_xf"][0], st["section_xf"][1]
    ncol = len(header)

    def xf_for(ri, ci):
        if ri == 0:
            return hdr_xf[ci] if ci < len(hdr_xf) else (hdr_xf[-1] if hdr_xf else 0)
        if (ri - 1) in sections:
            return sec_a if ci == 0 else sec_rest
        return body_xf

    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           f'<worksheet xmlns="{MAIN}">', st["sheetPr"], st["sheetView"],
           '<sheetFormatPr customHeight="1" defaultColWidth="12.63" defaultRowHeight="15.75"/>',
           st["cols"],
           "<sheetData>"]

    for ri, row in enumerate([header] + rows):
        cells = []
        for ci in range(ncol):
            val = row[ci] if ci < len(row) else ""
            s = xf_for(ri, ci)
            ref = f"{col_letter(ci)}{ri + 1}"
            if val == "":
                cells.append(f'<c r="{ref}" s="{s}"/>')
            else:
                cells.append(f'<c r="{ref}" s="{s}" t="inlineStr">'
                             f'<is><t xml:space="preserve">{esc(val)}</t></is></c>')
        out.append(f'<row r="{ri + 1}" ht="{heights[ri]}" customHeight="1">'
                   f'{"".join(cells)}</row>')
    out.append("</sheetData>")

    if merges:
        mc = "".join(
            f'<mergeCell ref="{col_letter(c)}{r1 + 2}:{col_letter(c)}{r2 + 2}"/>'
            for r1, r2, c in merges
        )
        out.append(f'<mergeCells count="{len(merges)}">{mc}</mergeCells>')

    out.append("</worksheet>")
    return "".join(out)


# ----------------------------------------------------------------- fallback style
FALLBACK_STYLES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{MAIN}">
<fonts count="2">
<font><sz val="10"/><name val="Arial"/></font>
<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>
</fonts>
<fills count="5">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF0B5394"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF38761D"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF3D85C6"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border>
<left style="thin"><color rgb="FF999999"/></left><right style="thin"><color rgb="FF999999"/></right>
<top style="thin"><color rgb="FF999999"/></top><bottom style="thin"><color rgb="FF999999"/></bottom>
<diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
</cellXfs>
</styleSheet>'''

# style mặc định khi KHÔNG có workbook mẫu (bảng màu chuẩn của team):
#   1 = header xanh đậm · 3 = header cột QA xanh lá · 2 = ô dữ liệu
#   4/5 = dòng section xanh nhạt (cột A đậm / các cột còn lại)
FALLBACK_XF = {"header": 1, "header_qa": 3, "body": 2, "section": [4, 5]}


def resolve_style(sheet, src):
    st = sheet.get("style", {})
    src_name = st.get("source_sheet")
    widths = sheet.get("widths")
    ncol = len(sheet["header"])

    if src and src_name and src_name in src.sheets:
        # Không khai body_xf/section_xf thì DÒ từ chính sheet mẫu, thay vì hardcode
        # style id của một app cụ thể vào skill.
        if "body_xf" not in st or "section_xf" not in st:
            try:
                import schema_tools
                x = src.sheet_xml(src_name)
                grid = schema_tools.sheet_grid(src.z, src.sheets[src_name],
                                               schema_tools.shared_strings(src.z))
                m = effective_map(sheet)
                body, section = schema_tools.detect_styles(x, grid, ncol, m)
                if "body_xf" not in st and body is not None:
                    st = dict(st); st["body_xf"] = body
                if "section_xf" not in st and section:
                    st = dict(st); st["section_xf"] = section
            except Exception:
                pass
        cols = src.part(src_name, "cols")
        # cắt bớt cột thừa so với header của mình
        cols = re.sub(r'<col [^>]*min="(\d+)"[^>]*/>',
                      lambda m: m.group(0) if int(m.group(1)) <= ncol else "", cols)
        hdr = src.header_styles(src_name)[:ncol] or [1] * ncol
        if len(hdr) < ncol:
            hdr += [hdr[-1]] * (ncol - len(hdr))
        return {
            "sheetPr": src.part(src_name, "sheetPr"),
            "sheetView": src.part(src_name, "sheetView"),
            "cols": cols,
            "header_xf": st.get("header_xf", hdr),
            "body_xf": st.get("body_xf", 24),
            "section_xf": st.get("section_xf", [15, 16]),
        }

    w = widths or [20] * ncol
    cols = "<cols>" + "".join(
        f'<col customWidth="1" min="{i}" max="{i}" width="{v}"/>' for i, v in enumerate(w, 1)
    ) + "</cols>"
    # Không có workbook mẫu -> style id của schema (24, 15, 60...) KHÔNG tồn tại trong
    # FALLBACK_STYLES (chỉ có 0-5). Phải bỏ qua, nếu không Excel báo file hỏng.
    n_fallback_xf = 6

    def safe(v, default):
        if isinstance(v, list):
            return v if all(isinstance(i, int) and i < n_fallback_xf for i in v) else default
        return v if isinstance(v, int) and v < n_fallback_xf else default

    # qa_from = chỉ số cột đầu tiên của khối cột QA (Status, Actual Result, Log iOS, Note)
    qa = st.get("qa_from")
    default_hdr = [
        FALLBACK_XF["header_qa"] if (qa is not None and i >= qa) else FALLBACK_XF["header"]
        for i in range(ncol)
    ]
    return {
        "sheetPr": "",
        "sheetView": '<sheetViews><sheetView showGridLines="0" workbookViewId="0">'
                     '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                     '</sheetView></sheetViews>',
        "cols": cols,
        "header_xf": safe(st.get("header_xf"), default_hdr) or default_hdr,
        "body_xf": safe(st.get("body_xf"), FALLBACK_XF["body"]),
        "section_xf": safe(st.get("section_xf"), FALLBACK_XF["section"]),
    }


# ----------------------------------------------------------------- build
def build(spec, out_path):
    schemas = load_schemas(spec.get("schemas_file"))
    sheets = [apply_schema(sh, schemas) for sh in spec["sheets"]]
    for sh in sheets:
        validate_sheet(sh)
    src = StyleSource(spec["style_source"]) if spec.get("style_source") else None
    styles_xml = src.styles if src else FALLBACK_STYLES
    theme_xml = src.theme if src else None

    n = len(sheets)
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          f'<workbook xmlns="{MAIN}" xmlns:r="{RELNS}"><sheets>'
          + "".join(f'<sheet name="{esc(s["name"])}" sheetId="{i}" r:id="rId{i}"/>'
                    for i, s in enumerate(sheets, 1))
          + "</sheets></workbook>")

    rel = "".join(f'<Relationship Id="rId{i}" Type="{RELNS}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                  for i in range(1, n + 1))
    rel += f'<Relationship Id="rId{n+1}" Type="{RELNS}/styles" Target="styles.xml"/>'
    if theme_xml:
        rel += f'<Relationship Id="rId{n+2}" Type="{RELNS}/theme" Target="theme/theme1.xml"/>'
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               f'{rel}</Relationships>')

    ov = "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                 for i in range(1, n + 1))
    if theme_xml:
        ov += '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          f'{ov}</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 f'<Relationship Id="rId1" Type="{RELNS}/officeDocument" Target="xl/workbook.xml"/></Relationships>')

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    all_rows, stats = {}, {}
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles_xml)
        if theme_xml:
            z.writestr("xl/theme/theme1.xml", theme_xml)
        for i, s in enumerate(sheets, 1):
            rows, merges, sections = blocks_to_rows(s)
            st = resolve_style(s, src)
            all_rows[s["name"]] = [s["header"]] + rows
            stats[s["name"]] = (len(rows), len(merges), st["header_xf"][:3], st["body_xf"])
            z.writestr(f"xl/worksheets/sheet{i}.xml",
                       render_sheet(s["header"], rows, merges, sections, st))
    return all_rows, stats, bool(src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--csv-dir")
    ap.add_argument("--list-schemas", action="store_true", help="liệt kê schema có sẵn rồi thoát")
    a = ap.parse_args()

    if a.list_schemas:
        for k, v in load_schemas().items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            print(f"{k:<18} {len(v['header']):>2} cột | sheet {v['sheet_name']!r}")
            print(f"{'':<18}    {v.get('_mo_ta', '')}")
        return

    if not a.spec or not a.out:
        raise SystemExit("Cần: build_event_xlsx.py spec.json out.xlsx")
    spec = json.load(open(a.spec, encoding="utf-8"))
    all_rows, stats, styled = build(spec, a.out)

    total = sum(len(v) - 1 for v in all_rows.values())
    print(f"OK: {a.out} — {len(all_rows)} sheet, {total} dòng"
          f" | style: {'copy từ workbook mẫu' if styled else 'mặc định'}")
    for name, rows in all_rows.items():
        nrow, nmerge, hxf, bxf = stats[name]
        print(f"   • {name}: {nrow} dòng x {len(rows[0])} cột, {nmerge} vùng merge, "
              f"header xf={hxf}…, body xf={bxf}")

    if a.csv_dir:
        os.makedirs(a.csv_dir, exist_ok=True)
        for name, rows in all_rows.items():
            p = os.path.join(a.csv_dir, re.sub(r"[^\w\-. ]", "_", name) + ".csv")
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerows(rows)
            print(f"   CSV: {p}")


if __name__ == "__main__":
    main()
