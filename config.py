import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = os.getenv("KEEPER_DB", str(BASE_DIR / "keeper.db"))
SECRET_KEY = os.getenv("KEEPER_SECRET", "keeper")