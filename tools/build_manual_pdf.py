"""Build the French user manual PDF from its maintained Markdown source.

Requires reportlab. Run from the repository root with the bundled PDF runtime.
"""

from pathlib import Path
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer,
    Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/Manuel_AstroClocks_3.4.4_FR.pdf"
NAVY = colors.HexColor("#152B3C")
BLUE = colors.HexColor("#176482")
GOLD = colors.HexColor("#C19030")
INK = colors.HexColor("#243745")
MUTED = colors.HexColor("#607482")
PALE = colors.HexColor("#EFF4F7")
WIDTH, HEIGHT = A4


def inline(text):
    text = text.replace("—", "-").replace("–", "-").replace("−", "-")
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{m[2]}" color="#176482">{m[1]}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r'<font face="Manual" color="#176482">\1</font>', text)


class ManualDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if getattr(flowable, "chapter_key", None):
            key = flowable.chapter_key
            title = flowable.getPlainText()
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0)
            self.notify("TOCEntry", (0, title, self.page, key))


def decorate(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, HEIGHT - 30, WIDTH, 30, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(48, HEIGHT - 255, 5, 112, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#DDE6EC"))
        canvas.line(48, 108, WIDTH - 48, 108)
        canvas.setFillColor(MUTED)
        canvas.setFont("Manual", 9)
        canvas.drawString(48, 90, "Documentation utilisateur - version française")
    else:
        canvas.setFont("ManualBold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(48, HEIGHT - 32, "ASTROCLOCKS")
        canvas.setFont("Manual", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(WIDTH - 48, HEIGHT - 32, "Manuel d’utilisation | 3.4.4")
        canvas.setStrokeColor(colors.HexColor("#DDE6EC"))
        canvas.line(48, HEIGHT - 42, WIDTH - 48, HEIGHT - 42)
        canvas.line(48, 40, WIDTH - 48, 40)
        canvas.setFont("Manual", 8)
        canvas.drawString(48, 26, "AstroClocks - Windows")
        canvas.drawRightString(WIDTH - 48, 26, str(doc.page))
    canvas.restoreState()


def build():
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Manual", str(font_dir / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("ManualBold", str(font_dir / "segoeuib.ttf")))
    pdfmetrics.registerFontFamily("Manual", normal="Manual", bold="ManualBold",
                                  italic="Manual", boldItalic="ManualBold")
    body = ParagraphStyle("Body", fontName="Manual", fontSize=10.2, leading=14.5,
                          textColor=INK, spaceAfter=8, alignment=TA_LEFT)
    chapter = ParagraphStyle("Chapter", parent=body, fontName="ManualBold",
                             fontSize=21, leading=25, textColor=NAVY,
                             spaceAfter=19, keepWithNext=True)
    subhead = ParagraphStyle("Subhead", parent=body, fontName="ManualBold",
                             fontSize=12, leading=16, textColor=BLUE,
                             spaceBefore=12, spaceAfter=6, keepWithNext=True)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=15,
                            firstLineIndent=0, bulletIndent=0, spaceAfter=5)
    cell = ParagraphStyle("Cell", parent=body, fontSize=9.2, leading=12.5,
                          spaceAfter=0)
    header_cell = ParagraphStyle("HeaderCell", parent=cell, fontName="ManualBold",
                                 textColor=colors.white)
    compact_body = ParagraphStyle("CompactBody", parent=body, fontSize=10,
                                  leading=13.6, spaceAfter=6)
    compact_subhead = ParagraphStyle("CompactSubhead", parent=subhead,
                                     spaceBefore=8, spaceAfter=5, leading=15)
    compact_bullet = ParagraphStyle("CompactBullet", parent=bullet, fontSize=10,
                                    leading=13.6, spaceAfter=4)
    code = ParagraphStyle("Code", parent=body, fontSize=9.2, leading=13,
                          backColor=PALE, borderPadding=10, spaceBefore=4,
                          spaceAfter=12)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = ManualDoc(str(OUTPUT), pagesize=A4, leftMargin=48, rightMargin=48,
                    topMargin=62, bottomMargin=58, title="AstroClocks 3.4.4 - Manuel d’utilisation",
                    author="AstroClocks", subject="Guide utilisateur français avec ASCOM en dernière partie")
    frame = Frame(48, 58, WIDTH - 96, HEIGHT - 120, leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Manual", frames=[frame], onPage=decorate))
    story = [Spacer(1, 105), Paragraph("ASTROCLOCKS", ParagraphStyle(
        "CoverName", parent=body, fontName="ManualBold", fontSize=34, leading=40,
        textColor=NAVY, leftIndent=24)),
        Spacer(1, 14), Paragraph("Manuel d’utilisation", ParagraphStyle(
            "CoverTitle", parent=body, fontSize=23, leading=30, leftIndent=24)),
        Spacer(1, 20), Paragraph("Version 3.4.4 • Windows • Français", ParagraphStyle(
            "CoverVersion", parent=body, fontSize=12, leading=18, leftIndent=24,
            textColor=BLUE)),
        Spacer(1, 70), Paragraph("Préparer une observation<br/>Lire les coordonnées de pointage<br/>"
            "Explorer les catalogues<br/>Régler la réfraction et les données météo", ParagraphStyle(
                "CoverTopics", parent=body, fontSize=14, leading=25)),
        Spacer(1, 30), Paragraph("Les fonctions optionnelles de connexion et de commande ASCOM "
            "sont regroupées en dernière partie.", body), Spacer(1, 18),
        Paragraph("Édition du 14 octobre 2026", body), PageBreak(),
        Paragraph("Sommaire", chapter), Paragraph(
            "Cliquez sur un titre pour accéder à la section. Les signets du lecteur PDF "
            "permettent également de naviguer entre les chapitres.", body), Spacer(1, 15)]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC", parent=body, fontSize=11, leading=17,
                                     spaceBefore=10, spaceAfter=5)]
    story.extend([toc])
    lines = (ROOT / "MANUEL_UTILISATION.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("## 1."))
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("## "):
            if line.startswith("## 12."):
                body, subhead, bullet = compact_body, compact_subhead, compact_bullet
            story.append(PageBreak())
            p = Paragraph(inline(line[3:]), chapter)
            p.chapter_key = "chapter-" + line[3:].split(".")[0]
            story.append(p)
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), subhead))
        elif line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(html.escape(lines[i]))
                i += 1
            story.append(Paragraph("<br/>".join(block), code))
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                pieces = [value.strip() for value in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", value) for value in pieces):
                    style = header_cell if not rows else cell
                    rows.append([Paragraph(inline(value), style) for value in pieces])
                i += 1
            table = Table(rows, colWidths=[(WIDTH - 96) * .33, (WIDTH - 96) * .67],
                          repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALE, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, -1), (-1, -1), .4, colors.HexColor("#DDE6EC")),
            ]))
            story.extend([table, Spacer(1, 12)])
            continue
        elif line.startswith("- ") or re.match(r"\d+\. ", line):
            match = re.match(r"(\d+)\. (.*)", line)
            label, text = (match[1] + ".", match[2]) if match else ("•", line[2:])
            story.append(Paragraph(inline(text), bullet, bulletText=label))
        else:
            text = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
                    r"^(#|\||```|- |\d+\. )", lines[i + 1]):
                i += 1
                text.append(lines[i])
            story.append(Paragraph(inline(" ".join(text)), body))
        i += 1
    doc.multiBuild(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
