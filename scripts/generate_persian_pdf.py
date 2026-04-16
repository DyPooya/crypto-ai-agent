#!/usr/bin/env python3
"""
Crypto AI Agent — Persian PDF Report Generator
Usage: python3 scripts/generate_persian_pdf.py <input.json> <output.pdf>

Input JSON schema:
{
  "date": "YYYY-MM-DD",
  "coins": [
    {
      "symbol": "BTC",
      "direction": "LONG",          // or "SHORT"
      "confidence": "HIGH",         // HIGH | MEDIUM | LOW
      "technical_summary": "...",   // 2-3 sentences, Persian
      "scenario_a": { "trigger": "65000", "sl": "64200", "tp": "67400", "rr": "3.0" },
      "scenario_b": { "trigger": "63500", "sl": "64300", "tp": "61000", "rr": "2.5" },
      "simple_conclusion": "..."    // 2-3 sentences for beginners, Persian
    }
  ],
  "daily_conclusion": "..."         // 3-5 sentences overall summary, Persian
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
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
    )
    from reportlab.platypus.flowables import BalancedColumns
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}")
    print("Run:  bash scripts/setup.sh")
    sys.exit(1)

# ── Font paths ───────────────────────────────────────────────────────────────
FONTS_DIR = Path(__file__).parent / "fonts"
FONT_REGULAR = FONTS_DIR / "Vazirmatn-Regular.ttf"
FONT_BOLD    = FONTS_DIR / "Vazirmatn-Bold.ttf"

# ── Persian trading tips (one per day, deterministic) ───────────────────────
TIPS = [
    "همیشه قبل از ورود به معامله، حد ضرر خود را مشخص کنید.",
    "هرگز بیش از ۲٪ از سرمایه‌تان را در یک معامله ریسک نکنید.",
    "با روند بازار معامله کنید، نه برخلاف آن.",
    "احساسات را از معامله جدا کنید؛ طمع و ترس بزرگ‌ترین دشمن معامله‌گر هستند.",
    "صبر یکی از مهم‌ترین مهارت‌های معامله‌گری است؛ منتظر ستاپ ایده‌آل بمانید.",
    "هرگز برای جبران ضرر، بلافاصله معامله جدید باز نکنید.",
    "کنترل ریسک از سود کردن مهم‌تر است.",
    "معاملات خود را در دفترچه ثبت و هر هفته تحلیل کنید.",
    "در بازارهای رنج و بدون روند، حجم موقعیت را کاهش دهید.",
    "قبل از ورود به هر معامله، سناریوی شکست را هم در نظر بگیرید.",
    "هرگز تمام سرمایه خود را روی یک ارز قرار ندهید.",
    "تحلیل تکنیکال ابزار است، نه پیش‌گویی؛ مدیریت سرمایه را فراموش نکنید.",
    "وقتی بازار در شک است، بهترین معامله، عدم معامله است.",
    "سودهای کوچک و مداوم، در بلندمدت از ضررهای بزرگ جلوگیری می‌کنند.",
    "همیشه از چند تایم‌فریم برای تأیید سیگنال استفاده کنید.",
    "ورود عجولانه بدون تأیید کافی، رایج‌ترین اشتباه معامله‌گران تازه‌کار است.",
    "حجم معامله را با فاصله تا حد ضرر تنظیم کنید، نه برعکس.",
    "حتی بهترین ستاپ‌ها هم گاهی شکست می‌خورند؛ این طبیعی است.",
    "نرخ فاندینگ منفی می‌تواند نشانه فرصت خرید باشد.",
    "اهرم بالا جای اطمینان از تحلیل را نمی‌گیرد؛ اهرم کم‌تر، عمر معامله‌گری بیشتر.",
    "قبل از خواب، موقعیت‌های باز خود را بررسی کنید.",
    "نقدینگی بازار را بررسی کنید؛ در بازارهای کم‌عمق اسلیپیج بالاتر است.",
    "در روزهای اعلام اخبار مهم اقتصادی احتیاط بیشتری به خرج دهید.",
    "پیروی کورکورانه از سیگنال‌های دیگران را متوقف کنید؛ تحلیل خود را داشته باشید.",
    "کمیسیون و فی معامله را در محاسبه سود و ضرر لحاظ کنید.",
    "افزایش حجم در جهت روند، نشانه قدرت حرکت است.",
    "وقتی بازار خلاف موقعیت شما حرکت کرد، به برنامه اولیه پایبند بمانید.",
    "موفقیت در معامله‌گری نیاز به تمرین مداوم و بررسی صادقانه اشتباهات دارد.",
    "هرگز با پول قرضی یا پول ضروری زندگی معامله نکنید.",
    "در تعطیلات رسمی بازارهای جهانی، نقدینگی کاهش می‌یابد؛ مراقب حرکات کاذب باشید.",
    "ستاپ کمتر اما با کیفیت‌تر، بهتر از ستاپ‌های زیاد با کیفیت پایین است.",
    "هر ضرر یک درس است؛ از آن یاد بگیرید و جلو بروید.",
]


def pick_tip(date_str: str) -> str:
    """Pick a deterministic tip based on the date."""
    idx = hash(date_str) % len(TIPS)
    return TIPS[idx]


def r(text: str) -> str:
    """Reshape + bidi for correct Persian display in PDF."""
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def register_fonts():
    if not FONT_REGULAR.exists() or not FONT_BOLD.exists():
        print(f"ERROR: Vazirmatn font not found in {FONTS_DIR}/")
        print("Run:  bash scripts/setup.sh")
        sys.exit(1)
    pdfmetrics.registerFont(TTFont("Vazir",      str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("Vazir-Bold", str(FONT_BOLD)))


# ── Color palette ────────────────────────────────────────────────────────────
C_DARK_BLUE  = colors.HexColor("#0f3460")
C_MID_BLUE   = colors.HexColor("#1a4a7a")
C_GREEN      = colors.HexColor("#1e7a45")
C_TIP_BG     = colors.HexColor("#eef6ff")
C_TIP_BORDER = colors.HexColor("#4a90d9")
C_CONC_BG    = colors.HexColor("#f0fff4")
C_CONC_BORDER= colors.HexColor("#27ae60")
C_WARN_BG    = colors.HexColor("#fffbea")
C_WARN_BORDER= colors.HexColor("#e6a817")
C_GRAY       = colors.HexColor("#666666")
C_LIGHT_LINE = colors.HexColor("#dddddd")


def make_styles() -> dict:
    base = dict(fontName="Vazir", alignment=TA_RIGHT)
    bold = dict(fontName="Vazir-Bold", alignment=TA_RIGHT)

    return {
        "title": ParagraphStyle("title", **bold,
            fontSize=15, leading=26, alignment=TA_CENTER,
            textColor=C_DARK_BLUE, spaceAfter=2),

        "subtitle": ParagraphStyle("subtitle", **base,
            fontSize=9, leading=16, alignment=TA_CENTER,
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

        "footer": ParagraphStyle("footer", **base,
            fontSize=7.5, leading=13, alignment=TA_CENTER,
            textColor=C_GRAY),
    }


def direction_fa(d: str) -> str:
    return "خرید (LONG)" if d == "LONG" else "فروش (SHORT)"


def confidence_fa(c: str) -> str:
    return {"HIGH": "اطمینان بالا ✅", "MEDIUM": "اطمینان متوسط 🟡", "LOW": "اطمینان پایین ⚠️"}.get(c, c)


def build_pdf(data: dict, output_path: str):
    register_fonts()
    s = make_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.8*cm,
        leftMargin=1.8*cm,
        topMargin=1.8*cm,
        bottomMargin=1.8*cm,
        title="گزارش روزانه بازار کریپتو",
        author="Crypto AI Agent",
    )

    story = []
    date_str = data.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    tip_text = data.get("tip") or pick_tip(date_str)

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph(r("گزارش روزانه بازار کریپتو"), s["title"]))
    story.append(Paragraph(r(date_str + " | Crypto AI Agent"), s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_DARK_BLUE, spaceAfter=6))

    # ── Tip of the day ───────────────────────────────────────────────────────
    story.append(Paragraph(r(f"💡  نکته روز:  {tip_text}"), s["tip"]))

    # ── Top coins section ────────────────────────────────────────────────────
    story.append(Paragraph(r("بهترین فرصت‌های معاملاتی امروز"), s["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_LINE, spaceAfter=4))

    for i, coin in enumerate(data.get("coins", []), 1):
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
            r(f"{i}.  {symbol}  —  {direction_fa(direction)}  |  {confidence_fa(confidence)}"),
            s["coin_head"]
        ))

        # Technical brief
        if tech:
            coin_block.append(Paragraph(r(tech), s["body"]))

        # Scenario A
        coin_block.append(Paragraph(r("📌  سناریوی اصلی:"), s["scenario_label"]))
        coin_block.append(Paragraph(
            r(f"ورود: ${sa.get('trigger','—')}   |   حد ضرر: ${sa.get('sl','—')}   |   هدف سود: ${sa.get('tp','—')}   |   R/R: 1:{sa.get('rr','—')}"),
            s["scenario_data"]
        ))

        # Scenario B
        coin_block.append(Paragraph(r("📌  سناریوی جایگزین:"), s["scenario_label"]))
        coin_block.append(Paragraph(
            r(f"ورود: ${sb.get('trigger','—')}   |   حد ضرر: ${sb.get('sl','—')}   |   هدف سود: ${sb.get('tp','—')}   |   R/R: 1:{sb.get('rr','—')}"),
            s["scenario_data"]
        ))

        # Simple conclusion for beginners
        if simple:
            coin_block.append(Paragraph(r(f"✅  برای تازه‌کاران:  {simple}"), s["simple"]))

        story.append(KeepTogether(coin_block))

        if i < len(data.get("coins", [])):
            story.append(HRFlowable(width="60%", thickness=0.4, color=C_LIGHT_LINE,
                                    spaceBefore=2, spaceAfter=2))

    # ── Daily conclusion ─────────────────────────────────────────────────────
    daily = data.get("daily_conclusion", "")
    if daily:
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=1, color=C_GREEN, spaceAfter=4))
        story.append(Paragraph(r("جمع‌بندی کلی امروز"), s["section_head"]))
        story.append(Paragraph(r(daily), s["daily_conc"]))

    # ── Disclaimer footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_LINE, spaceAfter=4))
    story.append(Paragraph(
        r("⚠️  این گزارش صرفاً جهت اطلاع‌رسانی است و توصیه مالی محسوب نمی‌شود. مسئولیت تصمیمات معاملاتی با خود معامله‌گر است."),
        s["footer"]
    ))

    doc.build(story)
    print(f"PDF saved → {output_path}")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/generate_persian_pdf.py <input.json> <output.pdf>")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    build_pdf(payload, output_path)
