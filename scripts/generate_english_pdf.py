#!/usr/bin/env python3
"""
Crypto AI Agent — English PDF Report Generator
Usage: python3 scripts/generate_english_pdf.py <input.json> <output.pdf>

Input JSON schema:
{
  "date": "YYYY-MM-DD",
  "coins": [
    {
      "symbol": "BTC",
      "direction": "LONG",          // or "SHORT"
      "confidence": "HIGH",         // HIGH | MEDIUM | LOW
      "technical_summary": "...",   // 2-3 sentences, English
      "scenario_a": { "trigger": "65000", "sl": "64200", "tp": "67400", "rr": "3.0" },
      "scenario_b": { "trigger": "63500", "sl": "64300", "tp": "61000", "rr": "2.5" },
      "simple_conclusion": "..."    // 2-3 sentences for beginners, English
    }
  ],
  "daily_conclusion": "..."         // 3-5 sentences overall summary, English
}
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# ── Dependency check ────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
    )
    from reportlab.lib.styles import ParagraphStyle
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}")
    print("Run:  bash scripts/setup.sh")
    sys.exit(1)

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
    """Pick a deterministic tip based on the date."""
    idx = hash(date_str) % len(TIPS)
    return TIPS[idx]


# ── Color palette ────────────────────────────────────────────────────────────
C_DARK_BLUE  = colors.HexColor("#0f3460")
C_MID_BLUE   = colors.HexColor("#1a4a7a")
C_GREEN      = colors.HexColor("#1e7a45")
C_TIP_BG     = colors.HexColor("#eef6ff")
C_TIP_BORDER = colors.HexColor("#4a90d9")
C_CONC_BG    = colors.HexColor("#f0fff4")
C_CONC_BORDER= colors.HexColor("#27ae60")
C_GRAY       = colors.HexColor("#666666")
C_LIGHT_LINE = colors.HexColor("#dddddd")


def make_styles() -> dict:
    base      = dict(fontName="Helvetica",      alignment=TA_LEFT)
    bold      = dict(fontName="Helvetica-Bold", alignment=TA_LEFT)
    base_center = {**base, "alignment": TA_CENTER}
    bold_center = {**bold, "alignment": TA_CENTER}

    return {
        "title": ParagraphStyle("title", **bold_center,
            fontSize=15, leading=26,
            textColor=C_DARK_BLUE, spaceAfter=2),

        "subtitle": ParagraphStyle("subtitle", **base_center,
            fontSize=9, leading=16,
            textColor=C_GRAY, spaceAfter=6),

        "tip": ParagraphStyle("tip", **base,
            fontSize=9.5, leading=17,
            backColor=C_TIP_BG, borderColor=C_TIP_BORDER,
            borderWidth=1, borderPadding=(6, 8, 6, 8),
            spaceAfter=10),

        "section_head": ParagraphStyle("section_head", **bold,
            fontSize=11, leading=20,
            textColor=C_DARK_BLUE, spaceBefore=8, spaceAfter=4),

        "coin_head": ParagraphStyle("coin_head", **bold,
            fontSize=10.5, leading=19,
            textColor=C_MID_BLUE, spaceBefore=6, spaceAfter=2),

        "body": ParagraphStyle("body", **base,
            fontSize=9.5, leading=17, spaceAfter=3),

        "scenario_label": ParagraphStyle("scenario_label", **bold,
            fontSize=9, leading=16, textColor=C_DARK_BLUE, spaceAfter=1),

        "scenario_data": ParagraphStyle("scenario_data", **base,
            fontSize=9, leading=15, textColor=C_GRAY, spaceAfter=4),

        "simple": ParagraphStyle("simple", **base,
            fontSize=9.5, leading=17,
            backColor=C_CONC_BG, borderColor=C_CONC_BORDER,
            borderWidth=1, borderPadding=(5, 8, 5, 8),
            spaceAfter=6),

        "daily_conc": ParagraphStyle("daily_conc", **base,
            fontSize=9.5, leading=17, spaceAfter=4),

        "footer": ParagraphStyle("footer", **base_center,
            fontSize=7.5, leading=13,
            textColor=C_GRAY),

        "brand": ParagraphStyle("brand", **bold_center,
            fontSize=20, leading=28,
            textColor=C_DARK_BLUE, spaceAfter=1),
    }


def direction_label(d: str) -> str:
    return "LONG (Buy)" if d == "LONG" else "SHORT (Sell)"


def confidence_label(c: str) -> str:
    return {"HIGH": "High Confidence ✅", "MEDIUM": "Medium Confidence 🟡", "LOW": "Low Confidence ⚠️"}.get(c, c)


def build_pdf(data: dict, output_path: str):
    s = make_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.8*cm,
        leftMargin=1.8*cm,
        topMargin=1.8*cm,
        bottomMargin=1.8*cm,
        title="Daily Crypto Market Report",
        author="Dart Team",
    )

    story = []
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    tip_text = data.get("tip") or pick_tip(date_str)

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Dart Team", s["brand"]))
    story.append(Paragraph("Daily Crypto Market Report", s["title"]))
    story.append(Paragraph(date_str, s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_DARK_BLUE, spaceAfter=6))

    # ── Tip of the day ───────────────────────────────────────────────────────
    story.append(Paragraph(f"💡  Tip of the Day:  {tip_text}", s["tip"]))

    # ── Top coins section ────────────────────────────────────────────────────
    story.append(Paragraph("Best Trading Opportunities Today", s["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_LINE, spaceAfter=4))

    coins = data.get("coins", [])
    for i, coin in enumerate(coins, 1):
        symbol     = coin.get("symbol", "")
        direction  = coin.get("direction", "LONG")
        confidence = coin.get("confidence", "MEDIUM")
        tech       = coin.get("technical_summary", "")
        sa         = coin.get("scenario_a", {})
        sb         = coin.get("scenario_b", {})
        simple     = coin.get("simple_conclusion", "")

        coin_block = []

        # Coin title line
        coin_block.append(Paragraph(
            f"{i}.  {symbol}  —  {direction_label(direction)}  |  {confidence_label(confidence)}",
            s["coin_head"]
        ))

        # Technical brief
        if tech:
            coin_block.append(Paragraph(tech, s["body"]))

        # Scenario A
        coin_block.append(Paragraph("📌  Primary Scenario:", s["scenario_label"]))
        coin_block.append(Paragraph(
            f"Trigger: ${sa.get('trigger','—')}   |   Stop-Loss: ${sa.get('sl','—')}   |   Take-Profit: ${sa.get('tp','—')}   |   R/R: 1:{sa.get('rr','—')}",
            s["scenario_data"]
        ))

        # Scenario B
        coin_block.append(Paragraph("📌  Counter Scenario:", s["scenario_label"]))
        coin_block.append(Paragraph(
            f"Trigger: ${sb.get('trigger','—')}   |   Stop-Loss: ${sb.get('sl','—')}   |   Take-Profit: ${sb.get('tp','—')}   |   R/R: 1:{sb.get('rr','—')}",
            s["scenario_data"]
        ))

        # Simple conclusion for beginners
        if simple:
            coin_block.append(Paragraph(f"✅  For Beginners:  {simple}", s["simple"]))

        story.append(KeepTogether(coin_block))

        if i < len(coins):
            story.append(HRFlowable(width="60%", thickness=0.4, color=C_LIGHT_LINE,
                                    spaceBefore=2, spaceAfter=2))

    # ── Daily conclusion ─────────────────────────────────────────────────────
    daily = data.get("daily_conclusion", "")
    if daily:
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=1, color=C_GREEN, spaceAfter=4))
        story.append(Paragraph("Overall Market Summary", s["section_head"]))
        story.append(Paragraph(daily, s["daily_conc"]))

    # ── Disclaimer footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_LINE, spaceAfter=4))
    story.append(Paragraph(
        "⚠️  This report is for informational purposes only and does not constitute financial advice. "
        "The trader is solely responsible for their own trading decisions.",
        s["footer"]
    ))
    story.append(Paragraph("© Dart Team", s["footer"]))

    doc.build(story)
    print(f"PDF saved → {output_path}")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/generate_english_pdf.py <input.json> <output.pdf>")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    build_pdf(payload, output_path)
