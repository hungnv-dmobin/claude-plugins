# dmb claude-plugins

Cấu hình Claude Code cá nhân — cài 1 lần trên mỗi máy, hoạt động ở mọi session.

## Nội dung

| Thành phần | Loại | Mô tả |
|---|---|---|
| **team agents** | user-level | `leader`, `coder`, `reviewer`, `tester`, `doc-writer` + lệnh `/team` |
| **android-cook** | plugin | 6 skills + 2 agents + `mobile-mcp` — Android task orchestration |
| **productivity** | plugin | 4 skills — brainstorming và soạn thảo skill |

---

## Điều kiện trước khi cài

### Mac

```bash
# Claude Code desktop app (bắt buộc)
# → Tải tại https://claude.ai/code → cài .dmg

# Sau khi cài app, thêm CLI vào PATH (1 trong 2 cách):
# Cách 1 — dùng menu trong app: Claude Code → Install CLI Tools
# Cách 2 — symlink thủ công:
sudo ln -sf '/Applications/Claude.app/Contents/MacOS/claude' /usr/local/bin/claude

# Git (nếu chưa có)
xcode-select --install          # cài Xcode CLI tools, bao gồm git

# Node.js — bắt buộc cho phần QA on-device của android-cook
brew install node

# Android SDK + adb — bắt buộc cho phần QA on-device của android-cook
brew install --cask android-studio   # sau đó mở Android Studio → SDK Manager → cài SDK + Platform Tools
# Thêm adb vào PATH (thêm vào ~/.zshrc hoặc ~/.bash_profile):
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

### Windows

```powershell
# Claude Code desktop app (bắt buộc)
# → Tải tại https://claude.ai/code → cài .exe (claude.exe tự vào PATH)

# Git for Windows — bao gồm Git Bash để chạy setup.sh
# → https://git-scm.com/download/win

# Node.js — bắt buộc cho phần QA on-device của android-cook
# → https://nodejs.org  (hoặc: winget install OpenJS.NodeJS)

# Android SDK + adb — bắt buộc cho phần QA on-device của android-cook
# → Cài Android Studio: https://developer.android.com/studio
# Thêm vào PATH (System Environment Variables):
# %LOCALAPPDATA%\Android\Sdk\platform-tools
```

> **Lưu ý:** Node.js và Android SDK chỉ cần thiết cho tính năng **QA on-device** (chạy app thật trên emulator/thiết bị). Các skill khác (team agents, brainstorming, clean architecture...) không cần chúng.

---

## Cài đặt trên máy mới

### Cách 1 — Script tự động *(Mac & Windows Git Bash)*

```bash
git clone https://github.com/hungnv-dmobin/claude-plugins.git ~/claude-plugins
cd ~/claude-plugins
bash setup.sh
```

Script tự kiểm tra `claude` và `node` trước khi cài, báo lỗi rõ nếu thiếu.
Khởi động lại Claude Code sau khi chạy xong.

### Cách 2 — Thủ công từng bước

```bash
# 1. Clone repo
git clone https://github.com/hungnv-dmobin/claude-plugins.git ~/claude-plugins
cd ~/claude-plugins

# 2. Cài team agents vào user-level
mkdir -p ~/.claude/agents ~/.claude/commands
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
claude plugin list          # android-cook + productivity phải enabled
claude mcp list             # plugin:android-cook:mobile-mcp phải Connected
ls ~/.claude/agents/        # coder.md  doc-writer.md  leader.md  reviewer.md  tester.md
```

---

## Hướng dẫn sử dụng

### Team agents — `/team`

Gõ `/team <mô tả task>` để khởi động team:
**leader → coder → reviewer** (lặp đến PASS) → tester/doc-writer nếu cần → leader tổng kết.

| Agent | Model | Vai trò |
|---|---|---|
| `leader` | Opus | Phân tích, lập kế hoạch, phân công |
| `coder` | Sonnet | Viết/sửa code, tự review nội bộ |
| `reviewer` | Sonnet | Review — trả về PASS hoặc FAIL + issue list |
| `tester` | Sonnet | Viết và chạy test |
| `doc-writer` | Sonnet | Viết README, API docs, changelog |

### Plugin android-cook

Gõ **"cook this task: \<mô tả task Android\>"**

Skill hỏi lại chỗ mơ hồ → lập kế hoạch (cần duyệt) → vòng lặp dev (code + build) → QA (chạy app trên device) → fix → smoke test → báo cáo.

**Skills:** `dmb-android-cook`, `qa-android-mcp-test-runner`, `qa-bug-tracker`, `android-clean-architecture`, `create-android-module`, `android-platform-components`

### Plugin productivity

| Skill | Dùng khi |
|---|---|
| `productivity:grill-me` | Muốn bị hỏi vặn để stress-test một kế hoạch |
| `productivity:grill-with-docs` | Grill kèm kiểm tra docs/ADR của project |
| `productivity:skill-handler` | Viết, sửa, audit một Claude Code skill |
| `productivity:handoff` | Tóm tắt hội thoại thành tài liệu bàn giao |

---

## Cập nhật

```bash
cd ~/claude-plugins
git pull

# Cập nhật team agents (nếu có thay đổi)
cp team/agents/*.md ~/.claude/agents/
cp team/commands/team.md ~/.claude/commands/

# Cập nhật plugins từ marketplace
claude plugin marketplace update dmb-plugins
```

---

## Ghi chú kỹ thuật

- **Team agents** cài user-level (`~/.claude/agents/`) thay vì plugin để tránh namespace (`team:leader`). Lệnh `/team` gọi agent bằng tên bare (`leader`, `coder`...) nên cần user-level.
- **Plugin android-cook** namespace agents nội bộ: `android-cook:dmb-android-dev` và `android-cook:dmb-android-qa`. Skill `dmb-android-cook` đã được sửa để dùng đúng tên này.
- `compose-expert` skill không có trong repo — agent `android-cook:dmb-android-dev` có thể tham chiếu nhưng sẽ không nạp được. Thêm sau nếu cần.
