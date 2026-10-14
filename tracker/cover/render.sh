#!/bin/sh
# Render cover-1280x720.png and thumbnail.png from cover.html with local headless Chrome.
cd "$(dirname "$0")"; CH=${CHROME:-google-chrome}; U="file://$PWD/cover.html"
$CH --headless=new --no-sandbox --hide-scrollbars --user-data-dir=$(mktemp -d) --force-device-scale-factor=1 --window-size=1280,720 --screenshot=cover-1280x720.png "$U" >/dev/null 2>&1
$CH --headless=new --no-sandbox --hide-scrollbars --user-data-dir=$(mktemp -d) --force-device-scale-factor=1 --window-size=600,600 --screenshot=thumbnail.png "$U#thumb" >/dev/null 2>&1
python3 -c "from PIL import Image;[print(f,Image.open(f).size) for f in ('cover-1280x720.png','thumbnail.png')]"
