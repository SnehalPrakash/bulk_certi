import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration (Relational SQLite by default, can be overridden via env)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/certificates.db")

# Output and Asset directories
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "output_certificates"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = BASE_DIR / "backend" / "assets"
TEMPLATE_PATH = ASSETS_DIR / "template.png"
DEFAULT_FONT_PATH = ASSETS_DIR / "america.ttf"
