#!/usr/bin/env python3
"""Generate tracker/Floorline-Tracker.xlsx from tracker/FORMULAS.md (spec v0.1.0) and tracker/presets_tab.csv.
No macros. Formulas are the FORMULAS.md cell formulas with PV/HIT/CENT_UP/CENT_DOWN expanded inline.

  python3 tracker/build_tracker.py            # writes tracker/Floorline-Tracker.xlsx (empty, ready to use)
  python3 tracker/build_tracker.py --demo OUT # same workbook with illustrative example rows (screenshots only)
Library use: build(path, accounts=[...], logs=[...]) (used by tracker/test_tracker.py)."""
import csv, datetime, json, os, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NA, NL = 11, 1001          # last account row, last log row

# ---- design tokens (mirror css/app.css) ----
BG, PANEL, INPUT, LINE, LINE2 = "0B0C0D", "121416", "1B1F23", "262A2F", "3A4048"
INK, MUT, DIM, BRAND = "ECEAE4", "8D939B", "5D636B", "FF5B1F"
GREEN, AMBER, RED, BLUE, DRED = "35D07F", "FFB224", "FF4A4A", "7CC4FF", "7A0E0E"
MONO = "Consolas"
fill = lambda c: PatternFill("solid", start_color=c, end_color=c)
F_BG, F_PANEL, F_IN = fill(BG), fill(PANEL), fill(INPUT)
thin = Side(style="thin", color=LINE); thin2 = Side(style="thin", color=LINE2)
B_CELL = Border(bottom=thin, right=thin); B_IN = Border(top=thin2, bottom=thin2, left=thin2, right=thin2)
B_HEAD = Border(bottom=Side(style="medium", color=BRAND))

# ---- notation from FORMULAS.md, expanded inline ----
PRESET_COL = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "H": "H", "I": "I", "J": "J",
              "K": "K", "L": "L", "M": "M", "N": "N", "O": "O", "P": "P"}
def PV(col, r): return f'IFERROR(INDEX(Presets!${col}$2:${col}$200,MATCH($B{r},Presets!$A$2:$A$200,0))&"","")'
def HIT(v, f, touch): return f'IF({touch},ROUND({v}-({f}),6)<=0,ROUND({v}-({f}),6)<0)'
def CENT_UP(x): return f'-INT(ROUND(-({x})*100,6))/100'
def CENT_DOWN(x): return f'INT(ROUND(({x})*100,6))/100'
def ISO(s):   # M-4: parse yyyy-mm-dd without locale-dependent VALUE(date text)
    return f'DATE(VALUE(LEFT({s},4)),VALUE(MID({s},6,2)),VALUE(MID({s},9,2)))'
def G(f): return f'=IFERROR({f},"INVALID")'   # final guard (FORMULAS §4)
LOGR = "'Daily Log'!$A$2:$A$1001"; LOGC = "'Daily Log'!$C$2:$C$1001"; LOGD = "'Daily Log'!$D$2:$D$1001"; LOGI = "'Daily Log'!$I$2:$I$1001"

def account_formulas(r):
    pv = lambda c: PV(c, r)
    W = (f'=IF(AND(A{r}="",B{r}=""),"",'
         f'IF(OR(A{r}="",B{r}="",P{r}="",Q{r}="",R{r}="",S{r}="",T{r}="",U{r}="",V{r}="",K{r}="",AND(U{r}<>"NONE",L{r}="")),"INCOMPLETE",'
         f'IF(OR(COUNTIFS($A$2:$A${NA},A{r})>1,'
         f'AND(P{r}<>"static",P{r}<>"eod_trailing",P{r}<>"intraday_trailing"),'
         f'NOT(ISNUMBER(Q{r})),Q{r}<=0,ROUND(Q{r}*100,6)<>INT(ROUND(Q{r}*100,6)),'
         f'NOT(ISNUMBER(R{r})),R{r}<=0,ROUND(R{r}*100,6)<>INT(ROUND(R{r}*100,6)),'
         f'AND(S{r}<>"NONE",NOT(ISNUMBER(S{r}))),'
         f'AND(P{r}="static",S{r}<>"NONE"),'
         f'IF(ISNUMBER(S{r}),ROUND(Q{r}+S{r}-(Q{r}-R{r}),6)<=0,FALSE),'
         f'IF(ISNUMBER(S{r}),OR(S{r}<-100000000,S{r}>100000000),FALSE),'
         f'AND(T{r}<>TRUE,T{r}<>FALSE),'
         f'AND(U{r}<>"NONE",OR(NOT(ISNUMBER(U{r})),U{r}<=0)),'
         f'IF(V{r}="NONE",FALSE,IF(ISNUMBER(V{r}),OR(V{r}<0,V{r}<>INT(V{r})),TRUE)),'
         f'NOT(ISNUMBER(K{r})),AND(U{r}<>"NONE",NOT(ISNUMBER(L{r}))),'
         f'Q{r}>100000000,R{r}>100000000,K{r}<=0,K{r}>100000000,'
         f'IF(ISNUMBER(U{r}),U{r}>100000000,FALSE),IF(ISNUMBER(L{r}),OR(L{r}<=0,L{r}>100000000),FALSE)),"INVALID",'
         f'IF(COUNTIFS({LOGR},A{r},{LOGI},"INVALID")>0,"INVALID",'
         f'IF(OR(COUNTIFS({LOGR},A{r},{LOGI},"INCOMPLETE")>0,COUNTIFS({LOGI},"UNKNOWN_ACCOUNT")>0),"INCOMPLETE","OK")))))')
    W = "=IFERROR(" + W[1:] + ',"INVALID")'
    ok = f'$W{r}<>"OK",$W{r}'
    return {
        "C": f'={pv("B")}',
        "P": G(f'IF(D{r}<>"",D{r},{pv("C")})'),
        "Q": G(f'IF(E{r}<>"",E{r},IF({pv("D")}<>"",VALUE({pv("D")}),""))'),
        "R": G(f'IF(F{r}<>"",F{r},IF({pv("E")}<>"",VALUE({pv("E")}),IF(AND({pv("F")}<>"",ISNUMBER(Q{r})),VALUE({pv("F")})/100*Q{r},"")))'),
        "S": G(f'IF(G{r}<>"",G{r},IF({pv("G")}="NONE","NONE",IF({pv("G")}<>"",VALUE({pv("G")}),"")))'),
        "T": G(f'IF(H{r}<>"",H{r},IF({pv("H")}="TRUE",TRUE,IF({pv("H")}="FALSE",FALSE,"")))'),
        "U": G(f'IF(I{r}<>"",I{r},IF({pv("I")}="NONE","NONE",IF({pv("I")}<>"",VALUE({pv("I")}),"")))'),
        "V": G(f'IF(J{r}<>"",J{r},IF({pv("J")}<>"",VALUE({pv("J")}),""))'),
        "W": W,
        "X": G(f'IF({ok},IF(P{r}="static",Q{r},IF(P{r}="eod_trailing",MAX(Q{r},_xlfn.MAXIFS({LOGC},{LOGR},A{r})),'
               f'MAX(Q{r},K{r},_xlfn.MAXIFS({LOGC},{LOGR},A{r}),_xlfn.MAXIFS({LOGD},{LOGR},A{r})))))'),
        "Y": G(f'IF({ok},{CENT_UP(f"AJ{r}")})'),
        "Z": G(f'IF({ok},AND(ISNUMBER(S{r}),P{r}<>"static",ROUND(X{r}-R{r}-(Q{r}+IF(ISNUMBER(S{r}),S{r},0)),6)>=0))'),
        "AA": G(f'IF({ok},OR(COUNTIFS({LOGR},A{r},{LOGI},"BREACHED")>0,{HIT(f"K{r}", f"AJ{r}", f"T{r}")}))'),
        "AB": G(f'IF({ok},IF(AA{r},"BREACHED",{CENT_DOWN(f"MAX(0,K{r}-AJ{r})")}))'),
        "AC": G(f'IF({ok},IF(AA{r},"BREACHED",IF(U{r}="NONE","NONE",{CENT_DOWN(f"MAX(0,U{r}-MAX(0,-(K{r}-L{r})))")})))'),
        "AD": G(f'IF({ok},IF(AA{r},"BREACHED",IF(AC{r}="NONE",AB{r},MIN(AB{r},AC{r}))))'),
        "AE": G(f'IF({ok},IF(AA{r},"BREACHED",IF(AND(AC{r}<>"NONE",AC{r}<AB{r}),"daily_loss","drawdown")))'),
        "AF": G(f'IF(AK{r}<>"OK",AK{r},IF(AA{r},"BREACHED",{CENT_DOWN(f"MIN(M{r},AD{r})")}))'),
        "AG": G(f'IF(AK{r}<>"OK",AK{r},IF(AA{r},"BREACHED",IF(V{r}="NONE",AL{r},MIN(AL{r},V{r}))))'),
        "AH": G(f'IF(AK{r}<>"OK",AK{r},AND(V{r}<>"NONE",AL{r}>V{r}))'),
        "AI": G(f'IF(AK{r}<>"OK",AK{r},M{r}>AD{r})'),
        "AJ": G(f'IF($W{r}<>"OK","",IF(P{r}="static",Q{r}-R{r},IF(S{r}="NONE",X{r}-R{r},MIN(X{r}-R{r},Q{r}+S{r}))))'),
        "AK": G(f'IF({ok},IF(OR(M{r}="",N{r}="",O{r}=""),"INCOMPLETE",IF(OR(NOT(ISNUMBER(M{r})),M{r}<0,NOT(ISNUMBER(N{r})),N{r}<1,N{r}<>INT(N{r}),NOT(ISNUMBER(O{r})),O{r}<=0,O{r}>100000,ROUND(O{r}*1000000,3)<>INT(ROUND(O{r}*1000000,3)),M{r}>100000000),"INVALID","OK")))'),
        "AL": G(f'IF(AK{r}<>"OK","",IF(AA{r},0,INT(ROUND(MIN(M{r},AD{r})/(N{r}*O{r}),9))))'),
        "AM": G(f'IF(AK{r}<>"OK",AK{r},IF(AA{r},"BREACHED",{CENT_DOWN(f"AG{r}*N{r}*O{r}")}))'),
        "AN": G(f'IF(AND(A{r}="",B{r}=""),"",_xlfn.TEXTJOIN("; ",TRUE,IF(C{r}="partial","PARTIAL PRESET: verify "&{pv("L")},""),'
                f'IF(C{r}="manual","MANUAL: all params user-entered",""),'
                f'IF(OR(AND(D{r}<>"",{pv("C")}<>""),AND(E{r}<>"",{pv("D")}<>""),AND(F{r}<>"",{pv("E")}<>""),AND(G{r}<>"",{pv("G")}<>""),'
                f'AND(H{r}<>"",{pv("H")}<>""),AND(I{r}<>"",{pv("I")}<>""),AND(J{r}<>"",{pv("J")}<>"")),"OVERRIDES PRESET",""),'
                f'IF(AND(A{r}<>"",V{r}=""),"MAX CONTRACTS MISSING: enter a number or NONE",""),'
                f'IF(AND({pv("N")}<>"",NOT(ISNUMBER($B$13))),"AS-OF DATE MISSING: enter today in B13 (stale check off)",""),'
                f'IF(AND({pv("N")}<>"",ISNUMBER($B$13)),IF($B$13-{ISO(pv("N"))}>30,"STALE PRESET: checked "&{pv("N")}&", over 30 days before As of",""),""),'
                f'IF({pv("M")}<>"","source: "&{pv("M")}&" checked "&{pv("N")},"")))'),
    }

def log_formulas(r):
    acc = lambda c: f'INDEX(Accounts!${c}$2:${c}${NA},$F{r})'
    t, S, DD, X, touch = acc("P"), acc("Q"), acc("R"), acc("S"), acc("T")
    prior = f'_xlfn.MAXIFS($C$2:$C${NL},$A$2:$A${NL},$A{r},$B$2:$B${NL},"<"&$B{r})'
    highs = f'_xlfn.MAXIFS($D$2:$D${NL},$A$2:$A${NL},$A{r},$B$2:$B${NL},"<="&$B{r})'
    Gf = (f'=IFERROR(IF(OR($A{r}="",$F{r}=""),"",IF({t}="static",{S},IF({t}="eod_trailing",MAX({S},{prior}),'
          f'MAX({S},{prior},{highs},$C{r})))),"")')
    Hf = f'=IFERROR(IF(G{r}="","",IF({t}="static",{S}-{DD},IF({X}="NONE",G{r}-{DD},MIN(G{r}-{DD},{S}+{X})))),"")'
    dp = lambda c: f'IF({c}{r}="",FALSE,IF(ISNUMBER({c}{r}),OR({c}{r}<=0,{c}{r}>100000000,ROUND({c}{r}*100,6)<>INT(ROUND({c}{r}*100,6))),TRUE))'
    invalid = (f'OR(NOT(ISNUMBER($B{r})),NOT(ISNUMBER($C{r})),{dp("C")},{dp("D")},{dp("E")},'
               f'AND($D{r}<>"",$D{r}<MAX($C{r},$E{r})),AND($E{r}<>"",$E{r}>MIN($C{r},IF($D{r}="",$C{r},$D{r}))),'
               f'COUNTIFS($A$2:$A${NL},$A{r},$B$2:$B${NL},$B{r})>1)')
    lowv = f'IF($E{r}="",$C{r},MIN($C{r},$E{r}))'
    # spec: IF(COUNTA(A:E)=0,"",...); COUNTA is outside the §0 allowed list, so the same test is written with OR(<>"")
    If = (f'=IF(AND($A{r}="",$B{r}="",$C{r}="",$D{r}="",$E{r}=""),"",IF(OR($A{r}="",$F{r}=""),"UNKNOWN_ACCOUNT",IF(OR($B{r}="",$C{r}=""),"INCOMPLETE",IFERROR(IF({invalid},"INVALID",'
          f'IFERROR(IF({HIT(lowv, f"H{r}", touch)},"BREACHED","OK"),"INCOMPLETE")),"INVALID"))))')
    return {"F": f'=IFERROR(MATCH($A{r},Accounts!$A$2:$A${NA},0),"")', "G": Gf, "H": Hf, "I": If,
            "J": f'=IF(OR(I{r}="OK",I{r}="BREACHED"),{CENT_UP(f"H{r}")},I{r})'}

ACC_HEAD = [("A", "Account ID", 13), ("B", "Preset", 46), ("C", "Preset status", 11), ("D", "Type override", 17),
    ("E", "Start override", 12), ("F", "DD $ override", 11), ("G", "Lock offset override", 11), ("H", "Touch = breach override", 10),
    ("I", "DLL $ override", 10), ("J", "Max contracts override", 10), ("K", "Equity now (incl. open P&L)", 13),
    ("L", "Day reference balance", 13), ("M", "Risk $ / trade", 10), ("N", "Stop ticks", 7), ("O", "Tick value $", 8),
    ("P", "Type", 18), ("Q", "Start", 12), ("R", "Max DD $", 10), ("S", "Lock offset", 9), ("T", "Touch = breach", 8),
    ("U", "DLL $", 9), ("V", "Max contracts", 10), ("W", "Check", 12), ("X", "Peak", 12), ("Y", "FLOOR", 14),
    ("Z", "Locked", 9), ("AA", "Breached", 10), ("AB", "DD room", 12), ("AC", "Daily room", 12), ("AD", "BINDING ROOM", 14),
    ("AE", "Binding", 11), ("AF", "Effective risk", 11), ("AG", "CONTRACTS", 11), ("AH", "Capped", 8), ("AI", "Room-limited", 9),
    ("AJ", "floor raw", 4), ("AK", "sizing check", 4), ("AL", "contracts raw", 4), ("AM", "Actual risk", 11), ("AN", "Flags", 70)]
LOG_HEAD = [("A", "Account ID", 13), ("B", "Trading date", 13), ("C", "EOD balance", 13), ("D", "Intraday high", 13),
    ("E", "Intraday low", 13), ("F", "acct row", 4), ("G", "Peak (this row)", 13), ("H", "floor raw", 4), ("I", "Status", 12), ("J", "FLOOR", 13)]
INPUT_ACC = set("ABDEFGHIJKLMNO"); MONEY = "#,##0.00;[Color9]-#,##0.00"

def base_sheet(ws, tab):
    ws.sheet_properties.tabColor = tab
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 100

def paint(ws, rows, cols, f=F_BG):
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            cell = ws.cell(r, c)
            cell.fill = f; cell.font = Font(name=MONO, size=10, color=INK)

def header(ws, spec, calc_from=None):
    ws.row_dimensions[1].height = 34
    for i, (col, name, w) in enumerate(spec, 1):
        c = ws[f"{col}1"]; c.value = name
        big = name.isupper()
        c.font = Font(name=MONO, size=9, bold=True, color=BRAND if big else (INK if col in calc_from else MUT))
        c.fill = F_PANEL if col in calc_from else F_BG
        c.alignment = Alignment(wrap_text=True, vertical="bottom", horizontal="left")
        c.border = B_HEAD
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C2" if ws.title == "Accounts" else "B2"

def text_sheet(wb, title, lines, tab=DIM, width=110):
    ws = wb.create_sheet(title); base_sheet(ws, tab)
    paint(ws, len(lines) + 4, 3)
    ws.column_dimensions["A"].width = 3; ws.column_dimensions["B"].width = width; ws.column_dimensions["C"].width = 3
    for i, ln in enumerate(lines, 2):
        c = ws.cell(i, 2, ln if not isinstance(ln, tuple) else ln[1])
        kind = ln[0] if isinstance(ln, tuple) else "p"
        c.font = {"h": Font(name=MONO, size=15, bold=True, color=INK), "s": Font(name=MONO, size=10, bold=True, color=BRAND),
                  "p": Font(name=MONO, size=10, color=INK), "m": Font(name=MONO, size=10, color=MUT)}[kind]
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if kind == "h": ws.row_dimensions[i].height = 28
        elif len(str(c.value)) > width - 8: ws.row_dimensions[i].height = 14 * (len(str(c.value)) // (width - 8) + 1)
    ws.protection.sheet = True
    return ws

def build(path, accounts=(), logs=(), demo_asof=None):
    wb = Workbook()
    presets = list(csv.reader(open(os.path.join(HERE, "presets_tab.csv"), newline="")))
    keys = [r[0] for r in presets[1:]]

    # ---------------- Disclaimer (first on open) ----------------
    ws = wb.active; ws.title = "Disclaimer"; wb.remove(ws)
    text_sheet(wb, "Disclaimer", [("h", "FLOORLINE  ·  Multi-Account Tracker"), ("m", "Read this first."), "",
        ("s", "DISCLAIMER"),
        "Not financial, trading, or investment advice; educational calculation tool only.",
        "Not affiliated with, endorsed by, or sponsored by any prop firm, exchange (CME Group), or platform named.",
        "Prop firm rules change without notice. Every preset shows source_url, checked_date (2026-10-14 for v0.1) and page date; verify against the firm's current rules and your dashboard before trading. Presets are not guaranteed permanent or complete; \"partial\" presets require user input.",
        "The tracker relies on user-entered balances; it cannot see intraday order of events and can differ from the firm's real-time system. The firm's own calculation is authoritative.",
        "Spreadsheet floating-point arithmetic; values are rounded to cents conservatively.", "",
        ("m", "Spec: tracker v0.1.0 / oracle v0.2.0. No macros, no scripts, no external links or data connections.")], tab=RED)

    # ---------------- How to use ----------------
    text_sheet(wb, "How to use", [("h", "How to use"),
        ("s", "REQUIREMENTS"),
        "Microsoft Excel 2019, Excel 2021 or Microsoft 365 (uses MAXIFS and TEXTJOIN; Excel 2016 and earlier show #NAME? and are NOT supported).",
        "Tested: formulas were recalculated and checked in LibreOffice only. Excel and Google Sheets have NOT been tested; treat both as unverified until you confirm the results yourself.",
        ("s", "GOOGLE SHEETS IMPORT (UNTESTED)"),
        "1. Open drive.google.com, click New > File upload and choose Floorline-Tracker.xlsx.",
        "2. Right-click the uploaded file > Open with > Google Sheets (or set Drive Settings > 'Convert uploads' before uploading).",
        "3. In Sheets: File > Save as Google Sheets if it opened in Office-compatibility mode, then work in the converted copy.",
        "4. Check the Accounts tab: Check column shows OK for filled rows and no cell shows #NAME? or #ERROR!. Compare a few results with your firm dashboard before relying on it.",
        "5. Not verified in Sheets: whether sheet protection, dropdowns, data validation and colour rules survive the import. Pasted values can bypass dropdowns and validation; the formulas check many inputs, but not every possible mistake.",
        ("s", "DAILY ROUTINE"),
        "1. Accounts: one row per account (max 10). Enter Account ID and pick a Preset (or Manual). Read the Flags column.",
        "2. Fill any field named in 'PARTIAL PRESET: verify ...' using the override columns D-J (amber flag until resolved).",
        "3. Enter Equity now (incl. open P&L), Day reference balance (the firm's reset reference) and, for sizing, Risk $, Stop ticks, Tick value $ (see Contracts tab).",
        "4. Daily Log: after each session add one row per account: Trading date (firm session date), EOD balance, intraday high and intraday low.",
        "5. Read FLOOR, BINDING ROOM and CONTRACTS on Accounts. Then tick the Checklist. If your firm dashboard disagrees, the firm's number wins.",
        "6. Enter today's date in Accounts!B13 (As of). Flags shows AS-OF DATE MISSING while it is blank and STALE PRESET when a preset was checked more than 30 days before it. The workbook never uses TODAY().",
        "7. If Accounts!B14 shows a red Log check message, a Daily Log row has an unknown or blank account ID; every account shows INCOMPLETE until it is fixed.",
        ("s", "STATUS WORDS"),
        "OK / a number = calculated.  INVALID = a value or rule is wrong (money must be 0 < x <= 100,000,000 with at most 2 decimals; tick value at most 6 decimals).  INCOMPLETE = a required input is missing, incl. a blank max contracts (type NONE for no cap), an incomplete log row, or any unknown-account log row.  UNKNOWN_ACCOUNT = log row whose account ID matches no account.  BREACHED = the floor was hit; rooms and size are blocked.  NONE = no daily loss limit / no cap.",
        ("s", "COLOURS"),
        "Green = buffer above 50% of max drawdown or lock reached.  Amber = 25-50% buffer, partial preset, overrides, stale preset.  Red = under 25%, INVALID or BREACHED.  Blue = sizing was capped or clamped to the room.",
        ("s", "LIMITS"),
        "Intraday trailing: a daily row cannot encode whether the low came before the high; the tracker assumes the high came first (higher, more conservative floor). Percent daily limits and payout/withdrawal floor locks must be entered manually. Futures only. 10 accounts, 1,000 log rows.",
        "Matching ignores letter case: account IDs must be unique ignoring case (p16 and P16 are duplicates), log row p16 belongs to account P16, and none / None count as NONE. Spaces are NOT ignored: 'Static ' with a trailing space is INVALID."], tab=BLUE)

    # ---------------- Accounts ----------------
    ws = wb.create_sheet("Accounts"); base_sheet(ws, BRAND)
    paint(ws, 16, len(ACC_HEAD))
    calc = {c for c, _, _ in ACC_HEAD if c not in INPUT_ACC}
    header(ws, ACC_HEAD, calc)
    for r in range(2, NA + 1):
        ws.row_dimensions[r].height = 20
        for col, f in account_formulas(r).items(): ws[f"{col}{r}"] = f
        for col, _, _ in ACC_HEAD:
            c = ws[f"{col}{r}"]
            inp = col in INPUT_ACC
            c.fill = F_IN if inp else F_BG
            c.border = B_IN if inp else B_CELL
            c.protection = Protection(locked=not inp)
            c.alignment = Alignment(vertical="center", horizontal="left" if col in ("A", "B", "AN", "W", "P", "AE") else "right")
            bold = col in ("Y", "AD", "AG")
            c.font = Font(name=MONO, size=12 if bold else 10, bold=bold, color=INK if (inp or bold) else MUT if col in "PQRSTUV" else INK)
            if col in ("E", "F", "K", "L", "M", "Q", "R", "X", "Y", "AB", "AC", "AD", "AF", "AM", "U", "I"): c.number_format = MONEY
    ws["A13"] = "As of"; ws["A13"].font = Font(name=MONO, size=9, bold=True, color=MUT)
    ws["B13"].fill = F_IN; ws["B13"].border = B_IN; ws["B13"].number_format = "yyyy-mm-dd"; ws["B13"].protection = Protection(locked=False)
    ws["B13"].font = Font(name=MONO, size=10, color=INK); ws["B13"].alignment = Alignment(horizontal="left")
    ws["C13"] = "← today's date (enables the 30-day stale-preset check; no TODAY() used)"; ws["C13"].font = Font(name=MONO, size=9, color=DIM)
    ws["A14"] = "Log check"; ws["A14"].font = Font(name=MONO, size=9, bold=True, color=MUT)
    ws["B14"] = (f'=IF(COUNTIFS({LOGI},"UNKNOWN_ACCOUNT")>0,COUNTIFS({LOGI},"UNKNOWN_ACCOUNT")&'
                 '" Daily Log row(s) with unknown account ID - fix before trading","")')
    ws["B14"].font = Font(name=MONO, size=10, bold=True, color=RED)
    ws.conditional_formatting.add("B14:C14", FormulaRule(formula=['$B$14<>""'], fill=fill(RED), font=Font(color="000000", bold=True)))
    ws["A15"] = "Inputs: shaded cells A–O.  Calculated: P–AN (locked).  FLOOR / BINDING ROOM / CONTRACTS are the numbers to trade by. Educational only; the firm's dashboard is authoritative."
    ws["A15"].font = Font(name=MONO, size=9, color=DIM)
    for col in ("AJ", "AK", "AL"): ws.column_dimensions[col].hidden = True

    rng = f"$A$2:$AN${NA}"
    def cf(ref, formula, **kw): ws.conditional_formatting.add(ref, FormulaRule(formula=[formula], stopIfTrue=False, **kw))
    font = lambda c, b=False: Font(color=c, bold=b)
    # whole-row BREACHED, then cell-level states
    cf(rng, f'$AA2=TRUE', fill=fill(DRED), font=font("FFFFFF", True))
    cf(f"C2:AN{NA}", 'C2="INVALID"', fill=fill(RED), font=font("000000", True))
    cf(f"C2:AN{NA}", 'C2="INCOMPLETE"', fill=fill(AMBER), font=font("000000", True))
    cf(f"W2:W{NA}", 'W2="OK"', font=font(GREEN, True))
    cf(f"Z2:Z{NA}", 'Z2=TRUE', font=font(GREEN, True))
    cf(f"AB2:AB{NA}", 'AND(ISNUMBER(AB2),ISNUMBER(R2),AB2<0.25*R2)', font=font("FF8A3D", True))
    lvl = f'AND(ISNUMBER($AD2),ISNUMBER($R2))'
    cf(f"AD2:AD{NA}", f'AND({lvl},$AD2<=0.25*$R2)', font=font(RED, True))
    cf(f"AD2:AD{NA}", f'AND({lvl},$AD2<=0.5*$R2)', font=font(AMBER, True))
    cf(f"AD2:AD{NA}", f'{lvl}', font=font(GREEN, True))
    cf(f"Y2:Y{NA}", f'{lvl}', font=Font(color=INK, bold=True))
    cf(f"AH2:AI{NA}", 'AH2=TRUE', fill=fill("0E2A40"), font=font(BLUE, True))
    cf(f"AG2:AG{NA}", 'OR($AH2=TRUE,$AI2=TRUE)', font=font(BLUE, True))
    cf(f"AN2:AN{NA}", 'OR(ISNUMBER(SEARCH("PARTIAL",AN2)),ISNUMBER(SEARCH("OVERRIDES",AN2)),ISNUMBER(SEARCH("MISSING",AN2)),ISNUMBER(SEARCH("STALE",AN2)))', font=font(AMBER))
    cf(f"C2:C{NA}", 'C2="verified"', font=font(GREEN, True))
    cf(f"C2:C{NA}", 'C2="partial"', font=font(AMBER, True))
    cf(f"B2:C{NA}", f'ISNUMBER(SEARCH("STALE PRESET",$AN2))', fill=fill("3A2A08"), font=font(AMBER, True))

    dv = lambda **k: DataValidation(showErrorMessage=True, errorStyle="stop", **k)
    v = dv(type="list", formula1="Presets!$A$2:$A$200", allow_blank=True); v.add(f"B2:B{NA}"); ws.add_data_validation(v)
    v = dv(type="list", formula1='"static,eod_trailing,intraday_trailing"', allow_blank=True); v.add(f"D2:D{NA}"); ws.add_data_validation(v)
    v = dv(type="list", formula1='"TRUE,FALSE"', allow_blank=True); v.add(f"H2:H{NA}"); ws.add_data_validation(v)
    money = lambda ref, extra="TRUE": f'AND(ISNUMBER({ref}),ROUND({ref}*100,6)=INT(ROUND({ref}*100,6)),{extra})'
    for col, extra in (("E", "E2>0,E2<=100000000"), ("F", "F2>0,F2<=100000000"), ("K", "K2>0,K2<=100000000"), ("L", "L2>0,L2<=100000000"), ("M", "M2>=0,M2<=100000000")):
        v = dv(type="custom", formula1=money(f"{col}2", extra), allow_blank=True, error="Number with at most 2 decimals, up to 100,000,000"); v.add(f"{col}2:{col}{NA}"); ws.add_data_validation(v)
    v = dv(type="custom", formula1='AND(ISNUMBER(O2),O2>0,O2<=100000,ROUND(O2*1000000,3)=INT(ROUND(O2*1000000,3)))', allow_blank=True, error="Tick value: 0 < x <= 100,000, at most 6 decimals"); v.add(f"O2:O{NA}"); ws.add_data_validation(v)
    v = dv(type="custom", formula1=f'OR(G2="NONE",{money("G2", "G2>=-100000000,G2<=100000000")})', allow_blank=True, error="Number (2 dp, may be <=0) or NONE"); v.add(f"G2:G{NA}"); ws.add_data_validation(v)
    v = dv(type="custom", formula1=f'OR(I2="NONE",{money("I2", "I2>0,I2<=100000000")})', allow_blank=True, error="Dollar amount > 0 or NONE"); v.add(f"I2:I{NA}"); ws.add_data_validation(v)
    v = dv(type="custom", formula1='OR(J2="NONE",AND(ISNUMBER(J2),J2>=0,J2=INT(J2)))', allow_blank=True, error="Whole number >= 0 or NONE"); v.add(f"J2:J{NA}"); ws.add_data_validation(v)
    v = dv(type="whole", operator="greaterThanOrEqual", formula1="1", allow_blank=True, error="Whole number >= 1"); v.add(f"N2:N{NA}"); ws.add_data_validation(v)
    v = dv(type="date", operator="greaterThan", formula1="1", allow_blank=True); v.add("B13"); ws.add_data_validation(v)
    ws.protection.sheet = True; ws.protection.formatColumns = False; ws.protection.formatRows = False
    for i, a in enumerate(accounts, 2):
        for col, val in a.items(): ws[f"{col}{i}"] = val
    if demo_asof: ws["B13"] = demo_asof

    # ---------------- Daily Log ----------------
    ws = wb.create_sheet("Daily Log"); base_sheet(ws, INK)
    lcalc = {"F", "G", "H", "I", "J"}
    header(ws, LOG_HEAD, lcalc)
    for r in range(2, NL + 1):
        ws.row_dimensions[r].height = 18
        for col, f in log_formulas(r).items(): ws[f"{col}{r}"] = f
        for col, _, _ in LOG_HEAD:
            c = ws[f"{col}{r}"]; inp = col not in lcalc
            c.fill = F_IN if inp else F_BG; c.border = B_IN if inp else B_CELL
            c.protection = Protection(locked=not inp)
            c.font = Font(name=MONO, size=10, bold=col == "J", color=INK if inp or col in "IJ" else MUT)
            c.alignment = Alignment(horizontal="left" if col in "AI" else "right", vertical="center")
            if col in "CDEGJ": c.number_format = MONEY
            if col == "B": c.number_format = "yyyy-mm-dd"
    for col in ("F", "H"): ws.column_dimensions[col].hidden = True
    lr = f"$A$2:$J${NL}"
    ws.conditional_formatting.add(lr, FormulaRule(formula=['$I2="BREACHED"'], fill=fill(DRED), font=Font(color="FFFFFF", bold=True)))
    ws.conditional_formatting.add(f"A2:J{NL}", FormulaRule(formula=['$I2="UNKNOWN_ACCOUNT"'], fill=fill(RED), font=Font(color="000000", bold=True)))
    ws.conditional_formatting.add(f"I2:J{NL}", FormulaRule(formula=['$I2="INVALID"'], fill=fill(RED), font=Font(color="000000", bold=True)))
    ws.conditional_formatting.add(f"I2:J{NL}", FormulaRule(formula=['$I2="INCOMPLETE"'], fill=fill(AMBER), font=Font(color="000000", bold=True)))
    ws.conditional_formatting.add(f"I2:I{NL}", FormulaRule(formula=['$I2="OK"'], font=Font(color=GREEN, bold=True)))
    v = dv(type="list", formula1=f"Accounts!$A$2:$A${NA}", allow_blank=True); v.add(f"A2:A{NL}"); ws.add_data_validation(v)
    v = dv(type="date", operator="greaterThan", formula1="1", allow_blank=True, error="Enter a valid date"); v.add(f"B2:B{NL}"); ws.add_data_validation(v)
    for col in "CDE":
        v = dv(type="custom", formula1=money(f"{col}2", f"{col}2>0,{col}2<=100000000"), allow_blank=True, error="Number with at most 2 decimals, up to 100,000,000"); v.add(f"{col}2:{col}{NL}"); ws.add_data_validation(v)
    ws.protection.sheet = True
    for i, row in enumerate(logs, 2):
        for col, val in row.items(): ws[f"{col}{i}"] = val

    # ---------------- Presets ----------------
    ws = wb.create_sheet("Presets"); base_sheet(ws, GREEN)
    nr, nc = len(presets), len(presets[0])
    paint(ws, nr, nc)
    numeric = {"start_balance", "dd_amount", "dd_pct", "max_contracts", "max_micros"}
    hdr = presets[0]
    for r, row in enumerate(presets, 1):
        for c, val in enumerate(row, 1):
            cell = ws.cell(r, c)
            # keep tokens as text so PV()'s &"" / VALUE() path works identically in Excel and Sheets
            cell.value = val if val != "" else None
            if r > 1: cell.number_format = "@"
            if r == 1: cell.font = Font(name=MONO, size=9, bold=True, color=MUT); cell.border = B_HEAD
            elif c == 2: cell.font = Font(name=MONO, size=10, bold=True, color=GREEN if val == "verified" else AMBER if val == "partial" else MUT)
    for c, w in zip("ABCDEFGHIJKLMNOP", (52, 9, 16, 11, 9, 7, 8, 7, 8, 7, 7, 40, 60, 11, 11, 7)): ws.column_dimensions[c].width = w
    ws.freeze_panes = "B2"; ws.protection.sheet = True

    # ---------------- Contracts ----------------
    cj = json.load(open(os.path.join(ROOT, "data", "contracts.json")))
    ws = wb.create_sheet("Contracts"); base_sheet(ws, MUT)
    head = ["symbol", "name", "tick_size", "tick_value_usd", "status", "checked_date", "source_url", "note"]
    paint(ws, len(cj["contracts"]) + 3, len(head))
    for c, h in enumerate(head, 1):
        x = ws.cell(1, c, h); x.font = Font(name=MONO, size=9, bold=True, color=MUT); x.border = B_HEAD
    for r, k in enumerate(cj["contracts"], 2):
        for c, h in enumerate(head, 1):
            x = ws.cell(r, c, k[h]); x.number_format = "@"
            if h == "status": x.font = Font(name=MONO, size=10, bold=True, color=AMBER)
            if h == "symbol": x.font = Font(name=MONO, size=10, bold=True, color=INK)
    ws.cell(len(cj["contracts"]) + 3, 1, "All tick values verified indirectly (CME pages bot-blocked); confirm on cmegroup.com. 'flagged' rows need a direct check.").font = Font(name=MONO, size=9, color=AMBER)
    for c, w in zip("ABCDEFGH", (8, 28, 10, 13, 17, 12, 50, 80)): ws.column_dimensions[c].width = w
    ws.freeze_panes = "B2"; ws.protection.sheet = True

    # ---------------- Checklist ----------------
    ws = wb.create_sheet("Checklist", index=3); base_sheet(ws, AMBER)
    items = ["Preset matches the plan purchased (firm, plan, size, purchase date — older purchases may have legacy rules).",
        "Opened source_url; rule text still matches; checked_date within 30 days.",
        "All needs_user / PARTIAL flags resolved.",
        "Lock offset confirmed (0 = start, X = start+X, NONE).",
        "Touch rule confirmed (\"hit/touch\" = TRUE, \"below\" = FALSE).",
        "DLL entered in $ for today's reset (% plans: firm dashboard value).",
        "Day reference balance = firm's reset reference (incl./excl. unrealized per firm).",
        "Max contracts entered in the units you trade (micros vs minis).",
        "Today's Daily Log row entered incl. intraday low.",
        "Tick value matches Contracts tab for the instrument.",
        "Firm dashboard floor equals tracker floor; if not, the firm's number wins."]
    paint(ws, len(items) + 8, 5)
    ws["A1"] = "PRE-SESSION CHECKLIST"; ws["A1"].font = Font(name=MONO, size=14, bold=True, color=INK)
    ws["A2"] = "Pick the account, tick each line (type x or ✓). Done = 11/11."; ws["A2"].font = Font(name=MONO, size=9, color=MUT)
    for c, h in zip("ABCD", ("#", "Done", "Account", "Check")):
        x = ws[f"{c}4"]; x.value = h; x.font = Font(name=MONO, size=9, bold=True, color=MUT); x.border = B_HEAD
    for i, t in enumerate(items, 5):
        ws[f"A{i}"] = i - 4; ws[f"A{i}"].font = Font(name=MONO, size=10, bold=True, color=BRAND); ws[f"A{i}"].alignment = Alignment(horizontal="center", vertical="center")
        for col in "BC":
            x = ws[f"{col}{i}"]; x.fill = F_IN; x.border = B_IN; x.protection = Protection(locked=False)
            x.alignment = Alignment(horizontal="center", vertical="center"); x.font = Font(name=MONO, size=12, bold=True, color=GREEN)
        ws[f"C{i}"].font = Font(name=MONO, size=10, color=INK)
        ws[f"D{i}"] = t; ws[f"D{i}"].font = Font(name=MONO, size=10, color=INK)
        ws[f"D{i}"].alignment = Alignment(wrap_text=True, vertical="center"); ws.row_dimensions[i].height = 30
    n = 5 + len(items) + 1
    ws[f"C{n}"] = "Done"; ws[f"C{n}"].font = Font(name=MONO, size=9, bold=True, color=MUT); ws[f"C{n}"].alignment = Alignment(horizontal="right")
    ws[f"D{n}"] = f'=COUNTIFS(B5:B{4+len(items)},"<>")&" / {len(items)}"'
    ws[f"D{n}"].font = Font(name=MONO, size=14, bold=True, color=INK)
    ws.conditional_formatting.add(f"D{n}", FormulaRule(formula=[f'COUNTIFS(B5:B{4+len(items)},"<>")={len(items)}'], font=Font(color=GREEN, bold=True)))
    ws.conditional_formatting.add(f"A5:D{4+len(items)}", FormulaRule(formula=['$B5<>""'], font=Font(color=DIM)))
    v = dv(type="list", formula1='"✓,x"', allow_blank=True); v.add(f"B5:B{4+len(items)}"); ws.add_data_validation(v)
    v = dv(type="list", formula1=f"Accounts!$A$2:$A${NA}", allow_blank=True); v.add(f"C5:C{4+len(items)}"); ws.add_data_validation(v)
    for c, w in zip("ABCD", (5, 7, 14, 100)): ws.column_dimensions[c].width = w
    ws.protection.sheet = True

    wb.active = 0
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)
    return path

DEMO_ACC = [
    {"A": "TS-50K-01", "B": "Topstep | Trading Combine | 50000 [P001]", "I": 1000, "J": 50, "K": 51240.5, "L": 51550.5, "M": 300, "N": 12, "O": 1.25},
    {"A": "APEX-50", "B": "Apex Trader Funding | Intraday Trailing Evaluation | 50000 [P006]", "G": "NONE", "K": 50410, "M": 250, "N": 16, "O": 0.5},
    {"A": "LUCID-25", "B": "Lucid Trading | LucidFlex (eval + funded) | 25000 [P018]", "I": "NONE", "J": "NONE", "K": 25120, "M": 100, "N": 8, "O": 1.25},
    {"A": "TS-100K", "B": "Topstep | Trading Combine | 100000 [P002]", "I": "NONE", "K": 97050, "M": 400, "N": 10, "O": 5},
    {"A": "MANUAL-1", "B": "Manual", "D": "static", "E": 25000, "F": 1000, "G": "NONE", "H": True, "I": "NONE", "J": 10, "K": 24300, "M": 200, "N": 20, "O": 1.25},
]
d = datetime.date
DEMO_LOG = [
    {"A": "TS-50K-01", "B": d(2026, 10, 12), "C": 51100, "D": 51320, "E": 50880},
    {"A": "TS-50K-01", "B": d(2026, 10, 13), "C": 51550.5, "D": 51700, "E": 51010},
    {"A": "APEX-50", "B": d(2026, 10, 12), "C": 50620, "D": 50980, "E": 50300},
    {"A": "APEX-50", "B": d(2026, 10, 13), "C": 50410, "D": 50700, "E": 49990},
    {"A": "LUCID-25", "B": d(2026, 10, 13), "C": 25120, "D": 25400, "E": 24980},
    {"A": "TS-100K", "B": d(2026, 10, 12), "C": 99800, "D": 100250, "E": 98900},
    {"A": "TS-100K", "B": d(2026, 10, 13), "C": 97050, "D": 99900, "E": 96950},
    {"A": "MANUAL-1", "B": d(2026, 10, 13), "C": 24300, "D": 24600, "E": 24150},
]

if __name__ == "__main__":
    if "--demo" in sys.argv:
        out = sys.argv[sys.argv.index("--demo") + 1]
        print("wrote", build(out, DEMO_ACC, DEMO_LOG, demo_asof=d(2026, 10, 14)))
    else:
        print("wrote", build(os.path.join(HERE, "Floorline-Tracker.xlsx")))
