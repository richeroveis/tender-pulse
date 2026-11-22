#!/usr/bin/env python3
"""Generate crisp 512x512 logo for TenderPulse in warm-ivory / deep-teal procurement palette."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parents[1]
OUT_DOCS = ROOT / "docs" / "logo.png"
OUT_PUBLIC = ROOT / "frontend" / "public" / "logo.png"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")
FONT_REGULAR = str(FONT_DIR / "DejaVuSans.ttf")

WIDTH, HEIGHT = 512, 512
img = Image.new("RGBA", (WIDTH, HEIGHT), (10, 37, 40, 255))
draw = ImageDraw.Draw(img)

# Deep Teal Gradient Background
for y in range(HEIGHT):
    factor = y / HEIGHT
    r = int(10 + factor * 8)
    g = int(37 + factor * 25)
    b = int(40 + factor * 28)
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

# Outer Octagonal / Circular Civic Seal Border
center_x, center_y = WIDTH // 2, 210
outer_radius = 160

# Subtle inner seal ring
draw.ellipse(
    [(center_x - outer_radius, center_y - outer_radius),
     (center_x + outer_radius, center_y + outer_radius)],
    outline=(20, 184, 166, 180), width=4
)
draw.ellipse(
    [(center_x - outer_radius + 10, center_y - outer_radius + 10),
     (center_x + outer_radius - 10, center_y + outer_radius - 10)],
    outline=(229, 184, 105, 120), width=2
)

# Central Graphic: The Scales of Public Procurement & Digital Pulse Seal
# Central Pillar
draw.line([(center_x, center_y - 100), (center_x, center_y + 90)], fill=(244, 238, 221, 240), width=6)
# Pillar base
draw.polygon([
    (center_x - 45, center_y + 90),
    (center_x + 45, center_y + 90),
    (center_x + 35, center_y + 75),
    (center_x - 35, center_y + 75),
], fill=(229, 184, 105, 230))

# Balance Beam
beam_y = center_y - 55
draw.line([(center_x - 110, beam_y + 12), (center_x + 110, beam_y - 12)], fill=(244, 238, 221, 240), width=5)

# Left Scale (Vendor Bid Vault)
left_x, left_y = center_x - 110, beam_y + 12
draw.line([(left_x, left_y), (left_x - 30, left_y + 60)], fill=(20, 184, 166, 200), width=2)
draw.line([(left_x, left_y), (left_x + 30, left_y + 60)], fill=(20, 184, 166, 200), width=2)
draw.arc([(left_x - 35, left_y + 55), (left_x + 35, left_y + 75)], 0, 180, fill=(229, 184, 105, 255), width=4)

# Right Scale (Procurement Escrow Vault)
right_x, right_y = center_x + 110, beam_y - 12
draw.line([(right_x, right_y), (right_x - 30, right_y + 60)], fill=(20, 184, 166, 200), width=2)
draw.line([(right_x, right_y), (right_x + 30, right_y + 60)], fill=(20, 184, 166, 200), width=2)
draw.arc([(right_x - 35, right_y + 55), (right_x + 35, right_y + 75)], 0, 180, fill=(229, 184, 105, 255), width=4)

# Pulse Waveform across center (AI Consensus Telemetry)
pulse_points = [
    (center_x - 70, center_y + 15),
    (center_x - 40, center_y + 15),
    (center_x - 25, center_y - 25),
    (center_x - 10, center_y + 45),
    (center_x + 5, center_y - 35),
    (center_x + 20, center_y + 25),
    (center_x + 35, center_y + 15),
    (center_x + 70, center_y + 15),
]
for i in range(len(pulse_points) - 1):
    draw.line([pulse_points[i], pulse_points[i+1]], fill=(45, 212, 191, 240), width=4)

# Top Emblem Star / Diamond
draw.polygon([
    (center_x, center_y - 118),
    (center_x + 10, center_y - 106),
    (center_x, center_y - 94),
    (center_x - 10, center_y - 106),
], fill=(229, 184, 105, 255))

# Typography
f_title = ImageFont.truetype(FONT_BOLD, 36)
f_sub = ImageFont.truetype(FONT_REGULAR, 15)

title_text = "TENDERPULSE"
title_bbox = draw.textbbox((0, 0), title_text, font=f_title)
title_w = title_bbox[2] - title_bbox[0]
draw.text((center_x - title_w // 2, 405), title_text, font=f_title, fill=(244, 238, 221, 255))

sub_text = "AI-AUDITED PUBLIC PROCUREMENT"
sub_bbox = draw.textbbox((0, 0), sub_text, font=f_sub)
sub_w = sub_bbox[2] - sub_bbox[0]
draw.text((center_x - sub_w // 2, 452), sub_text, font=f_sub, fill=(20, 184, 166, 230))

OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)

img.save(OUT_DOCS, "PNG")
img.save(OUT_PUBLIC, "PNG")
print(f"Saved {OUT_DOCS} and {OUT_PUBLIC}")
