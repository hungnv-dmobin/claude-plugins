#!/usr/bin/env bash
# Setup script for dmb claude-plugins — Mac & Windows (Git Bash).
# Run once per machine: bash setup.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
OS="$(uname -s)"

# ── Kiểm tra điều kiện ───────────────────────────────────────────────────────

if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' không tìm thấy trong PATH."
  if [ "$OS" = "Darwin" ]; then
    echo ""
    echo "Mac — một trong hai cách:"
    echo "  1. Mở Claude Code desktop app → menu 'Claude Code' → 'Install CLI Tools'"
    echo "  2. sudo ln -sf '/Applications/Claude.app/Contents/MacOS/claude' /usr/local/bin/claude"
  else
    echo "Windows — cài Claude Code từ https://claude.ai/code, đảm bảo thư mục cài nằm trong PATH"
  fi
  exit 1
fi

if ! command -v node &>/dev/null; then
  echo "WARNING: Node.js không tìm thấy — phần QA on-device (android-cook) sẽ không chạy được."
  if [ "$OS" = "Darwin" ]; then
    echo "  Cài Node.js: brew install node"
  else
    echo "  Cài Node.js: https://nodejs.org"
  fi
  echo "  Tiếp tục cài đặt phần còn lại..."
  echo ""
fi

# ── Cài đặt ──────────────────────────────────────────────────────────────────

echo "==> Tạo thư mục Claude nếu chưa có..."
mkdir -p "$CLAUDE_DIR/agents" "$CLAUDE_DIR/commands"

echo "==> Cài team agents (leader, coder, reviewer, tester, doc-writer)..."
cp "$REPO_DIR/team/agents/"*.md "$CLAUDE_DIR/agents/"

echo "==> Cài /team command..."
cp "$REPO_DIR/team/commands/team.md" "$CLAUDE_DIR/commands/"

echo "==> Thêm plugin marketplace..."
claude plugin marketplace add hungnv-dmobin/claude-plugins

echo "==> Cài plugin android-cook (6 skills + 2 agents + mobile-mcp)..."
claude plugin install android-cook@dmb-plugins

echo "==> Cài plugin productivity (4 skills)..."
claude plugin install productivity@dmb-plugins

# ── Xong ─────────────────────────────────────────────────────────────────────

echo ""
echo "✓ Hoàn tất! Khởi động lại Claude Code để các thay đổi có hiệu lực."
echo ""
echo "Kiểm tra:"
echo "  claude plugin list    # android-cook + productivity phải enabled"
echo "  claude mcp list       # plugin:android-cook:mobile-mcp phải Connected"
if [ "$OS" = "Darwin" ]; then
  echo "  ls ~/.claude/agents/  # 5 agent files"
else
  echo "  ls ~/.claude/agents/"
fi
