#!/usr/bin/env bash
# Ask Gemini (via the Antigravity CLI `agy`) a question about a screenshot and print
# the text answer. Keeps image tokens out of the Claude context: Claude saves the
# screenshot to disk, this script reads it on Gemini quota and returns plain text.
#
# Usage: gemini-vision.sh <image-path> "<question>" [model]
#   model defaults to gemini-3.8-flash-medium (see `agy models`).
# Exit codes: 0 answer printed | 1 bad usage / missing file / agy missing | 2 agy failed

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $(basename "$0") <image-path> \"<question>\" [model]" >&2
  exit 1
fi

image="$1"
question="$2"
model="${3:-gemini-3.8-flash-medium}"

if ! command -v agy >/dev/null 2>&1; then
  echo "gemini-vision: 'agy' (Antigravity CLI) not found on PATH" >&2
  exit 1
fi
if [[ ! -f "$image" ]]; then
  echo "gemini-vision: image not found: $image" >&2
  exit 1
fi

image_abs="$(cd "$(dirname "$image")" && pwd)/$(basename "$image")"
image_dir="$(dirname "$image_abs")"

# Gemini is told not to run commands, so it cannot measure the file itself; without
# the size it answers UNSURE to any coordinate question. PIL first, PNG header as fallback.
size="$(python3 - "$image_abs" <<'PY' 2>/dev/null || true
import struct, sys
path = sys.argv[1]
try:
    from PIL import Image
    with Image.open(path) as im:
        print("%dx%d" % im.size)
except Exception:
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        print("%dx%d" % struct.unpack(">II", head[16:24]))
PY
)"
size_line=""
if [[ -n "$size" ]]; then
  size_line="The image is ${size} pixels (width x height). Give any coordinates in this pixel space, origin top-left, as the centre of the element.
"
fi

prompt="You are a QA assistant reading an Android app screenshot.
Open and look at this image file: ${image_abs}
${size_line}Rules: only view the image; do not run commands, edit or create files.
Report only what is visibly on screen. Quote on-screen text verbatim.
If something cannot be determined from the image, answer UNSURE for it instead of guessing.

Question: ${question}"

raw="$(cd "$image_dir" && agy -p "$prompt" \
  --model "$model" \
  --add-dir "$image_dir" \
  --mode plan \
  --output-format json \
  --print-timeout 180s 2>&1)" || {
  echo "gemini-vision: agy exited non-zero" >&2
  echo "$raw" >&2
  exit 2
}

# agy prints one JSON object; pull out the answer, fail loudly on anything else.
printf '%s' "$raw" | python3 -c '
import json, sys
raw = sys.stdin.read()
start = raw.find("{")
try:
    data = json.loads(raw[start:]) if start >= 0 else None
except json.JSONDecodeError:
    data = None
if not isinstance(data, dict) or data.get("status") != "SUCCESS":
    sys.stderr.write("gemini-vision: agy returned no successful answer:\n" + raw + "\n")
    sys.exit(2)
print(data.get("response", "").strip())
'
