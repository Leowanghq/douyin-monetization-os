#!/usr/bin/env python3
"""
Tech Cover Generator — creates a sci-fi themed cover image featuring:
  - Top: "Claude Code" branding with glow
  - Center: User's photo (circular crop + neon ring)
  - Bottom: "AI大爆炸" title
  - Background: Dark gradient + circuit board pattern + particles
"""

import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Configuration ──────────────────────────────────────────────────
PHOTO_PATH = r"C:\Users\asus\Pictures\mmexport1768392067546.jpg"
OUTPUT_PATH = r"C:\Users\asus\Pictures\cover_ai_bigbang.png"

W, H = 800, 1200          # Cover size (2:3 ratio, good for sharing)
BG_COLOR_TOP = (5, 5, 25)
BG_COLOR_BOT = (15, 5, 40)
ACCENT_CYAN = (0, 230, 255)
ACCENT_PURPLE = (140, 60, 255)
ACCENT_BLUE = (30, 100, 255)
PHOTO_SIZE = 360          # Circular photo diameter
PHOTO_Y = 500             # Photo center Y position
GLOW_RINGS = 3            # Number of glow rings around photo


# ── Helpers ────────────────────────────────────────────────────────

def gradient_bg(draw, w, h):
    """Vertical dark gradient background."""
    for y in range(h):
        t = y / h
        r = int(BG_COLOR_TOP[0] + (BG_COLOR_BOT[0] - BG_COLOR_TOP[0]) * t)
        g = int(BG_COLOR_TOP[1] + (BG_COLOR_BOT[1] - BG_COLOR_TOP[1]) * t)
        b = int(BG_COLOR_TOP[2] + (BG_COLOR_BOT[2] - BG_COLOR_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def draw_circuit_lines(draw, w, h):
    """Draw sci-fi circuit board lines and nodes."""
    for _ in range(40):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        # Horizontal or vertical lines
        if random.random() < 0.5:
            length = random.randint(40, 200)
            x2 = x1 + length if random.random() < 0.5 else x1 - length
            y2 = y1
        else:
            length = random.randint(40, 200)
            x2 = x1
            y2 = y1 + length if random.random() < 0.5 else y1 - length

        alpha = random.randint(15, 60)
        color = random.choice([
            (0, alpha + 40, alpha + 80),
            (alpha + 30, 0, alpha + 60),
            (alpha + 20, alpha + 40, alpha + 100),
        ])
        draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

        # Nodes at endpoints and corners
        for cx, cy in [(x1, y1), (x2, y2), (x1, y2), (x2, y1)]:
            if random.random() < 0.3:
                r = random.randint(1, 3)
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT_CYAN + (80,))


def draw_hex_grid(draw, w, h):
    """Subtle hexagonal grid in the background."""
    spacing = 80
    for row in range(-2, h // spacing + 3):
        offset = (spacing // 2) if row % 2 else 0
        for col in range(-2, w // spacing + 3):
            cx = col * spacing + offset
            cy = row * int(spacing * 0.87)
            hex_size = spacing // 3
            pts = []
            for i in range(6):
                angle = math.pi / 3 * i - math.pi / 6
                px = cx + hex_size * math.cos(angle)
                py = cy + hex_size * math.sin(angle)
                pts.append((px, py))
            draw.polygon(pts, outline=(30, 30, 80), width=1)


def draw_particles(draw, w, h):
    """Floating light particles."""
    for _ in range(200):
        x, y = random.randint(0, w), random.randint(0, h)
        r = random.randint(1, 3)
        alpha = random.randint(20, 120)
        colors = [ACCENT_CYAN, ACCENT_PURPLE, ACCENT_BLUE, (180, 180, 255)]
        color = random.choice(colors) + (alpha,)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


# ── Photo Processing ───────────────────────────────────────────────

def circle_crop_with_glow(img, size, y_center, base_img, draw):
    """Place the photo as a circle with neon glow rings."""
    cx, cy = W // 2, y_center
    radius = size // 2

    # Resize photo to fit the circle
    img_resized = img.resize((size, size), Image.LANCZOS)

    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size, size], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1))

    # Create the photo circle
    photo_circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    photo_circle.paste(img_resized, (0, 0))

    # Apply mask
    rgba = photo_circle.copy()
    rgba.putalpha(mask)

    # Calculate paste position
    paste_x = cx - radius
    paste_y = cy - radius

    # Draw glow rings (behind the photo, on the base image)
    for i in range(GLOW_RINGS, 0, -1):
        glow_r = radius + 8 + i * 18
        glow_alpha = 120 - i * 30
        glow_color = ACCENT_CYAN + (glow_alpha,)
        draw.ellipse(
            [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
            outline=glow_color,
            width=2 + i,
        )

    # Draw an extra purple glow ring
    purple_glow_r = radius + 50
    draw.ellipse(
        [cx - purple_glow_r, cy - purple_glow_r, cx + purple_glow_r, cy + purple_glow_r],
        outline=ACCENT_PURPLE + (40,),
        width=4,
    )

    # Paste the circular photo onto base image
    base_img.paste(rgba, (paste_x, paste_y), rgba)

    # Draw a thin white ring exactly at the photo edge
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255),
        width=2,
    )

    return cx, cy, radius


# ── Text Rendering ─────────────────────────────────────────────────

def get_font(size, bold=False):
    """Try to load a good font, fall back to default."""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",     # 微软雅黑 Bold
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/STZHONGS.TTF",   # 华文中宋
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arialbd.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def draw_text_with_glow(draw, text, position, font, color, glow_color, glow_width=4):
    """Draw text with an outer glow effect."""
    x, y = position
    # Glow layers
    for dx in range(-glow_width, glow_width + 1, 2):
        for dy in range(-glow_width, glow_width + 1, 2):
            if dx == 0 and dy == 0:
                continue
            dist = math.sqrt(dx * dx + dy * dy)
            alpha = max(10, int(120 - dist * 30))
            g_color = glow_color + (alpha,)
            draw.text((x + dx, y + dy), text, font=font, fill=g_color)
    # Main text
    draw.text((x, y), text, font=font, fill=color)


def draw_top_branding(draw):
    """Draw Claude Code branding at the top."""
    font_brand = get_font(36, bold=True)

    # Claude Code text with cyan glow
    brand_text = "Claude Code"
    bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
    tw = bbox[2] - bbox[0]
    bx = (W - tw) // 2
    by = 60

    # Glow layers
    for g in range(6, 0, -2):
        glow_c = ACCENT_CYAN + (40 + g * 15,)
        draw.text((bx - g, by - g), brand_text, font=font_brand, fill=glow_c)
        draw.text((bx + g, by + g), brand_text, font=font_brand, fill=glow_c)
        draw.text((bx - g, by + g), brand_text, font=font_brand, fill=glow_c)
        draw.text((bx + g, by - g), brand_text, font=font_brand, fill=glow_c)

    # Main text - white
    draw.text((bx, by), brand_text, font=font_brand, fill=(255, 255, 255))

    # Decorative line under brand
    line_y = by + 55
    line_w = 200
    lx = (W - line_w) // 2
    # Gradient line from transparent -> cyan -> transparent
    for i in range(line_w):
        t = abs(i - line_w / 2) / (line_w / 2)
        alpha = int(200 * (1 - t))
        draw.line([(lx + i, line_y), (lx + i, line_y + 2)],
                  fill=ACCENT_CYAN + (alpha,), width=1)

    # Subtitle
    font_sub = get_font(16)
    sub_text = "POWERED BY ANTHROPIC"
    sbbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    sw = sbbox[2] - sbbox[0]
    sx = (W - sw) // 2
    draw.text((sx, line_y + 12), sub_text, font=font_sub, fill=ACCENT_CYAN + (150,))


def draw_bottom_title(draw):
    """Draw 'AI大爆炸' title at the bottom with explosive effects."""
    font_title = get_font(60, bold=True)

    # --- "AI" part ---
    ai_text = "AI"
    # Draw "AI" slightly above and left
    ai_x, ai_y = 180, 880
    for g in range(8, 0, -3):
        g_c = ACCENT_CYAN + (30 + g * 20,)
        draw.text((ai_x - g, ai_y - g), ai_text, font=font_title, fill=g_c)
        draw.text((ai_x + g, ai_y - g), ai_text, font=font_title, fill=g_c)
    draw.text((ai_x, ai_y), ai_text, font=font_title, fill=(255, 255, 255))

    # --- "大爆炸" part ---
    boom_text = "大爆炸"
    font_boom = get_font(64, bold=True)
    boom_x, boom_y = 320, 870
    for g in range(10, 0, -3):
        g_c = ACCENT_PURPLE + (20 + g * 20,)
        draw.text((boom_x - g, boom_y - g), boom_text, font=font_boom, fill=g_c)
        draw.text((boom_x + g, boom_y + g), boom_text, font=font_boom, fill=g_c)
    for g in range(6, 0, -2):
        g_c = ACCENT_CYAN + (30 + g * 15,)
        draw.text((boom_x + g, boom_y), boom_text, font=font_boom, fill=g_c)

    # Main text with gradient-ish effect
    draw.text((boom_x, boom_y), boom_text, font=font_boom, fill=(255, 255, 255))

    # --- Decorative lines around title ---
    line_w = 120
    for lx_start, ly in [(60, 910), (640, 910)]:
        for i in range(line_w):
            t = i / line_w
            alpha = int(150 * (1 - t) if lx_start < 400 else int(150 * t))
            draw.line([(lx_start + i, ly), (lx_start + i, ly + 1)],
                      fill=ACCENT_CYAN + (alpha,), width=1)

    # --- Particle burst effect around title ---
    for _ in range(30):
        angle = random.random() * 2 * math.pi
        dist = random.randint(50, 250)
        px = 380 + dist * math.cos(angle)
        py = 920 + dist * math.sin(angle) * 0.6
        r = random.randint(1, 4)
        color = random.choice([ACCENT_CYAN, ACCENT_PURPLE, ACCENT_BLUE, (255, 200, 100)])
        alpha = random.randint(60, 200)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color + (alpha,))


def draw_tech_border(draw, w, h):
    """Draw a subtle tech border/frame."""
    margin = 15
    # Corner brackets
    corner_len = 50
    bracket_width = 2
    for ox, oy in [(margin, margin), (w - margin, margin),
                   (margin, h - margin), (w - margin, h - margin)]:
        dx = -1 if ox > w // 2 else 1
        dy = -1 if oy > h // 2 else 1
        draw.line([(ox, oy), (ox + dx * corner_len, oy)],
                  fill=ACCENT_CYAN + (100,), width=bracket_width)
        draw.line([(ox, oy), (ox, oy + dy * corner_len)],
                  fill=ACCENT_CYAN + (100,), width=bracket_width)

    # Thin full border
    draw.rectangle([margin, margin, w - margin, h - margin],
                   outline=(40, 40, 80), width=1)


# ── Main ───────────────────────────────────────────────────────────

def generate_cover():
    print("Generating cover...")

    # Create base image
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(base)

    # 1. Background
    print("  Drawing background...")
    gradient_bg(draw, W, H)
    draw_hex_grid(draw, W, H)
    draw_circuit_lines(draw, W, H)
    draw_particles(draw, W, H)

    # 2. Tech border
    print("  Drawing tech border...")
    draw_tech_border(draw, W, H)

    # 3. Top branding
    print("  Drawing Claude Code branding...")
    draw_top_branding(draw)

    # 4. Center photo
    print("  Processing photo...")
    photo = Image.open(PHOTO_PATH).convert("RGB")

    # Enhance photo slightly for better contrast against dark bg
    enhancer = ImageEnhance.Contrast(photo)
    photo = enhancer.enhance(1.15)
    enhancer = ImageEnhance.Brightness(photo)
    photo = enhancer.enhance(1.05)

    circle_crop_with_glow(photo, PHOTO_SIZE, PHOTO_Y, base, draw)

    # 5. Bottom title
    print("  Drawing AI大爆炸 title...")
    draw_bottom_title(draw)

    # 6. Convert to RGB for final PNG output (no alpha needed)
    final = Image.new("RGB", (W, H), (0, 0, 0))
    final.paste(base, (0, 0), base)

    # Save
    final.save(OUTPUT_PATH, "PNG", quality=95)
    print(f"\n✅ Cover saved to: {OUTPUT_PATH}")
    print(f"   Size: {W}x{H} pixels")


if __name__ == "__main__":
    generate_cover()
