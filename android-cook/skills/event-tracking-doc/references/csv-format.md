# Format sheet Event tracking

## 17 cột

| # | Tên cột | Ai điền | Nội dung |
| :- | :--- | :--- | :--- |
| 0 | `Event Name` | Dev | Tên event snake_case. Chỉ điền ở **dòng đầu** của block event. Nhiều event dùng chung một bộ param có thể gộp, ngăn bằng xuống dòng. |
| 1 | `Event Display Name` | Dev | Tên hiển thị Title Case. Chỉ dòng đầu block. |
| 2 | `Event Definition` | Dev | Một câu: event này nghĩa là gì với user. Chỉ dòng đầu block. |
| 3 | `Trigger` | Dev | Bullet `- ` bắt đầu bằng "Trigger khi…", thêm bullet "Không trigger khi…" nếu dễ nhầm. Chỉ dòng đầu block. |
| 4 | `Param/ Property Name` | Dev | Tên param. Chỉ điền ở **dòng đầu** của block param. |
| 5 | `Param/ Property Display Name` | Dev | Tên hiển thị. Chỉ dòng đầu block param. |
| 6 | `Param/ Property Definition` | Dev | Param này mô tả gì. Chỉ dòng đầu block param. |
| 7 | `Values` | Dev | **Một giá trị mỗi dòng.** Giá trị động dùng `{uuid}`, `{tên các màn}`. Enum ngăn bằng ` \| `. |
| 8 | `Value Definition/ Note` | Dev | Giá trị này nghĩa là gì, xét từ góc nhìn user. Tiếng Việt. |
| 9 | `Data Type` | Dev | `String` / `Number` / `Boolean` |
| 10 | `Param/ Property Type` | Dev | `Parameter` (gắn với event) / `Property` (user property) |
| 11 | `Trạng thái gắn (dev)` | Dev | `TRUE` = đã gắn trong code, `FALSE` = đề xuất/chưa gắn |
| 12 | `Status` | QA | `Pass` / `Fail` — để trống khi bàn giao |
| 13 | `Actual Result` | QA | Log Android dán vào |
| 14 | *(không tên)* | QA | Status iOS |
| 15 | `Log iOS` | QA | Log iOS dán vào |
| 16 | `Note` | Dev | Hằng số Kotlin, `file:line`, cảnh báo cho người đọc số liệu |

## Quy tắc dòng

Một dòng = **một giá trị của một param**. Ô nào lặp lại so với dòng trên thì để trống —
sheet đọc theo kiểu merge cell.

```
button_click | Button click | User bấm… | - Trigger khi… | button_name | Button name | Tên button | btn_a | Click A | String | Parameter | TRUE
             |              |           |                |             |             |            | btn_b | Click B | String | Parameter | TRUE
             |              |           |                | screen_name | Screen name | Ở màn nào  | home  | Màn Home| String | Parameter | TRUE
```

Dòng section (tiêu đề nhóm) chỉ có cột 0, 16 cột còn lại rỗng.

## Event nền của template (đừng định nghĩa lại)

Ba event này đã có sẵn trong mọi sheet. Feature mới chỉ **thêm giá trị**
cho `screen_name` / `button_name` / `overlay_name`, không tạo event mới.

- `screen_show` — Trigger: `- Trigger khi user đến một màn nào đó\n\n- Chỉ cần trigger với những màn quan trọng/ cần theo dõi\n\n- Không trigger với những màn đã được biểu diễn bằng event khác (ví dụ iap_show, ad_impression)`
- `button_click` — Trigger: `- Trigger khi user bấm một button\n\n- Chỉ cần trigger với những button quan trọng/ cần theo dõi\n\n- Không trigger với những hành vi click button đã được biểu diễn bằng event khác (ví dụ screen_go, iap_click, ad_click)`
- `overlay_show` — Trigger: `- Trigger khi dialog/ popup/... được show ra\n\n- Chỉ cần trigger với những overlay quan trọng/ cần theo dõi\n\n- Không trigger với những overlay đã được biểu diễn bằng event khác (ví dụ iap_show, ad_impression)`

Bộ `iap_show` / `iap_close` / `iap_click` / `iap_purchase` / `iap_error_show` cũng đã có —
feature mới thường chỉ thêm giá trị cho param `placement`.

## Schema `spec.json`

```jsonc
{
  "output_header": true,
  "blocks": [
    { "section": "TÊN SECTION" },
    {
      "event": "button_click",
      "display": "Button click",
      "definition": "User bấm vào một button",
      "trigger": "- Trigger khi user bấm một button\n\n- Chỉ cần trigger với…",
      "params": [
        {
          "name": "button_name",
          "display": "Button name",
          "defi": "Tên của button mà user bấm",
          "dtype": "String",          // mặc định "String"
          "ptype": "Parameter",       // mặc định "Parameter"
          "values": [
            ["btn_abc", "Click nút ABC ở màn Home", "TRUE", "AbcWidget.kt:63"],
            ["btn_xyz", "Click nút XYZ trong popup", "TRUE", "XYZ_BUTTON_NAME"]
          ]
        }
      ]
    }
  ]
}
```

Mỗi phần tử `values` là `[Values, Value Definition/ Note, Trạng thái gắn (dev), Note]`.

## Đặt tên file

`<Mã dự án> <Tên app> - Event tracking - <Feature>.csv`, đặt trong `docs/event-tracking/`.

Ví dụ: `[A00_001] MyApp - Event tracking - Feature ABC.csv`

## Schema spec cho `build_event_xlsx.py` (nhiều sheet)

Bọc thêm một lớp `sheets`, mỗi sheet khai `header` + `map` riêng. `blocks` giống hệt schema
một-sheet ở trên.

```jsonc
{
  "style_source": "/duong/dan/workbook-mau.xlsx",   // optional — copy style thật
  "sheets": [
    {
      "schema": "event_tracking",   // header + map + widths + style lấy từ templates/schemas.json
      "blocks": [ /* … */ ]
    },
    {
      "schema": "iap_tracking",     // cột 0 header RỖNG nhưng vẫn chứa event name — schema lo hết
      "blocks": [ /* … */ ]
    }
  ]
}
```

`map` mặc định (khớp sheet Event tracking 17 cột):

```
event 0 · display 1 · definition 2 · trigger 3 · param 4 · param_display 5 · param_defi 6
values 7 · value_note 8 · dtype 9 · ptype 10 · dev 11 · note 16
```

Sheet có cột `KPI` (IAA Tracking, Zoom-Camera-Event-Tracking) thì thêm `"kpi": <index>` vào
`map` và `kpi` vào block; các key khác dịch index theo.

Key nào không có trong `map` thì bỏ qua — dùng để cắt cột không tồn tại ở sheet đó.

## Đọc lại file đã tạo để verify

`build_event_xlsx.py` không tự kiểm tra output. Luôn đọc ngược bằng `xlsx2csv.py` rồi so
header với workbook gốc:

```bash
S=${CLAUDE_SKILL_DIR}/scripts
python3 $S/xlsx2csv.py out.xlsx --list                 # đúng số sheet & tên sheet chưa
python3 $S/xlsx2csv.py out.xlsx --sheet 1 -o /tmp/a.csv
python3 $S/xlsx2csv.py "goc.xlsx" --sheet "Event tracking" -o /tmp/b.csv
head -1 /tmp/a.csv; head -1 /tmp/b.csv                 # header phải trùng
```

## Rule chung: workbook nhiều sheet, đừng trộn nhau

Workbook event của một app thường có nhiều sheet **không đồng nhất**. Trước khi viết spec,
phân loại từng sheet:

| Loại sheet | Nhận biết | Xử lý |
| :--- | :--- | :--- |
| Sheet event chính | có `screen_show` / `button_click` / `overlay_show` | thêm giá trị mới vào đây |
| Sheet IAP | có `iap_show` / `iap_close` / `iap_purchase` | chỉ thêm `placement` mới |
| Sheet IAA / Ads | có `ad_request` / `ad_impression`, cột `Trạng thái gắn` toàn FALSE | ad SDK tự bắn — **không đụng** |
| Sheet nền tảng khác | cùng app nhưng vocabulary khác hẳn | **không trộn** vào sheet đang làm |

**Phân biệt sheet Android vs iOS trong cùng workbook** — bẫy hay gặp nhất:

- Cột `Actual Result` chứa logcat (`com.xxx.yyy  D  pushEvent:`) → sheet Android
- Note nhắc tên kiểu Swift (`SomeKind.rawValue`, `SomeView`, `SomeViewModel.setup()`) → sheet iOS
- Android hay có tiền tố `btn_` / `dialog_`, iOS thường không

Hai nền tảng đặt tên khác nhau cho **cùng một hành vi** (`btn_shutter_photo` vs
`capture_photo`, `onboarding 1` vs `onboard_1`). Trộn vào nhau là dashboard đếm sai. User
muốn hai bên chung dashboard thì đó là việc team phải thống nhất — nêu ra, đừng tự gộp.

Xác định sheet của mình bằng cách so quy ước đặt tên trong sheet với **tên hằng số thật
trong code** đang làm.

## Copy style từ workbook mẫu

Thêm `style_source` ở cấp cao nhất + `style.source_sheet` cho từng sheet. Script sẽ copy
nguyên `xl/styles.xml` + `xl/theme/theme1.xml` từ workbook mẫu, rồi tái dùng đúng style id
mà sheet mẫu đang dùng — kèm độ rộng cột, freeze pane, ẩn gridline, và tự sinh merge ô.

```jsonc
{
  "style_source": "/duong/dan/workbook-mau.xlsx",
  "sheets": [{
    "name": "Event tracking",
    "header": [ /* … */ ],
    "style": {
      "source_sheet": "Event tracking",  // lấy cols/sheetView/style header từ sheet này
      "body_xf": 24,                     // style id dùng cho ô dữ liệu
      "section_xf": [15, 16]             // [cột A, các cột còn lại] của dòng section
    },
    "blocks": [ /* … */ ]
  }]
}
```

`header_xf` tự đọc từ dòng 1 của sheet mẫu, không cần khai. Muốn ép thì thêm
`"header_xf": [1,1,1,…]` (một id mỗi cột).

**Chọn `body_xf` / `section_xf` bằng cách giải mã styles.xml của workbook mẫu**, đừng đoán:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/dump_styles.py "workbook-mau.xlsx" --sheet "Event tracking"
```

In ra từng cellXf (font, đậm, màu chữ, màu nền, viền, canh lề) kèm style id mà 4 dòng đầu
của sheet đang dùng. Dòng 1 = header, dòng section thường có nền khác, dòng dữ liệu đầu tiên
cho biết `body_xf`. Thêm `--only 1,15,24` để xem vài id, `--rows 8` để xem nhiều dòng hơn.

### Style id — DÒ, đừng hardcode

Style id (`body_xf`, `section_xf`) khác nhau giữa các workbook nên **không** ghi cứng vào
skill. Có `style_source` thì `build_event_xlsx.py` tự dò từ chính sheet mẫu:

- `body_xf` = style xuất hiện nhiều nhất ở cột `Values` trong các dòng dữ liệu
- `section_xf` = style của dòng mà **chỉ cột 0 có chữ** (dòng tiêu đề nhóm)
- `header_xf` = style của từng cột ở dòng 1

Dò sai (workbook lạ) thì khai đè: `"style": {"body_xf": 24, "section_xf": [15, 16]}`.
Xem id nào là màu gì bằng `dump_styles.py`.

### Merge ô

Script tự merge theo cấu trúc block: cột `event/display/definition/trigger/kpi` merge suốt
một block event, cột `param/param_display/param_defi` merge suốt một block param. Vùng chỉ
một dòng thì không merge.

**Luôn chạy `scripts/verify_xlsx.py` trước khi giao file** — merge chồng nhau làm Excel báo file hỏng.

## Chiều cao dòng — BẮT BUỘC tự tính khi có merge

**Excel không auto-fit chiều cao cho ô đã merge dọc.** Sheet gốc export từ Google Sheets
không ghi `ht` (Google tự co khi render), nên nếu chỉ copy style mà không set `ht` thì mở
bằng Excel sẽ thấy chữ trong ô merge bị cắt cụt — user phải kéo tay từng dòng.

`build_event_xlsx.py` tự xử lý: mô phỏng word-wrap theo độ rộng cột thật, tính số dòng chữ,
rồi ghi `ht=... customHeight="1"` cho mọi dòng. Với vùng merge dọc, phần chiều cao còn thiếu
được chia đều cho các dòng trong vùng (chứ không dồn hết vào dòng đầu).

Hằng số: `LINE_H = 12.75` (Arial 10), `PAD_H = 3.0`, `MIN_H = 15.75` (= `defaultRowHeight`
của workbook mẫu), `MAX_H = 409` (trần Excel).

### Verify

Một lệnh kiểm cả ba lỗi (XML hỏng, merge chồng, ô cắt chữ), exit code 1 nếu có vấn đề:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/verify_xlsx.py out.xlsx \
  --compare "workbook-goc.xlsx" \
  --sheet-map "Event tracking=Event tracking,IAP Tracking=IAP Tracking"
```

`--compare` + `--sheet-map` là tuỳ chọn, dùng để so header với workbook gốc.

## Dự án mới — không có workbook mẫu

`templates/starter.spec.json` là spec khởi tạo: user properties + `screen_show` +
`button_click` + `overlay_show` + sheet IAP Tracking, câu Trigger đã viết chuẩn.

```bash
cp ${CLAUDE_SKILL_DIR}/templates/starter.spec.json docs/event-tracking/app.spec.json
# điền TODO bằng giá trị grep từ code, rồi:
python3 ${CLAUDE_SKILL_DIR}/scripts/build_event_xlsx.py \
  docs/event-tracking/app.spec.json "docs/event-tracking/<App> - Event tracking.xlsx"
```

Bỏ `style_source` → dùng bảng màu mặc định (đã theo chuẩn team):

| xf | Dùng cho | Màu |
| :- | :--- | :--- |
| `1` | Header thường | `#0B5394` bold trắng |
| `3` | Header cột QA | `#38761D` bold trắng |
| `2` | Ô dữ liệu | không nền, viền 4 cạnh, wrap |
| `4` / `5` | Dòng section (cột A / còn lại) | `#3D85C6` |

Khai `"style": {"qa_from": 12}` để cột từ index 12 trở đi dùng header xanh lá. Muốn kiểm
soát từng cột thì khai thẳng `"header_xf": [1,1,…,3,3]`.

Khi có workbook chuẩn rồi, thêm `style_source` + `style.source_sheet` và build lại — nội
dung không đổi, chỉ style đổi.


## Schema chuẩn — nguồn chân lý duy nhất

`templates/schemas.json` giữ header / `map` / độ rộng cột / style id của từng loại sheet,
**trích thẳng từ workbook gốc** chứ không gõ tay. Spec chỉ khai `"schema": "<tên>"`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build_event_xlsx.py --list-schemas
```

| Schema | Cột | Sheet |
| :--- | :-- | :--- |
| `event_tracking` | 17 | Event tracking (Android) |
| `iap_tracking` | 15 | IAP Tracking — cột 0 header rỗng |
| `iaa_tracking` | 15 | IAA Tracking — có cột KPI, ad SDK tự bắn |
| `zoom_camera_ios` | 14 | Zoom-Camera-Event-Tracking (iOS) |

### Thêm schema cho workbook mới

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/xlsx2csv.py wb.xlsx --list          # tên các sheet
python3 ${CLAUDE_SKILL_DIR}/scripts/xlsx2csv.py wb.xlsx --sheet 1 | head -1   # header
python3 ${CLAUDE_SKILL_DIR}/scripts/dump_styles.py wb.xlsx --sheet "..."      # style id
```

Rồi thêm một entry vào `schemas.json`: `sheet_name`, `header` (copy y nguyên, kể cả ô rỗng),
`map`, `widths`, `qa_from`, `style`.

### Script tự bắt các lỗi này

| Lỗi | Thông báo |
| :--- | :--- |
| `header` khai tay lệch schema | liệt kê từng cột lệch, dừng |
| `schema` không tồn tại | in danh sách schema có sẵn |
| `map[key]` vượt số cột | báo key nào, cột nào |
| block không có `params` | báo block nào |
| param không có `values` | báo param nào |
| `Trạng thái gắn` khác TRUE/FALSE/rỗng | báo giá trị nào sai |

Exit code 1 khi spec sai. Style id của schema (24, 60, 15…) chỉ dùng khi có `style_source`;
không có thì script tự lùi về bảng màu mặc định thay vì trỏ tới id không tồn tại.
