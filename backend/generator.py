import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from backend.config import TEMPLATE_PATH, DEFAULT_FONT_PATH, STORAGE_DIR

def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filenames."""
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', name).strip('_')
    return clean or "certificate"

def load_fonts():
    """Load fonts for certificate fields, falling back to default if necessary."""
    try:
        if DEFAULT_FONT_PATH.exists():
            name_font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 68)
        else:
            name_font = ImageFont.load_default()
    except Exception:
        name_font = ImageFont.load_default()

    # Standard clean fonts for labels
    try:
        title_font = ImageFont.truetype("Arial", 54)
        subtitle_font = ImageFont.truetype("Arial", 26)
        event_font = ImageFont.truetype("Arial", 36)
        meta_font = ImageFont.truetype("Arial", 22)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        event_font = ImageFont.load_default()
        meta_font = ImageFont.load_default()

    return {
        "title": title_font,
        "subtitle": subtitle_font,
        "name": name_font,
        "event": event_font,
        "meta": meta_font
    }

def generate_certificate_image(
    job_id: str,
    cert_id: str,
    recipient_name: str,
    event_name: str,
    issue_date: str = None
) -> str:
    """
    Renders a certificate for a single recipient using the predefined template.
    Saves to STORAGE_DIR / job_id / filename.png and returns the file path.
    """
    # 1. Ensure template exists, or generate fallback
    if TEMPLATE_PATH.exists():
        img = Image.open(TEMPLATE_PATH).convert("RGB")
    else:
        # Fallback 1920x1080 canvas
        img = Image.new("RGB", (1920, 1080), "#fdfcf9")

    w, h = img.size
    draw = ImageDraw.Draw(img)
    fonts = load_fonts()

    # 2. Render Text Elements (Centered layout)
    center_x = w // 2

    # Title
    draw.text((center_x, 220), "CERTIFICATE OF ACHIEVEMENT", fill="#1e293b", font=fonts["title"], anchor="mm")

    # Subtitle
    draw.text((center_x, 320), "This is proudly presented to", fill="#64748b", font=fonts["subtitle"], anchor="mm")

    # Recipient Name
    draw.text((center_x, 460), recipient_name, fill="#0f172a", font=fonts["name"], anchor="mm")

    # Name underline accent
    draw.line([(center_x - 320, 520), (center_x + 320, 520)], fill="#c5a059", width=2)

    # Event context
    draw.text((center_x, 600), "For successfully completing and mastering the requirements of", fill="#475569", font=fonts["subtitle"], anchor="mm")
    draw.text((center_x, 670), event_name, fill="#1e293b", font=fonts["event"], anchor="mm")

    # Date
    date_str = f"Issued: {issue_date}" if issue_date else "Issued upon program completion"
    draw.text((center_x, 770), date_str, fill="#64748b", font=fonts["meta"], anchor="mm")

    # Signature blocks
    draw.line([(center_x - 450, 920), (center_x - 150, 920)], fill="#94a3b8", width=1)
    draw.text((center_x - 300, 940), "Authorized Signature", fill="#64748b", font=fonts["meta"], anchor="mm")

    draw.line([(center_x + 150, 920), (center_x + 450, 920)], fill="#94a3b8", width=1)
    draw.text((center_x + 300, 940), "Program Director", fill="#64748b", font=fonts["meta"], anchor="mm")

    # 3. Save to job directory
    job_dir = STORAGE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(recipient_name)
    file_path = job_dir / f"{safe_name}_{cert_id[:8]}.png"

    img.save(file_path, format="PNG")
    return str(file_path)
