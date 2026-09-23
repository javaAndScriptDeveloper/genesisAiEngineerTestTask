"""One-page A4 PDF report built with reportlab and matplotlib's bundled DejaVu font."""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from .run import load_run

FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
LABELS = {
    "en": {"subtitle": "Wikipedia pageviews (agent=user), views per million project views · {start}..{end} · generated {gen}",
           "table": ["topic", "lang", "title", "pm latest", "pm year ago", "YoY %", "growth/yr % (clipped)", "spikes %", "coverage %", "confidence"],
           "ranking": "Ranking", "notes": "Recommendation", "assumptions": "Assumptions", "limitations": "Limitations",
           "source": "Source: Wikimedia Pageviews API (wikimedia.org/api/rest_v1), Wikidata sitelinks. Built with the wikipedia-interest skill."},
    "uk": {"subtitle": "Перегляди Wikipedia (agent=user), переглядів на мільйон переглядів розділу · {start}..{end} · створено {gen}",
           "table": ["тема", "мова", "стаття", "на млн зараз", "на млн рік тому", "YoY %", "ріст/рік % (без піків)", "піки %", "покриття %", "довіра"],
           "ranking": "Рейтинг", "notes": "Рекомендація", "assumptions": "Припущення", "limitations": "Обмеження",
           "source": "Джерело: Wikimedia Pageviews API (wikimedia.org/api/rest_v1), Wikidata. Побудовано навичкою wikipedia-interest."},
}
CONF_COLORS = {"high": colors.HexColor("#2e7d32"), "medium": colors.HexColor("#ef6c00"), "low": colors.HexColor("#c62828")}


def _register_fonts() -> None:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    ttf_dir = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    pdfmetrics.registerFont(TTFont(FONT, os.path.join(ttf_dir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(ttf_dir, "DejaVuSans-Bold.ttf")))


def render_pdf(run_dir: Path, out: Path, title: str | None, notes: str, lang: str = "en") -> Path:
    _register_fonts()
    run = load_run(Path(run_dir))
    L = LABELS.get(lang, LABELS["en"])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = A4
    margin = 14 * mm
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle(title or ", ".join(run["topics"]))
    y = H - margin

    # Title + subtitle
    c.setFont(FONT_BOLD, 15)
    c.drawString(margin, y, _fit(title or f"{', '.join(run['topics'])} — {', '.join(run['langs'])}", FONT_BOLD, 15, W - 2 * margin))
    y -= 7 * mm
    c.setFont(FONT, 8)
    c.drawString(margin, y, L["subtitle"].format(start=run["window"]["start"], end=run["window"]["end"], gen=run["generated_at"]))
    y -= 6 * mm

    # Key numbers table
    rows = [L["table"]]
    for k, m in run["metrics"].items():
        topic, lg = k.split("|", 1)
        title_ = run["resolutions"][topic]["per_lang"][lg]["title"] or ""
        rows.append([topic[:28], lg, title_[:26], _f(m["pm_latest"]), _f(m["pm_year_ago"]), _f(m["yoy_pct"]),
                     _f(m["growth_clipped_pct_per_year"]), _f(m["spike_share_pct"]), _f(m["coverage_pct"]), m["confidence"]])
    tbl = Table(rows, colWidths=[30 * mm, 9 * mm, 34 * mm, 15 * mm, 17 * mm, 13 * mm, 22 * mm, 13 * mm, 16 * mm, 14 * mm])
    style = [("FONT", (0, 0), (-1, -1), FONT, 6.5), ("FONT", (0, 0), (-1, 0), FONT_BOLD, 6.5),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, row in enumerate(rows[1:], start=1):
        style.append(("TEXTCOLOR", (-1, i), (-1, i), CONF_COLORS.get(row[-1], colors.black)))
    tbl.setStyle(TableStyle(style))
    _, th = tbl.wrapOn(c, W - 2 * margin, H)
    tbl.drawOn(c, margin, y - th)
    y -= th + 5 * mm

    # Chart
    chart = Path(run_dir) / "chart.png"
    chart_h = 78 * mm
    if chart.exists():
        c.drawImage(str(chart), margin, y - chart_h, width=W - 2 * margin, height=chart_h, preserveAspectRatio=True, anchor="n")
    else:
        c.setFont(FONT, 8)
        c.drawString(margin, y - 5 * mm, "(chart.png not found)")
    y -= chart_h + 4 * mm

    # Ranking line
    c.setFont(FONT_BOLD, 9)
    c.drawString(margin, y, L["ranking"] + ":")
    c.setFont(FONT, 8)
    ranking = "; ".join(f"{i + 1}. {r['key']} ({r['score']})" for i, r in enumerate(run["ranking"])) or "—"
    c.drawString(margin + 22 * mm, y, _fit(ranking, FONT, 8, W - 2 * margin - 22 * mm))
    y -= 6 * mm

    # Footer block (fixed height) then notes fill what remains
    footer_top = margin + 30 * mm
    _draw_footer(c, run, L, margin, W, footer_top)
    avail_h = y - footer_top - 3 * mm
    _draw_notes(c, notes, L["notes"], margin, y, W - 2 * margin, avail_h)

    c.showPage()
    c.save()
    return out


def _draw_notes(c, notes: str, heading: str, x: float, top: float, width: float, avail_h: float) -> None:
    c.setFont(FONT_BOLD, 9)
    c.drawString(x, top, heading)
    top -= 4 * mm
    avail_h -= 4 * mm
    if not notes.strip() or avail_h < 10 * mm:
        return  # nothing to draw, or the table was so tall that no room is left above the footer
    html = _notes_to_html(notes)
    for size in (9, 8.5, 8, 7.5, 7):
        para = Paragraph(html, ParagraphStyle("n", fontName=FONT, fontSize=size, leading=size * 1.25))
        _, h = para.wrap(width, avail_h)
        if h <= avail_h:
            para.drawOn(c, x, top - h)
            return
    # Truncate at 7 pt until it fits
    words = html.split(" ")
    while words:
        words = words[: max(1, int(len(words) * 0.85))]
        para = Paragraph(" ".join(words) + " …", ParagraphStyle("n", fontName=FONT, fontSize=7, leading=8.75))
        _, h = para.wrap(width, avail_h)
        if h <= avail_h:
            para.drawOn(c, x, top - h)
            return
        if len(words) == 1:
            return


def _draw_footer(c, run: dict, L: dict, margin: float, W: float, top: float) -> None:
    width = W - 2 * margin
    text = (f"<b>{L['assumptions']}:</b> " + " ".join(run["assumptions"][:4])
            + f"<br/><b>{L['limitations']}:</b> " + " ".join(run["limitations"][:6])
            + f"<br/>{L['source']}")
    for size in (7, 6.5, 6, 5.5):
        para = Paragraph(text, ParagraphStyle("f", fontName=FONT, fontSize=size, leading=size * 1.2,
                                              textColor=colors.HexColor("#444444")))
        _, h = para.wrap(width, top - margin)
        if h <= top - margin:
            para.drawOn(c, margin, top - h)
            return
    para = Paragraph(text[:1500] + " …", ParagraphStyle("f", fontName=FONT, fontSize=5.5, leading=6.6))
    _, h = para.wrap(width, top - margin)
    para.drawOn(c, margin, max(margin, top - h))


def _notes_to_html(notes: str) -> str:
    out = []
    for line in notes.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith(("- ", "* ")):
            out.append("&bull; " + line[2:])
        else:
            out.append(line)
    return "<br/>".join(out)


def _fit(text: str, font: str, size: float, width: float) -> str:
    while text and pdfmetrics.stringWidth(text, font, size) > width:
        text = text[:-2] + "…"
    return text


def _f(x) -> str:
    return "–" if x is None else f"{x:g}"
