"""DealForge Agents — Package init."""

from pathlib import Path

from dotenv import load_dotenv

_REPOSITORY_DIR = Path(__file__).resolve().parent.parent

load_dotenv(_REPOSITORY_DIR / "backend" / ".env")
load_dotenv(_REPOSITORY_DIR / ".env")
