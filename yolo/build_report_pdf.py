from __future__ import annotations

import re
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report" / "yolo_ui_detection_report.md"
OUTPUT = ROOT / "report" / "yolo_ui_detection_report.pdf"
FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def register_fonts() -> tuple[str, str]:
    if FONT_REGULAR.is_file() and FONT_BOLD.is_file():
        pdfmetrics.registerFont(TTFont("Malgun", str(FONT_REGULAR)))
        pdfmetrics.registerFont(TTFont("Malgun-Bold", str(FONT_BOLD)))
        return "Malgun", "Malgun-Bold"
    return "Helvetica", "Helvetica-Bold"


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def strip_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


def make_styles() -> dict[str, ParagraphStyle]:
    regular, bold = register_fonts()
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleKo",
            parent=sample["Title"],
            fontName=bold,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "Heading1Ko",
            parent=sample["Heading1"],
            fontName=bold,
            fontSize=15,
            leading=22,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "Heading2Ko",
            parent=sample["Heading2"],
            fontName=bold,
            fontSize=12,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BodyKo",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=9.5,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "BulletKo",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=9.5,
            leading=15,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "CodeKo",
            parent=sample["Code"],
            fontName=regular,
            fontSize=8,
            leading=11,
            backColor=colors.HexColor("#F4F6F8"),
            borderColor=colors.HexColor("#D8DEE4"),
            borderWidth=0.4,
            borderPadding=5,
            spaceBefore=4,
            spaceAfter=7,
        ),
    }


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for line in lines:
        if re.match(r"^\|\s*-", line):
            continue
        cells = [strip_inline_markdown(cell.strip()) for cell in line.strip("|").split("|")]
        rows.append([Paragraph(escape(cell), styles["body"]) for cell in cells])

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Malgun"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCD6E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_story(markdown: str) -> list[object]:
    styles = make_styles()
    story: list[object] = []
    lines = markdown.splitlines()
    index = 0
    in_front_matter = False

    while index < len(lines):
        line = lines[index].rstrip()

        if index == 0 and line == "---":
            in_front_matter = True
            index += 1
            continue
        if in_front_matter:
            if line == "---":
                in_front_matter = False
            index += 1
            continue

        if not line:
            story.append(Spacer(1, 3))
            index += 1
            continue

        if line.startswith("```"):
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            code_text = "\n".join(code_lines)
            wrapped = []
            for code_line in code_text.splitlines():
                wrapped.extend(textwrap.wrap(code_line, width=92) or [""])
            story.append(Preformatted("\n".join(wrapped), styles["code"]))
            continue

        if line.startswith("|") and "|" in line[1:]:
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(parse_table(table_lines, styles))
            story.append(Spacer(1, 6))
            continue

        if line == "---":
            story.append(Spacer(1, 8))
            index += 1
            continue

        if line.startswith("# "):
            text = strip_inline_markdown(line[2:].strip())
            if story:
                story.append(PageBreak())
            story.append(Paragraph(escape(text), styles["title"]))
            index += 1
            continue

        if line.startswith("## "):
            story.append(Paragraph(escape(strip_inline_markdown(line[3:].strip())), styles["h1"]))
            index += 1
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(strip_inline_markdown(line[4:].strip())), styles["h2"]))
            index += 1
            continue

        if line.startswith("- "):
            story.append(Paragraph("• " + escape(strip_inline_markdown(line[2:].strip())), styles["bullet"]))
            index += 1
            continue

        story.append(Paragraph(escape(strip_inline_markdown(line)), styles["body"]))
        index += 1

    return story


def add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Malgun", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawRightString(200 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="YOLO 기반 UI 요소 탐지 기능 구현 보고서",
        author="Codex",
    )
    doc.build(build_story(markdown), onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(OUTPUT)


if __name__ == "__main__":
    main()
