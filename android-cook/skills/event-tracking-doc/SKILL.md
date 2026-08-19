---
name: event-tracking-doc
description: >
  Thống kê event tracking (Firebase/Databuckets) của một feature ra file .xlsx/.csv
  đúng format sheet mẫu của team — copy cả style, độ rộng cột, merge ô, chiều cao dòng.
  Đọc code Kotlin tìm chỗ bắn event thật, đối chiếu sheet gốc, đánh dấu chỗ còn thiếu.
  Đọc được .xlsx không cần cài openpyxl/pandas.
when_to_use: >
  Dùng khi user nói "thống kê event", "làm file event", "tạo sheet event tracking",
  "liệt kê event cho feature X", "bổ sung event vào sheet", hoặc đưa một file sheet
  event mẫu. KHÔNG dùng để thêm code bắn event mới (đó là task implement thường),
  hay để phân tích số liệu đã thu thập.
allowed-tools: Read Grep Glob Bash(python3 *) Write
---

# Event tracking doc

Sinh file thống kê event của một feature, đúng format sheet mẫu của team
(một dòng = một giá trị của một param). Mẫu `.xlsx` → xuất `.xlsx` kèm style;
mẫu `.csv` → xuất `.csv`.

## Đường dẫn script

Các lệnh dưới dùng `${CLAUDE_SKILL_DIR}` = thư mục chứa SKILL.md này. Nếu shell in ra
`/scripts/...` (biến rỗng, không expand) thì tự xác định lại một lần rồi dùng suốt phiên:

```bash
S=$(dirname "$(find ~/.claude "${CLAUDE_PROJECT_DIR:-.}/.claude" -name build_event_xlsx.py -path '*event-tracking-doc*' 2>/dev/null | head -1)")
echo "$S"    # .../event-tracking-doc/scripts
```

Các script tự tìm file cạnh nó (`templates/`, module khác), nên gọi từ thư mục nào cũng được.

## Quy trình

### 1. Tìm sheet mẫu (nếu có)

Sheet mẫu là nguồn chân lý về format và về những event/value **đã có**. Tìm theo thứ tự:

1. File user đang mở / vừa nhắc tới.
2. `docs/event-tracking/*.csv` trong repo.
3. `~/Downloads/*Event tracking*.csv`.

Đọc header + vài dòng đầu để xác nhận đúng 17 cột. Chi tiết từng cột: [references/csv-format.md](references/csv-format.md).

Sheet mẫu là `.xlsx` chứ không phải `.csv` → đọc bằng script kèm theo. Script chỉ dùng
thư viện chuẩn Python (`zipfile` + `xml.etree`), không cần cài `openpyxl`/`pandas`:

```bash
S=${CLAUDE_SKILL_DIR}/scripts/xlsx2csv.py
python3 $S file.xlsx --list                              # xem có những sheet nào
python3 $S file.xlsx --sheet "Event tracking" -o /tmp/sheet.csv
python3 $S file.xlsx --unmerge                           # điền giá trị ô merge ra toàn vùng
```

Sheet event hay merge ô ở cột Event Name / Param Name. Mặc định script giữ nguyên kiểu
merge (giá trị ở ô trên cùng, ô dưới để trống) — khớp với format cần sinh ra. Chỉ dùng
`--unmerge` khi cần đọc hiểu nội dung, đừng dùng khi đối chiếu format.

### 1b. Dự án mới, chưa từng có sheet mẫu

Khởi tạo từ template có sẵn thay vì dựng tay:

```bash
T=${CLAUDE_SKILL_DIR}/templates/starter.spec.json
cp $T docs/event-tracking/<ten-du-an>.spec.json
```

Template có sẵn: user properties (`is_iap_user`, `current_screen`, `ab_test_variant`),
3 event nền (`screen_show`, `button_click`, `overlay_show`) với đúng câu Trigger chuẩn, và
sheet IAP Tracking. Các ô để `TODO` / `btn_todo` / `dialog_todo` là chỗ phải điền bằng giá
trị **grep được từ code** ở bước 2 — không được giao file còn nguyên TODO.

Không có workbook mẫu thì bỏ `style_source`; script dùng bảng màu mặc định đã theo chuẩn
team (header `#0B5394`, cột QA `#38761D`, section `#3D85C6`, body viền đủ 4 cạnh). Khai
`"style": {"qa_from": <chỉ số cột QA đầu tiên>}` để nhóm cột QA tự đổi sang xanh lá.

Khi dự án đã có workbook chuẩn, thêm `style_source` + `style.source_sheet` vào spec rồi
build lại — nội dung giữ nguyên, chỉ style đổi.

### 2. Quét code tìm chỗ bắn event

Đừng đoán tên event từ tên feature. Grep thật:

```bash
grep -rn "pushEvent\|Event(eventName\|remoteOnClickSingle\|remoteClickableSingle\|RemoteOverlayScreen\|RemoteScreen(" --include=*.kt app/src/main
```

Với mỗi feature, gom đủ 4 nhóm:

| Nhóm | Tìm ở đâu |
| :--- | :--- |
| Event tự định nghĩa | file `*Analytics.kt`, enum tên event, `pushEvent(Event(eventName = ...))` |
| `button_click` | `buttonName = "btn_..."` trong `remoteOnClickSingle` / `remoteClickableSingle` |
| `overlay_show` / `screen_show` | `overlayName = ` / `screenName = ` truyền vào `RemoteOverlayScreen` / `RemoteScreen` |
| `iap_*` / `ad_*` | giá trị `placement` mới truyền vào `pushEventIap*` hoặc route paywall |

Với mỗi event lấy: tên event, **toàn bộ** param + giá trị có thể có, màn/overlay nó bắn ở đâu,
và hằng số Kotlin sinh ra giá trị đó (ghi vào cột Note để QA truy ngược được).

### 3. Đối chiếu và ghi nhận gap

So tập event tìm được trong code với sheet mẫu. Ghi rõ 3 loại:

- **Có trong code, chưa có trong sheet** → thêm vào file mới, cột `Trạng thái gắn (dev)` = `TRUE`.
- **Có trong sheet, không thấy trong code** → nêu trong phần tóm tắt cho user, đừng im lặng bỏ qua.
- **Đáng lẽ phải có nhưng code chưa bắn** (ví dụ: một nút không đi qua `remoteOnClickSingle`,
  hoặc một luồng có event ở feature A mà feature B tương đương lại thiếu) → cho vào một
  section riêng tên `GAP / ĐỀ XUẤT BỔ SUNG (chưa gắn trong code)`, `Trạng thái gắn (dev)` = `FALSE`,
  cột Note ghi `file:line` cần sửa.

Không trộn event đề xuất vào section event thật.

### 4. Sinh file output

Viết một file JSON spec rồi chạy script — đừng ghép CSV/XML bằng tay (dấu phẩy, xuống dòng
trong ô, dấu ngoặc kép rất dễ hỏng).

**Sheet mẫu là `.xlsx` → xuất `.xlsx`** (khớp schema từng sheet, paste thẳng vào workbook
gốc được, và không dính lỗi encoding tiếng Việt khi mở bằng Excel):

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build_event_xlsx.py \
  spec.json "docs/event-tracking/<Tên app> - Event tracking - <Feature>.xlsx" \
  --csv-dir docs/event-tracking/csv
```

**Sheet mẫu là `.csv` → xuất `.csv`** (một sheet, cố định 17 cột):

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build_event_csv.py spec.json "…/<Feature>.csv"
```

**KHÔNG chép tay `header` vào spec.** Mỗi sheet chỉ khai `"schema": "<tên>"`; header, `map`,
độ rộng cột lấy từ schema. Chép tay lệch một cột là cả file sai chỗ mà nhìn mắt không ra.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build_event_xlsx.py --list-schemas
```

Skill có sẵn 3 layout chuẩn của team: `event_tracking` (17 cột), `iap_tracking` (15 cột,
cột 0 header rỗng), `iaa_tracking` (có cột KPI nên các cột sau lệch 1).

**Workbook của app không khớp layout nào → HỌC từ chính nó, đừng khai tay:**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/learn_schema.py "wb.xlsx" \
  -o docs/event-tracking/schemas.json --prefix myapp_
```

Script đọc header, suy ra cột nào chứa gì (khớp tên cột sau khi bỏ dấu, nên "Param/ Property
Name" hay "param property name" đều nhận), tìm cột QA, đọc độ rộng cột và style id. Sheet
nào thiếu vai trò bắt buộc (`event` / `param` / `values` / `dev`) nó cảnh báo `⚠` — chỗ đó
phải khai `map` tay.

Rồi trỏ spec tới file vừa học: `"schemas_file": "docs/event-tracking/schemas.json"`.
Đặc thù của app nằm trong repo app, **không** thêm vào `templates/schemas.json` của skill.

Khai cả `schema` lẫn `header` thì script bắt buộc hai bên phải khớp, lệch là báo lỗi và dừng.

Chỉ tạo sheet cho phần thực sự có nội dung mới. Feature chạm vào IAP thì mới thêm sheet IAP
Tracking; ad SDK tự bắn (`ad_request`, `ad_impression_db`, …) thì không đụng sheet IAA.

**Copy style của sheet mẫu**: khai `style_source` (workbook mẫu) + `style.source_sheet`.
Script copy nguyên `styles.xml` + theme, **tự dò** style id của header/body/section từ chính
sheet mẫu, kèm độ rộng cột, freeze pane, ẩn gridline và merge ô theo block — không hardcode
màu của app nào. Dò sai thì khai đè `"style": {"body_xf": N, "section_xf": [A, B]}`; xem id
nào là màu gì bằng `scripts/dump_styles.py`.

Schema `spec.json` đầy đủ: [references/csv-format.md](references/csv-format.md).

Giữ lại file `spec.json` cạnh output trong repo — sửa spec rồi chạy lại, đừng sửa tay file
output rồi để hai bên lệch nhau.

**Chiều cao dòng**: Excel KHÔNG auto-fit ô merge dọc, mà sheet gốc lại không ghi `ht`.
Script tự tính và ghi `ht` cho mọi dòng — đừng bỏ bước verify "0 ô bị cắt chữ" ở
[references/csv-format.md](references/csv-format.md), nếu không user phải kéo tay từng dòng.

### 5. Verify trước khi báo xong

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/verify_xlsx.py "<file vừa tạo>.xlsx" \
  --compare "<workbook mẫu>.xlsx" \
  --sheet-map "Event tracking=Event tracking,IAP Tracking=IAP Tracking"
```

Kiểm 3 thứ mắt thường không thấy: XML well-formed, merge không chồng nhau, không ô nào bị
cắt chữ — cộng so header với workbook gốc. Exit code 1 nếu có vấn đề. Xuất `.csv` thì kiểm
số cột bằng `csv.reader` là đủ.

Rồi báo lại cho user: bao nhiêu event mới, gap nào tìm được, file nằm ở đâu.

## Nguyên tắc nội dung

- **Giá trị phải copy từ code**, không tự đặt lại cho "đẹp". Sai một ký tự là dashboard hụt số.
- Cột `Value Definition/ Note` viết bằng tiếng Việt, mô tả **hành vi user**, không mô tả code.
- Cột `Note` (cột cuối) dành cho dev/QA: tên hằng số Kotlin, `file:line`, cảnh báo đặc thù
  (ví dụ event kỹ thuật bắn tự động chứ không do user bấm → phải loại khỏi báo cáo đếm click).
- Param chỉ xuất hiện ở một số value của event (ví dụ `overlay_name` chỉ có với button nằm
  trong popup) → nói rõ điều đó ở cột `Value Definition/ Note`, đừng để người đọc tự suy.
- Nếu feature có A/B test / nhiều kịch bản remote config, thêm section
  `REMOTE CONFIG KEY LIÊN QUAN` ở cuối để người đọc số liệu biết đang so cái gì với cái gì.
- Cột `Status`, `Actual Result`, `Log iOS` để trống — QA điền sau khi test.
