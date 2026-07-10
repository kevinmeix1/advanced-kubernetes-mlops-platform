#!/usr/bin/env bash
set -euo pipefail

SCREENSHOT_DIR="${1:-docs/screenshots}"
AUDIO="${2:-.local/demo/kubernetes-mlops-judge-demo.mp3}"
OUTPUT="${3:-docs/demo/kubernetes-mlops-judge-demo.mp4}"

command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 1; }
test -f "$AUDIO" || { echo "Missing narration: run make demo-voice" >&2; exit 1; }
for screenshot in dashboard.png dashboard-advance.png dashboard-rollback.png dashboard-mobile.png; do
  test -f "$SCREENSHOT_DIR/$screenshot" || { echo "Missing screenshot: $screenshot" >&2; exit 1; }
done

mkdir -p "$(dirname "$OUTPUT")"
ffmpeg -y \
  -loop 1 -t 48 -i "$SCREENSHOT_DIR/dashboard.png" \
  -loop 1 -t 42 -i "$SCREENSHOT_DIR/dashboard-advance.png" \
  -loop 1 -t 48 -i "$SCREENSHOT_DIR/dashboard-rollback.png" \
  -loop 1 -t 42 -i "$SCREENSHOT_DIR/dashboard-mobile.png" \
  -i "$AUDIO" \
  -filter_complex \
    "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,format=yuv420p[v0]; \
     [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,format=yuv420p[v1]; \
     [2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,format=yuv420p[v2]; \
     [3:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,format=yuv420p[v3]; \
     [v0][v1][v2][v3]concat=n=4:v=1:a=0[video]" \
  -map "[video]" -map 4:a \
  -c:v libx264 -profile:v high -crf 20 -c:a aac -b:a 160k -shortest "$OUTPUT"
echo "$OUTPUT"
