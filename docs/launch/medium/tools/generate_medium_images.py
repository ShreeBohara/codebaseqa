#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "diagrams"


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(64, bold=True)
FONT_H2 = load_font(42, bold=True)
FONT_BODY = load_font(30)
FONT_SMALL = load_font(24)
FONT_LABEL = load_font(20, bold=True)
FONT_FLOW = load_font(15, bold=True)


def rounded_box(draw: ImageDraw.ImageDraw, box, fill, outline, radius=24, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw: ImageDraw.ImageDraw, start, end, color="#d1d5db", width=6):
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex > sx else -1
        tip = (ex, ey)
        p1 = (ex - 20 * direction, ey - 10)
        p2 = (ex - 20 * direction, ey + 10)
    else:
        direction = 1 if ey > sy else -1
        tip = (ex, ey)
        p1 = (ex - 10, ey - 20 * direction)
        p2 = (ex + 10, ey - 20 * direction)
    draw.polygon([tip, p1, p2], fill=color)


def poly_arrow(draw: ImageDraw.ImageDraw, points, color="#475569", width=4):
    if len(points) < 2:
        return
    for i in range(len(points) - 2):
        draw.line([points[i], points[i + 1]], fill=color, width=width)
    arrow(draw, points[-2], points[-1], color=color, width=width)


def draw_multiline_center(draw: ImageDraw.ImageDraw, text: str, center, font, fill):
    lines = text.split("\n")
    line_heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    total_h = sum(line_heights) + (len(lines) - 1) * 6
    x, y = center
    cur_y = y - total_h // 2
    for ln, h in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]
        draw.text((x - w // 2, cur_y), ln, font=font, fill=fill)
        cur_y += h + 6


def draw_card(
    draw: ImageDraw.ImageDraw,
    box,
    text: str,
    fill: str,
    outline: str,
    text_fill: str = "#0f172a",
    radius: int = 20,
):
    x1, y1, x2, y2 = box
    # Subtle drop shadow for clean separation on light background.
    shadow = (x1 + 5, y1 + 6, x2 + 5, y2 + 6)
    draw.rounded_rectangle(shadow, radius=radius, fill="#dbe3ee")
    rounded_box(draw, box, fill=fill, outline=outline, radius=radius, width=3)
    draw_multiline_center(draw, text, ((x1 + x2) // 2, (y1 + y2) // 2), FONT_LABEL, text_fill)


def make_architecture_png(path: Path):
    img = Image.new("RGB", (1600, 900), "#f8fafc")
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((60, 34), "CodebaseQA Architecture", font=FONT_H2, fill="#0f172a")
    draw.text((60, 86), "Launch container view: clear request flow + data services", font=FONT_SMALL, fill="#475569")
    draw.line((60, 126, 1540, 126), fill="#dbe3ee", width=3)

    # Section labels
    draw.text((120, 255), "CLIENT", font=FONT_FLOW, fill="#64748b")
    draw.text((500, 255), "APPLICATION", font=FONT_FLOW, fill="#64748b")
    draw.text((1270, 145), "DATA + AI SERVICES", font=FONT_FLOW, fill="#64748b")

    # Cards
    user_box = (90, 320, 330, 470)
    fe_box = (400, 300, 740, 500)
    api_box = (810, 300, 1150, 500)
    repo_box = (810, 590, 1150, 760)
    sqlite_box = (1240, 180, 1530, 300)
    chroma_box = (1240, 360, 1530, 480)
    llm_box = (1240, 540, 1530, 660)

    draw_card(draw, user_box, "Developer\n(Browser)", fill="#ffffff", outline="#cbd5e1")
    draw_card(draw, fe_box, "Next.js Web App\n(Vercel)", fill="#e0f2fe", outline="#38bdf8")
    draw_card(draw, api_box, "FastAPI Backend\n(Render)", fill="#dcfce7", outline="#22c55e")
    draw_card(draw, repo_box, "Imported Repository", fill="#ede9fe", outline="#8b5cf6")
    draw_card(draw, sqlite_box, "SQLite\nMetadata", fill="#ffffff", outline="#94a3b8")
    draw_card(draw, chroma_box, "ChromaDB\nVectors", fill="#ffffff", outline="#94a3b8")
    draw_card(draw, llm_box, "LLM Provider\n(OpenAI / Anthropic / Ollama)", fill="#fff7ed", outline="#fb923c")

    # Primary request flow
    arrow(draw, (330, 395), (400, 395), color="#334155", width=5)
    draw.text((345, 365), "HTTPS", font=FONT_FLOW, fill="#475569")
    arrow(draw, (740, 395), (810, 395), color="#334155", width=5)
    draw.text((752, 365), "REST", font=FONT_FLOW, fill="#475569")

    # Backend to repo
    arrow(draw, (980, 500), (980, 590), color="#334155", width=5)
    draw.text((1000, 540), "index + parse", font=FONT_FLOW, fill="#475569")

    # Backend to services via clean elbows
    trunk_x = 1205
    poly_arrow(draw, [(1150, 395), (trunk_x, 395), (trunk_x, 240), (1240, 240)], color="#334155", width=4)
    draw.text((1088, 214), "metadata", font=FONT_FLOW, fill="#475569")

    poly_arrow(draw, [(1150, 395), (trunk_x, 395), (trunk_x, 420), (1240, 420)], color="#334155", width=4)
    draw.text((1088, 430), "vector retrieval", font=FONT_FLOW, fill="#475569")

    poly_arrow(draw, [(1150, 395), (trunk_x, 395), (trunk_x, 600), (1240, 600)], color="#334155", width=4)
    draw.text((1088, 614), "LLM generation", font=FONT_FLOW, fill="#475569")

    draw.text(
        (60, 836),
        "Deterministic retrieval + source citations + guided learning workflows",
        font=FONT_SMALL,
        fill="#475569",
    )
    img.save(path, "PNG")


def make_deployment_vs_local_png(path: Path):
    img = Image.new("RGB", (1600, 900), "#f8fafc")
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((60, 34), "Deployment vs Local Self-Host", font=FONT_H2, fill="#0f172a")
    draw.text((60, 86), "Practical trade-offs for launch traction vs full infrastructure control", font=FONT_SMALL, fill="#475569")
    draw.line((60, 126, 1540, 126), fill="#dbe3ee", width=3)

    # Main comparison table container
    table_x1, table_y1, table_x2, table_y2 = 80, 170, 1520, 760
    rounded_box(draw, (table_x1, table_y1, table_x2, table_y2), fill="#ffffff", outline="#cbd5e1", radius=22, width=3)

    # Column layout: label | hosted | local
    label_col = 430
    hosted_col = 930
    header_h = 110
    # Row height is calculated dynamically to prevent overlap.
    row_h = 0

    # Header background
    rounded_box(draw, (table_x1 + 2, table_y1 + 2, table_x2 - 2, table_y1 + header_h), fill="#f1f5f9", outline="#f1f5f9", radius=20, width=1)

    # Column separators
    draw.line((label_col, table_y1 + 10, label_col, table_y2 - 10), fill="#e2e8f0", width=3)
    draw.line((hosted_col, table_y1 + 10, hosted_col, table_y2 - 10), fill="#e2e8f0", width=3)

    # Header labels
    draw.text((140, table_y1 + 38), "Dimension", font=FONT_LABEL, fill="#475569")
    draw.text((530, table_y1 + 34), "Hosted (Vercel + Render)", font=FONT_LABEL, fill="#0f766e")
    draw.text((1040, table_y1 + 34), "Local Self-Host", font=FONT_LABEL, fill="#1d4ed8")

    rows = [
        ("Setup Time", "Very low", "Higher upfront"),
        ("Best For", "Try-now user experience", "Privacy and full control"),
        ("Cost Control", "Moderate", "High"),
        ("Latency Tuning", "Moderate", "High"),
        ("Customization", "Moderate", "Very high"),
        ("Operational Overhead", "Lower", "Higher"),
        ("Launch Fit", "Best for public traction", "Best for advanced teams"),
    ]

    # Row backgrounds + text
    start_y = table_y1 + header_h
    row_h = (table_y2 - start_y) // len(rows)
    for i, (dim, hosted, local) in enumerate(rows):
        y1 = start_y + i * row_h
        y2 = y1 + row_h

        if i % 2 == 0:
            draw.rectangle((table_x1 + 2, y1, table_x2 - 2, y2), fill="#fafcff")

        draw.line((table_x1 + 8, y2, table_x2 - 8, y2), fill="#eef2f7", width=2)

        text_y = y1 + max(18, (row_h - 30) // 2)
        draw.text((120, text_y), dim, font=FONT_SMALL, fill="#334155")
        draw.text((500, text_y), hosted, font=FONT_SMALL, fill="#0f766e")
        draw.text((1000, text_y), local, font=FONT_SMALL, fill="#1e40af")

    # Bottom recommendation pill
    pill = (180, 804, 1420, 868)
    rounded_box(draw, pill, fill="#ecfeff", outline="#99f6e4", radius=28, width=2)
    draw.text((220, 832), "Recommendation: use hosted for launch growth, use local for privacy and deep infra customization.", font=FONT_SMALL, fill="#0f766e")
    img.save(path, "PNG")


def make_cta_card_png(path: Path):
    img = Image.new("RGB", (1600, 900), "#042f2e")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, 1600, 900), fill="#0f766e")
    rounded_box(draw, (120, 120, 1480, 780), fill="#052e2b", outline="#99f6e4", radius=34, width=5)

    draw.text((220, 220), "Try CodebaseQA", font=FONT_TITLE, fill="#ecfeff")
    draw.text((220, 330), "Understand unfamiliar repositories faster with grounded AI guidance.", font=FONT_BODY, fill="#d1fae5")

    draw.text((220, 430), "Live app: codebaseqa-web.vercel.app", font=FONT_BODY, fill="#a7f3d0")
    draw.text((220, 500), "API docs: codebaseqa-api.onrender.com/docs", font=FONT_BODY, fill="#a7f3d0")
    draw.text((220, 570), "GitHub: github.com/ShreeBohara/codebaseqa", font=FONT_BODY, fill="#a7f3d0")
    draw.text((220, 640), "Issues: github.com/ShreeBohara/codebaseqa/issues", font=FONT_BODY, fill="#a7f3d0")

    draw.text((220, 730), "Launch feedback welcome: retrieval quality, graph clarity, and learning flow.", font=FONT_SMALL, fill="#ccfbf1")
    img.save(path, "PNG")


def make_hero_cover_png(path: Path):
    img = Image.new("RGB", (1600, 900), "#111827")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, 1600, 900), fill="#0f172a")
    rounded_box(draw, (90, 90, 1510, 810), fill="#111827", outline="#14b8a6", radius=40, width=6)

    draw.text((160, 180), "CodebaseQA", font=FONT_TITLE, fill="#ccfbf1")
    draw.text((160, 300), "Understand any codebase in minutes,", font=FONT_H2, fill="#e2e8f0")
    draw.text((160, 360), "not days.", font=FONT_H2, fill="#e2e8f0")

    bullets = [
        "Citation-backed chat over real code context",
        "Persona learning paths + challenges",
        "Dependency graph exploration for architecture clarity",
        "Web + CLI workflows for daily developer use",
    ]
    y = 470
    for b in bullets:
        draw.text((180, y), f"- {b}", font=FONT_BODY, fill="#99f6e4")
        y += 75

    draw.text((160, 770), "Launch deep dive: architecture, tradeoffs, and deployment strategy", font=FONT_SMALL, fill="#94a3b8")
    img.save(path, "PNG")


def main():
    DIAGRAMS.mkdir(parents=True, exist_ok=True)
    make_architecture_png(DIAGRAMS / "architecture-container.png")
    make_deployment_vs_local_png(DIAGRAMS / "deployment-vs-local.png")
    make_cta_card_png(DIAGRAMS / "cta-card.png")
    make_hero_cover_png(DIAGRAMS / "hero-cover.png")
    print("Generated PNG assets in", DIAGRAMS)


if __name__ == "__main__":
    main()
