---
description: Khởi tạo và điều phối team agents (leader/coder/reviewer/tester/doc-writer) để xử lý một yêu cầu
---

Khởi tạo và điều phối một **team agents phát triển phần mềm** để xử lý yêu cầu của user.

## Thành viên team

| Agent | File | Vai trò |
|-------|------|---------|
| leader | `~/.claude/agents/leader.md` | Lập kế hoạch, phân công, điều phối |
| coder | `~/.claude/agents/coder.md` | Viết/sửa code |
| reviewer | `~/.claude/agents/reviewer.md` | Review code |
| tester | `~/.claude/agents/tester.md` | Viết/chạy test (tùy task) |
| doc-writer | `~/.claude/agents/doc-writer.md` | Cập nhật tài liệu (tùy task) |

## Cách khởi tạo team

1. Nếu môi trường Claude Code có sẵn công cụ **Agent Teams** (`TeamsCreate`): tạo team tên `dev_team` với các teammate trên; các teammate trao đổi với nhau qua `SendMessage`, KHÔNG tự tạo subagent rời rạc.
2. Nếu KHÔNG có `TeamsCreate`: điều phối bằng tool `Agent` — lần lượt spawn từng agent theo workflow, truyền đầy đủ context (kèm mọi link/tài nguyên) cho mỗi agent vì agent là phiên mới, không thấy hội thoại gốc.

## Workflow

1. **leader** nhận yêu cầu, khảo sát codebase, lập kế hoạch step-by-step và phân công.
2. Với mỗi task: **leader → coder** (implement) **→ reviewer** (review).
   - reviewer **PASS** → báo leader, leader chuyển task tiếp theo.
   - reviewer **FAIL** → leader đẩy task lại coder kèm danh sách issue; lặp đến khi PASS.
3. **leader** chèn **tester** khi task có logic mới / fix bug / refactor có rủi ro.
4. **leader** chèn **doc-writer** khi cần cập nhật README / API docs / changelog.
5. Hết task → leader tổng kết và dừng.

## Quy tắc

- Mọi link/tài nguyên user cung cấp phải được truyền nguyên vẹn xuống từng teammate.
- Trao đổi và báo cáo với user bằng **tiếng Việt**.
- Bám sát kế hoạch của leader; mọi thay đổi scope phải báo lại leader.

---

**Yêu cầu của user:** $ARGUMENTS

Nếu phần yêu cầu ở trên trống, hãy hỏi user muốn team xử lý task gì trước khi khởi tạo team.
