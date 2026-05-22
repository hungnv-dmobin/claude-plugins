# dmb claude-plugins

Cấu hình Claude Code cá nhân — cài 1 lần trên mỗi máy, hoạt động ở mọi session.

## Nội dung

| Thành phần | Loại | Mô tả |
|---|---|---|
| **team agents** | user-level | `leader`, `coder`, `reviewer`, `tester`, `doc-writer` + lệnh `/team` |
| **android-cook** | plugin | 6 skills + 2 agents + `mobile-mcp` — Android task orchestration |
| **productivity** | plugin | 4 skills — brainstorming và soạn thảo skill |

---

## Cài đặt trên máy mới

### Cách 1 — Script tự động (khuyến nghị)

```bash
git clone https://github.com/hungnv-dmobin/claude-plugins.git ~/claude-plugins
cd ~/claude-plugins
bash setup.sh
```

Khởi động lại Claude Code sau khi chạy xong.

### Cách 2 — Thủ công từng bước

```bash
# 1. Clone repo
git clone https://github.com/hungnv-dmobin/claude-plugins.git ~/claude-plugins
cd ~/claude-plugins

# 2. Cài team agents vào user-level (~/.claude/agents/)
cp team/agents/*.md ~/.claude/agents/
cp team/commands/team.md ~/.claude/commands/

# 3. Cài plugins
claude plugin marketplace add hungnv-dmobin/claude-plugins
claude plugin install android-cook@dmb-plugins
claude plugin install productivity@dmb-plugins
```

---

## Kiểm tra sau khi cài

```bash
claude plugin list          # android-cook + productivity phải ở trạng thái enabled
claude mcp list             # plugin:android-cook:mobile-mcp phải Connected
ls ~/.claude/agents/        # coder.md  doc-writer.md  leader.md  reviewer.md  tester.md
```

---

## Hướng dẫn sử dụng

### Team agents — `/team`

Gõ `/team <mô tả task>` để khởi động team: leader lập kế hoạch → coder implement → reviewer review → lặp đến khi PASS → tester/doc-writer nếu cần.

Workflow: **leader → coder → reviewer** (lặp đến PASS) **→ leader tổng kết**.

| Agent | Model | Vai trò |
|---|---|---|
| `leader` | Opus | Phân tích, lập kế hoạch, phân công |
| `coder` | Sonnet | Viết/sửa code, tự review nội bộ |
| `reviewer` | Sonnet | Review — trả về PASS hoặc FAIL + issue list |
| `tester` | Sonnet | Viết và chạy test |
| `doc-writer` | Sonnet | Viết README, API docs, changelog |

### Plugin android-cook — `dmb-android-cook`

Gõ **"cook this task: \<mô tả task Android\>"**

Skill hỏi lại chỗ mơ hồ → lập kế hoạch (cần duyệt) → vòng lặp `android-cook:dmb-android-dev` (code) → `android-cook:dmb-android-qa` (chạy app test trên device) → fix → smoke test → báo cáo.

**Skills đi kèm:** `dmb-android-cook`, `qa-android-mcp-test-runner`, `qa-bug-tracker`, `android-clean-architecture`, `create-android-module`, `android-platform-components`

**Yêu cầu cho phần QA (chạy app thật):** Node.js, Android SDK + `adb` trong PATH, emulator hoặc thiết bị đang kết nối.

### Plugin productivity

| Skill | Kích hoạt khi |
|---|---|
| `productivity:grill-me` | "grill me on this plan" — phỏng vấn kế hoạch của bạn |
| `productivity:grill-with-docs` | Grill kèm kiểm tra docs/ADR của project |
| `productivity:skill-handler` | Viết, sửa, audit một Claude Code skill |
| `productivity:handoff` | Tóm tắt hội thoại thành tài liệu bàn giao |

---

## Cập nhật

```bash
# Kéo thay đổi mới nhất và cài lại agents
cd ~/claude-plugins
git pull
cp team/agents/*.md ~/.claude/agents/
cp team/commands/team.md ~/.claude/commands/

# Cập nhật plugins từ marketplace
claude plugin marketplace update dmb-plugins
```

---

## Ghi chú kỹ thuật

- **Team agents** cài user-level (`~/.claude/agents/`) — không qua plugin để tránh namespace (`team:leader`). Lệnh `/team` gọi agent bằng tên bare (`leader`, `coder`...) nên cần user-level.
- **Plugin android-cook** namespace agents nội bộ: `android-cook:dmb-android-dev` và `android-cook:dmb-android-qa`. Skill `dmb-android-cook` đã được sửa để dùng đúng tên này.
- `compose-expert` skill không có trong repo — agent `android-cook:dmb-android-dev` có thể tham chiếu nhưng sẽ không nạp được. Thêm sau nếu cần.
