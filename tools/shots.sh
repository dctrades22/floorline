#!/bin/sh
# Headless screenshots with locally installed Chrome/Chromium. Usage: sh tools/shots.sh
cd "$(dirname "$0")/.." && mkdir -p shots
CH=${CHROME:-google-chrome}; U="file://$PWD/index.html"
shot() { $CH --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=$1 --virtual-time-budget=3000 --screenshot=shots/$2.png "$U$3" >/dev/null 2>&1; echo shots/$2.png; }
shot 375,2700 mobile-375 ""
shot 1280,1100 desktop-1280 ""
shot 375,2700 mobile-375-partial "#P019"
shot 1280,1100 desktop-1280-partial "#P019"
shot 1280,1100 desktop-1280-custom-only "#P004"
