"""Where this server keeps its Amazon session files (owner-only folder in the home directory)."""

from pathlib import Path

DATA_DIR = Path.home() / ".amazon-orders-mcp"
COOKIE_JAR_PATH = DATA_DIR / "cookies.json"
