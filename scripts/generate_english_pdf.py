#!/usr/bin/env python3
"""
Crypto AI Agent — English PDF Report Generator (Dark Theme)
Usage: python3 scripts/generate_english_pdf.py <input.json> <output.pdf>

Generates a dark-themed A4 PDF matching the Dart brand system.
Uses headless Chrome for HTML-to-PDF conversion.
"""

import sys
import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from html import escape

# ── Trading tips pool (deterministic by date) ────────────────────────────────
TIPS = [
    "Always define your stop-loss before entering a trade.",
    "Never risk more than 2% of your capital on a single trade.",
    "Trade with the trend, not against it.",
    "Remove emotions from trading — greed and fear are a trader's worst enemies.",
    "Patience is one of the most important trading skills; wait for the ideal setup.",
    "Never immediately open a new trade to recover a loss.",
    "Risk control matters more than chasing profits.",
    "Log every trade and review your journal weekly.",
    "In choppy, trendless markets, reduce your position size.",
    "Before entering any trade, plan for the scenario where you are wrong.",
    "Never put all your capital into a single asset.",
    "Technical analysis is a tool, not a crystal ball — never ignore risk management.",
    "When the market is uncertain, the best trade is no trade.",
    "Small, consistent gains protect you from large losses over the long run.",
    "Always confirm signals across multiple timeframes.",
    "Rushing in without enough confirmation is the most common beginner mistake.",
    "Size your position based on the distance to your stop-loss, not the other way around.",
    "Even the best setups fail sometimes — that is completely normal.",
    "Negative funding rates can signal a buying opportunity.",
    "High leverage does not replace confidence in your analysis; use less leverage, trade longer.",
    "Review your open positions before you sleep.",
    "Check market liquidity; slippage is higher in thin markets.",
    "Exercise extra caution on days with major economic news releases.",
    "Stop blindly following signals from others — develop your own analysis.",
    "Factor in commissions and fees when calculating profit and loss.",
    "Rising volume in the direction of the trend signals strong momentum.",
    "When the market moves against your position, stick to your original plan.",
    "Success in trading requires consistent practice and honest review of mistakes.",
    "Never trade with borrowed money or money you cannot afford to lose.",
    "During global market holidays, liquidity drops — watch for false breakouts.",
    "Fewer, higher-quality setups beat many low-quality ones.",
    "Every loss is a lesson; learn from it and move forward.",
]


def pick_tip(date_str: str) -> str:
    idx = hash(date_str) % len(TIPS)
    return TIPS[idx]


def esc(s):
    return escape(str(s or ""))


LOGO_SVG = """<svg viewBox="0 0 64 64" width="22" height="22">
  <g fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="square" stroke-linejoin="miter">
    <path d="M12 52 L44 20"/>
    <path d="M30 20 L44 20 L44 34"/>
    <path d="M12 52 L20 52 M12 52 L12 44" opacity="0.55"/>
  </g>
</svg>"""


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --ink-900:#05070d; --ink-850:#080b14; --ink-800:#0b0f1a; --ink-700:#10172a;
  --ink-600:#1a2340; --ink-500:#2a3558; --ink-400:#4a5578; --ink-300:#7a86a8;
  --ink-200:#b8c1de; --ink-100:#e4e8f5; --ink-050:#f4f6fc;
  --signal-700:#1e4fb8; --signal-500:#3b82f6; --signal-300:#93c5fd;
  --long-300:#6ee7b7; --short-300:#fca5a5; --warn:#fbbf24;
  --sans:'Inter Tight','Inter',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,Menlo,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{
  background:var(--ink-900);
  font-family:var(--sans);
  color:var(--ink-100);
  -webkit-font-smoothing:antialiased;
  -webkit-print-color-adjust:exact !important;
  print-color-adjust:exact !important;
}
@page { size: A4; margin: 0; }
.page{
  width:210mm; height:297mm;
  background:var(--ink-900);
  color:var(--ink-100);
  padding:18mm 20mm;
  position:relative;
  font-size:12px;
  display:flex;flex-direction:column;
  page-break-after:always;
  overflow:hidden;
}
.page:last-child{page-break-after:auto;}

.pdf-head{
  display:flex;justify-content:space-between;align-items:flex-start;
  padding-bottom:14px;margin-bottom:22px;
  border-bottom:1px solid var(--ink-600);
}
.pdf-head-l{display:flex;align-items:center;gap:10px;}
.pdf-head-l svg{width:22px;height:22px;color:var(--ink-050);}
.pdf-head-l .wm{font-size:18px;font-weight:500;letter-spacing:-0.03em;color:var(--ink-050);}
.pdf-head-r{
  font-family:var(--mono);font-size:10px;color:var(--ink-400);
  letter-spacing:.1em;text-transform:uppercase;text-align:right;
}
.pdf-head-r .date{color:var(--ink-100);font-weight:500;}

.kicker{
  font-family:var(--mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.14em;color:var(--signal-300);margin-bottom:10px;
}
.title{font-size:38px;font-weight:300;letter-spacing:-.028em;line-height:1;color:var(--ink-050);margin-bottom:16px;}
.title em{font-style:italic;color:var(--signal-300);font-weight:300;}
.deck{font-size:13px;color:var(--ink-200);line-height:1.55;max-width:58ch;margin-bottom:20px;}

.tip{
  display:flex;align-items:flex-start;gap:10px;
  padding:10px 14px;border-radius:3px;font-size:11px;
  margin-bottom:18px;line-height:1.5;
  background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.15);color:var(--ink-200);
}
.tip .ico{flex-shrink:0;font-size:14px;margin-top:1px;}

.banner{
  display:flex;align-items:flex-start;gap:10px;
  padding:10px 14px;border-radius:3px;font-size:11px;
  margin-bottom:18px;line-height:1.5;
}
.banner-warn{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);color:var(--warn);}
.banner-macro{background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.25);color:var(--signal-300);}
.banner .ico{
  width:14px;height:14px;flex-shrink:0;margin-top:1px;
  border:1.5px solid currentColor;border-radius:50%;
  display:grid;place-items:center;font-size:9px;font-weight:700;
}

.section-head{
  display:flex;align-items:baseline;gap:12px;
  margin-bottom:14px;padding-bottom:8px;
  border-bottom:1px solid var(--ink-700);
}
.section-num{font-family:var(--mono);font-size:10px;color:var(--ink-400);letter-spacing:.14em;}
.section-title{font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:.14em;color:var(--ink-100);}

.btc-card{
  border:1px solid var(--ink-600);border-radius:3px;padding:18px;margin-bottom:18px;
  background:linear-gradient(180deg,rgba(59,130,246,.04),transparent);
}
.btc-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--ink-700);}
.sym-row{display:flex;align-items:center;gap:10px;}
.chip{
  width:32px;height:32px;border-radius:50%;
  background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3);
  display:grid;place-items:center;
  font-family:var(--mono);font-size:10px;color:var(--signal-300);font-weight:600;
}
.sym-row .name{font-size:14px;font-weight:500;color:var(--ink-050);letter-spacing:-0.01em;}
.sym-row .sub{font-family:var(--mono);font-size:9.5px;color:var(--ink-400);letter-spacing:.08em;text-transform:uppercase;}
.price-right{text-align:right;}
.price-right .p{font-family:var(--mono);font-size:17px;font-weight:500;color:var(--ink-050);letter-spacing:-.01em;}
.price-right .lbl{font-family:var(--mono);font-size:9px;color:var(--ink-400);letter-spacing:.12em;text-transform:uppercase;}

.summary{font-size:12px;line-height:1.55;color:var(--ink-200);margin-bottom:16px;}

.scenario-pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;}
.scenario-pair.one{grid-template-columns:1fr;}
.sc-box{background:var(--ink-850);border:1px solid var(--ink-700);border-radius:3px;padding:12px;font-family:var(--mono);font-size:11px;}
.sc-head{display:flex;justify-content:space-between;padding-bottom:8px;margin-bottom:8px;border-bottom:1px dashed var(--ink-700);}
.sc-head .ttl{font-family:var(--sans);font-size:11px;font-weight:500;color:var(--ink-100);}
.sc-head .rr{color:var(--signal-300);font-weight:500;}
.sc-row{display:flex;justify-content:space-between;padding:3px 0;}
.sc-row .k{color:var(--ink-400);font-size:10px;letter-spacing:.06em;text-transform:uppercase;}
.sc-row .v{color:var(--ink-050);font-weight:500;}
.sc-row.trig .v{color:var(--signal-300);}
.sc-row.sl .v{color:var(--short-300);}
.sc-row.tp .v{color:var(--long-300);}

.plain{
  font-size:12px;line-height:1.6;color:var(--ink-200);
  padding:14px 16px;border-left:2px solid var(--signal-500);
  background:rgba(59,130,246,.04);border-radius:0 3px 3px 0;
}
.plain .lbl{font-family:var(--mono);font-size:9px;color:var(--signal-300);letter-spacing:.14em;text-transform:uppercase;display:block;margin-bottom:6px;}

.coin-card{border:1px solid var(--ink-600);border-radius:3px;padding:16px;margin-bottom:12px;}
.coin-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
.coin-badges{display:flex;gap:6px;}
.sym-s{
  width:28px;height:28px;border-radius:50%;
  background:var(--ink-700);border:1px solid var(--ink-600);
  display:grid;place-items:center;
  font-family:var(--mono);font-size:9px;font-weight:600;color:var(--ink-200);
}

.badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:3px 9px;font-family:var(--mono);font-size:9.5px;
  font-weight:500;letter-spacing:.1em;text-transform:uppercase;
  border-radius:2px;border:1px solid;
}
.badge.long{color:var(--long-300);border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.08);}
.badge.short{color:var(--short-300);border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.08);}
.badge.high{color:var(--signal-300);border-color:rgba(59,130,246,.35);background:rgba(59,130,246,.08);}
.badge.med{color:#fbbf24;border-color:rgba(245,158,11,.3);background:rgba(245,158,11,.08);}
.badge.low{color:var(--ink-300);border-color:var(--ink-500);background:var(--ink-700);}
.badge.dot::before{content:'';display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;}

.open-pos{
  display:grid;grid-template-columns:110px 1fr 80px;gap:14px;
  padding:12px 0;border-top:1px solid var(--ink-700);font-size:11.5px;
}
.open-pos:first-child{border-top:0;}
.op-sym{display:flex;flex-direction:column;gap:4px;}
.op-sym .sym-inner{display:flex;align-items:center;gap:8px;}
.op-sym .dot{
  width:18px;height:18px;border-radius:50%;
  background:var(--ink-700);border:1px solid var(--ink-600);
  display:grid;place-items:center;
  font-family:var(--mono);font-size:8px;color:var(--ink-200);
}
.op-sym .nm{font-weight:500;color:var(--ink-100);font-size:12px;}
.op-sym .entry{font-family:var(--mono);font-size:9.5px;color:var(--ink-400);letter-spacing:.06em;}
.op-guide{color:var(--ink-200);line-height:1.5;}
.op-status{
  font-family:var(--mono);font-size:9px;letter-spacing:.08em;
  text-transform:uppercase;text-align:right;color:var(--ink-300);padding-top:2px;
}
.op-status.profit{color:var(--long-300);}
.op-status.loss{color:var(--short-300);}

.conclusion{padding:18px;border:1px solid var(--ink-600);border-radius:3px;background:var(--ink-850);}
.conclusion h5{font-family:var(--mono);font-size:10px;color:var(--signal-300);letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;}
.conclusion p{font-size:12px;line-height:1.6;color:var(--ink-100);}

.pdf-foot{
  margin-top:auto;padding-top:14px;border-top:1px solid var(--ink-600);
  display:flex;justify-content:space-between;
  font-family:var(--mono);font-size:9px;color:var(--ink-400);
  letter-spacing:.1em;text-transform:uppercase;
}
.pdf-foot .pg{color:var(--ink-200);}

.empty-state{
  padding:18px;border:1px dashed var(--ink-500);border-radius:3px;
  font-size:12px;color:var(--ink-300);line-height:1.55;text-align:center;
}

.disclaimer{
  margin-top:auto;padding-top:14px;
  font-family:var(--mono);font-size:8px;color:var(--ink-400);
  letter-spacing:.04em;line-height:1.5;text-align:center;
  border-top:1px solid var(--ink-700);
  padding-top:10px;margin-bottom:8px;
}
"""


def header_html(date_str):
    return f"""
    <header class="pdf-head">
      <div class="pdf-head-l">{LOGO_SVG}<span class="wm">Dart</span></div>
      <div class="pdf-head-r">
        <div class="date">{esc(date_str)}</div>
        <div>Daily Market Brief</div>
      </div>
    </header>"""


def footer_html(pg, total):
    return f"""
    <footer class="pdf-foot">
      <span>Dart Team &middot; Not financial advice</span>
      <span class="pg">{str(pg).zfill(2)} / {str(total).zfill(2)}</span>
    </footer>"""


def banners_html(data):
    out = ""
    mood = data.get("market_mood", "")
    if "weekend" in mood.lower():
        out += """
    <div class="banner banner-warn">
      <span class="ico">!</span>
      <span><strong>WEEKEND CAUTION</strong> — traditional markets are closed. Volume is lower and price moves can be sharper. Trade smaller sizes than usual.</span>
    </div>"""
    if "economic event" in mood.lower() or "macro" in mood.lower():
        out += """
    <div class="banner banner-macro">
      <span class="ico">i</span>
      <span><strong>MACRO WINDOW</strong> — a major US economic event is coming up soon. Consider waiting until after the event before opening new trades.</span>
    </div>"""
    return out


def scenario_box_html(label, s, direction=""):
    if not s:
        return ""
    return f"""
      <div class="sc-box">
        <div class="sc-head">
          <span class="ttl">{esc(label)}{(' \u00b7 ' + direction) if direction else ''}</span>
          <span class="rr">R:R {esc(s.get('rr', '—'))}</span>
        </div>
        <div class="sc-row trig"><span class="k">Trigger</span><span class="v">${esc(s.get('trigger', '—'))}</span></div>
        <div class="sc-row sl"><span class="k">Stop-loss</span><span class="v">${esc(s.get('sl', '—'))}</span></div>
        <div class="sc-row tp"><span class="k">Take-profit</span><span class="v">${esc(s.get('tp', '—'))}</span></div>
      </div>"""


def btc_block_html(btc):
    if not btc:
        return ""
    is_q = btc.get("mode") == "qualified"
    price_html = ""
    if btc.get("current_price"):
        price_html = f"""
        <div class="price-right">
          <div class="p">${esc(btc['current_price'])}</div>
          <div class="lbl">Live price</div>
        </div>"""

    scenarios_html = ""
    if is_q:
        scenarios_html = f"""
      <div class="scenario-pair">
        {scenario_box_html("Scenario A", btc.get("scenario_a"), "Long")}
        {scenario_box_html("Scenario B", btc.get("scenario_b"), "Short")}
      </div>"""

    return f"""
    <div class="btc-card">
      <div class="btc-top">
        <div class="sym-row">
          <div class="chip">BTC</div>
          <div>
            <div class="name">Bitcoin</div>
            <div class="sub">{'Qualified setup' if is_q else 'Range watch &middot; no entry'}</div>
          </div>
        </div>
        {price_html}
      </div>
      <div class="summary">{esc(btc.get('technical_summary', ''))}</div>
      {scenarios_html}
      <div class="plain">
        <span class="lbl">In plain language</span>
        {esc(btc.get('simple_conclusion', ''))}
      </div>
    </div>"""


def coin_block_html(coin, idx):
    direction = coin.get("direction", "LONG")
    confidence = coin.get("confidence", "MEDIUM")
    dir_class = "long" if direction == "LONG" else "short"
    conf_class = "high" if confidence == "HIGH" else ("med" if confidence == "MEDIUM" else "low")
    dir_label = direction.lower()
    alt_dir = "Long" if direction == "LONG" else "Short"

    return f"""
    <div class="coin-card">
      <div class="coin-top">
        <div class="sym-row">
          <div class="sym-s">{esc(coin.get('symbol', ''))}</div>
          <div>
            <div class="name">{esc(coin.get('symbol', ''))}</div>
            <div class="sub">Setup N\u00ba {str(idx).zfill(2)} \u00b7 {dir_label} \u00b7 {confidence.lower()} conviction</div>
          </div>
        </div>
        <div class="coin-badges">
          <span class="badge {dir_class} dot">{esc(direction)}</span>
          <span class="badge {conf_class}">{esc(confidence)}</span>
        </div>
      </div>
      <div class="summary">{esc(coin.get('technical_summary', ''))}</div>
      <div class="scenario-pair">
        {scenario_box_html("Scenario A", coin.get("scenario_a"), alt_dir)}
        {scenario_box_html("Scenario B", coin.get("scenario_b"), alt_dir + " \u00b7 alt")}
      </div>
      <div class="plain">
        <span class="lbl">In plain language</span>
        {esc(coin.get('simple_conclusion', ''))}
      </div>
    </div>"""


def open_pos_html(p):
    direction = p.get("direction", "LONG")
    dir_class = "long" if direction == "LONG" else "short"
    status = p.get("current_status", "")
    status_class = "profit" if "profit" in status.lower() else ("loss" if "loss" in status.lower() else "")
    import re
    status_label = re.sub(r"^currently\s+", "", status, flags=re.IGNORECASE)
    status_label = re.sub(r"^at a ", "", status_label, flags=re.IGNORECASE).strip()

    return f"""
    <div class="open-pos">
      <div class="op-sym">
        <div class="sym-inner">
          <div class="dot">{esc(p.get('symbol', ''))}</div>
          <div class="nm">{esc(p.get('symbol', ''))}</div>
        </div>
        <div><span class="badge {dir_class} dot">{esc(direction)}</span></div>
        <div class="entry">@ ${esc(p.get('entry_price', ''))}</div>
      </div>
      <div class="op-guide">{esc(p.get('guidance', ''))}</div>
      <div class="op-status {status_class}">{esc(status_label or status)}</div>
    </div>"""


def build_html(data: dict) -> str:
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    tip_text = data.get("tip") or pick_tip(date_str)
    coins = data.get("coins", [])
    open_positions = data.get("open_positions_guidance", [])
    daily = data.get("daily_conclusion", "")
    market_mood = data.get("market_mood", "")

    # Split mood into lead sentence and rest
    import re
    mood_sentences = re.split(r'(?<=[.!?])\s+', market_mood)
    mood_lead = mood_sentences[0] if mood_sentences else "Daily market brief."
    mood_rest = " ".join(mood_sentences[1:]) if len(mood_sentences) > 1 else ""

    total_pages = 3

    # ── Page 1 — Cover + BTC Watch
    page1 = f"""
  <section class="page">
    {header_html(date_str)}
    <div class="kicker">Market mood</div>
    <h1 class="title">{esc(mood_lead)}</h1>
    {"<p class='deck'>" + esc(mood_rest) + "</p>" if mood_rest else ""}
    <div class="tip">
      <span class="ico">💡</span>
      <span>{esc(tip_text)}</span>
    </div>
    {banners_html(data)}
    <div class="section-head">
      <span class="section-num">&sect; 01</span>
      <span class="section-title">BTC Watch</span>
    </div>
    {btc_block_html(data.get("btc_watch"))}
    {footer_html(1, total_pages)}
  </section>"""

    # ── Page 2 — Top Coin Scenarios
    coins_html = ""
    if coins:
        for i, coin in enumerate(coins, 1):
            coins_html += coin_block_html(coin, i)
    else:
        coins_html = '<div class="empty-state">No non-BTC setups qualified today. Our agent screens the top liquid alts each morning; when none meet the confidence threshold, we pass rather than force a trade.</div>'

    page2 = f"""
  <section class="page">
    {header_html(date_str)}
    <div class="section-head">
      <span class="section-num">&sect; 02</span>
      <span class="section-title">Top coin scenarios</span>
    </div>
    {coins_html}
    {footer_html(2, total_pages)}
  </section>"""

    # ── Page 3 — Open Positions + Conclusion
    pos_html = ""
    if open_positions:
        for p in open_positions:
            pos_html += open_pos_html(p)
    else:
        pos_html = '<div class="empty-state">No open positions require guidance today. All tracked positions are holding inside their original plans — no stop-loss, take-profit, or exit adjustments recommended.</div>'

    page3 = f"""
  <section class="page">
    {header_html(date_str)}
    <div class="section-head">
      <span class="section-num">&sect; 03</span>
      <span class="section-title">Open positions — guidance</span>
    </div>
    <div style="margin-bottom:24px;">
      {pos_html}
    </div>
    <div class="section-head">
      <span class="section-num">&sect; 04</span>
      <span class="section-title">Daily conclusion</span>
    </div>
    <div class="conclusion">
      <h5>Today, in one breath</h5>
      <p>{esc(daily)}</p>
    </div>
    <div class="disclaimer">
      This report is for informational purposes only and does not constitute financial advice.
      The trader is solely responsible for their own trading decisions. &copy; Dart Team
    </div>
    {footer_html(3, total_pages)}
  </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dart — Daily Market Brief</title>
<style>{CSS}</style>
</head>
<body>
{page1}
{page2}
{page3}
</body>
</html>"""


def build_pdf(data: dict, output_path: str):
    html_content = build_html(data)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_content)
        tmp_html = f.name

    try:
        chrome_cmd = None
        for candidate in ["google-chrome", "chromium", "chromium-browser"]:
            try:
                subprocess.run([candidate, "--version"], capture_output=True, check=True)
                chrome_cmd = candidate
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not chrome_cmd:
            print("ERROR: No Chrome/Chromium found. Install google-chrome or chromium.")
            sys.exit(1)

        result = subprocess.run([
            chrome_cmd,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={output_path}",
            "--print-to-pdf-no-header",
            f"file://{tmp_html}",
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Chrome stderr: {result.stderr}")

        if os.path.exists(output_path):
            print(f"PDF saved → {output_path}")
        else:
            print(f"ERROR: PDF was not created. Chrome output: {result.stderr}")
            sys.exit(1)
    finally:
        os.unlink(tmp_html)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/generate_english_pdf.py <input.json> <output.pdf>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    build_pdf(payload, output_path)
