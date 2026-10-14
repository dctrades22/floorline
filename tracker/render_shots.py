#!/usr/bin/env python3
"""Render Accounts, Daily Log and Checklist tabs (demo data) to PNG via LibreOffice -> PDF -> pdftoppm. Writes tracker/shots/."""
import os, subprocess, tempfile, shutil, sys
from openpyxl import load_workbook
from openpyxl.worksheet.page import PageMargins
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_tracker as bt
SHOTS = {"Accounts": ("A1:AN13", "accounts"), "Accounts ": ("A1:AN13", "accounts-results"), "Daily Log": ("A1:J12", "daily-log"), "Checklist": ("A1:D17", "checklist")}
tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(HERE, "shots"), exist_ok=True)
for key, (area, name) in SHOTS.items():
    tab = key.strip()
    p = os.path.join(tmp, name + ".xlsx")
    bt.build(p, bt.DEMO_ACC, bt.DEMO_LOG, demo_asof=bt.d(2026, 10, 14))
    wb = load_workbook(p)
    for ws in wb.worksheets:
        if ws.title != tab: ws.sheet_state = "hidden"
    ws = wb[tab]; wb.active = wb.worksheets.index(ws)
    if name == "accounts-results":   # zoomed view: identity + results (inputs D-O and flags hidden)
        for c in "DEFGHIJLMNO": ws.column_dimensions[c].hidden = True
        ws.column_dimensions["AN"].hidden = True; area = "A1:AM13"
    ws.print_area = area; ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3 if tab == "Accounts" else ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1; ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.1, right=0.1, top=0.1, bottom=0.1, header=0, footer=0)
    ws.print_options.gridLines = False
    wb.save(p)
    # xlsx -> ods -> pdf (direct xlsx -> pdf export errors in LibreOffice 25.2 headless on this workbook)
    subprocess.run(["soffice", "--headless", "--convert-to", "ods", "--outdir", tmp, p], check=True, capture_output=True, timeout=300)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, p[:-5] + ".ods"], check=True, capture_output=True, timeout=300)
    out = os.path.join(HERE, "shots", name)
    subprocess.run(["pdftoppm", "-png", "-r", "200" if name == "accounts" else "150", "-singlefile", os.path.join(tmp, name + ".pdf"), out], check=True)
    from PIL import Image, ImageChops
    im = Image.open(out + ".png").convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    im.crop(bbox).save(out + ".png"); print(out + ".png", im.crop(bbox).size)
shutil.rmtree(tmp)
