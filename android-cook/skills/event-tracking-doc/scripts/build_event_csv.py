#!/usr/bin/env python3
"""Sinh CSV event tracking (17 cột) từ file JSON spec.

Usage: build_event_csv.py <spec.json> <output.csv>
Schema của spec.json: xem references/csv-format.md
"""
import csv
import json
import os
import sys

HEADER = [
    "Event Name", "Event Display Name", "Event Definition", "Trigger",
    "Param/ Property Name", "Param/ Property Display Name", "Param/ Property Definition",
    "Values", "Value Definition/ Note", "Data Type", "Param/ Property Type",
    "Trạng thái gắn (dev)", "Status", "Actual Result", "", "Log iOS", "Note",
]
NCOL = len(HEADER)


def build_rows(spec):
    rows = []
    for block in spec["blocks"]:
        if "section" in block:
            rows.append([block["section"]] + [""] * (NCOL - 1))
            continue

        first_event_row = True
        for param in block.get("params", []):
            first_param_row = True
            for value in param["values"]:
                # [Values, Value Definition/Note, Trạng thái gắn, Note]
                value = list(value) + [""] * (4 - len(value))
                r = [""] * NCOL
                if first_event_row:
                    r[0] = block.get("event", "")
                    r[1] = block.get("display", "")
                    r[2] = block.get("definition", "")
                    r[3] = block.get("trigger", "")
                    first_event_row = False
                if first_param_row:
                    r[4] = param.get("name", "")
                    r[5] = param.get("display", "")
                    r[6] = param.get("defi", "")
                    first_param_row = False
                r[7], r[8] = value[0], value[1]
                r[9] = param.get("dtype", "String")
                r[10] = param.get("ptype", "Parameter")
                r[11] = value[2]
                r[16] = value[3]
                rows.append(r)
    return rows


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec_path, out_path = sys.argv[1], sys.argv[2]

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    rows = build_rows(spec)
    bad = [i for i, r in enumerate(rows) if len(r) != NCOL]
    if bad:
        sys.exit(f"Lỗi: dòng {bad} lệch cột")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if spec.get("output_header", True):
            w.writerow(HEADER)
        w.writerows(rows)

    print(f"OK: {out_path} — {len(rows)} dòng dữ liệu")


if __name__ == "__main__":
    main()
