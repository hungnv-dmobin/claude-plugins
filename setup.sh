#!/usr/bin/env bash
# Setup script for dmb claude-plugins on a new machine.
# Run once: bash setup.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

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

echo ""
echo "Done! Khởi động lại Claude Code để các thay đổi có hiệu lực."
echo ""
echo "Lệnh kiểm tra:"
echo "  claude plugin list"
echo "  claude mcp list"
