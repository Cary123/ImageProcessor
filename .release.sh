#!/bin/zsh
set -e

cd /Users/josephgao/Documents/ImageProcessor

git credential-osxkeychain get <<'EOF' > /tmp/gh_creds.txt
protocol=https
host=github.com
EOF

TOKEN=$(awk '/password=/{print substr($0, 10)}' /tmp/gh_creds.txt)
rm -f /tmp/gh_creds.txt

export GITHUB_TOKEN="$TOKEN"

gh release create v1.0.0 dist/ImageProcessor-macOS.zip \
  --title "ImageProcessor v1.0.0" \
  --notes "Bug fix release:\n- Fix image not centering in canvas\n- Fix crash when running AI matting (caused by cross-thread signal lambda)\n\nDownload the macOS app bundle below." \
  --repo Cary123/ImageProcessor
