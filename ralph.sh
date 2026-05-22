#!/bin/bash
# Ralph Loop — 自主执行脚本
# 用法: ./ralph.sh [--tool claude|amp] [max_iterations]
# 示例: ./ralph.sh --tool claude 15

set -e

TOOL="claude"
MAX_ITERATIONS=10
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool) TOOL="$2"; shift 2 ;;
    --tool=*) TOOL="${1#*=}"; shift ;;
    *) [[ "$1" =~ ^[0-9]+$ ]] && MAX_ITERATIONS="$1"; shift ;;
  esac
done

if [[ "$TOOL" != "claude" && "$TOOL" != "amp" ]]; then
  echo "错误: tool 必须是 claude 或 amp"
  exit 1
fi

if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^feat/||;s|^fix/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    echo "📦 归档上次运行: $LAST_BRANCH → $ARCHIVE_FOLDER"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  [ -n "$CURRENT_BRANCH" ] && echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
fi

if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo ""
echo "🚀 Ralph Loop 启动"
echo "   工具: $TOOL | 最大迭代: $MAX_ITERATIONS"
echo "   项目: $(jq -r '.project // "unknown"' "$PRD_FILE" 2>/dev/null)"
echo "   分支: $(jq -r '.branchName // "unknown"' "$PRD_FILE" 2>/dev/null)"
echo ""

TOTAL=$(jq '.userStories | length' "$PRD_FILE" 2>/dev/null || echo "?")
DONE=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
echo "📋 任务状态: $DONE / $TOTAL 完成"
echo ""

for i in $(seq 1 $MAX_ITERATIONS); do
  REMAINING=$(jq '[.userStories[] | select(.passes==false)] | length' "$PRD_FILE" 2>/dev/null || echo "1")
  if [ "$REMAINING" -eq 0 ]; then
    echo "✅ 所有任务已完成！"
    exit 0
  fi

  echo "================================================================"
  echo " 迭代 $i / $MAX_ITERATIONS"
  NEXT_STORY=$(jq -r '[.userStories[] | select(.passes==false)] | sort_by(.priority) | first | .title' "$PRD_FILE" 2>/dev/null || echo "unknown")
  echo " 下一个 story: $NEXT_STORY"
  echo "================================================================"

  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(cat "$SCRIPT_DIR/CLAUDE.md" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  else
    OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true
  fi

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "✅ Ralph 完成所有任务！（第 $i 轮）"
    DONE=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE" 2>/dev/null || echo "?")
    echo "   完成: $DONE / $TOTAL"
    exit 0
  fi

  if echo "$OUTPUT" | grep -q "<promise>NEED_PERMISSIONS</promise>"; then
    echo ""
    echo "⚠️ Ralph 需要额外权限，已暂停。请处理后重新运行。"
    exit 2
  fi

  DONE=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
  echo "进度: $DONE / $TOTAL | 迭代 $i 完成，继续..."
  echo ""
  sleep 2
done

echo ""
echo "⏱️ 达到最大迭代次数 ($MAX_ITERATIONS)，任务未全部完成。"
DONE=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
echo "   完成: $DONE / $TOTAL"
echo "   查看 progress.txt 了解详情，可重新运行继续。"
exit 1
