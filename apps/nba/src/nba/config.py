from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    telegram_enabled: bool = False
    odds_enabled: bool = False

    @classmethod
    def load(cls):
        # Solo variables NBA. No buscar .env ni reutilizar credenciales de qf.
        root = Path(__file__).resolve().parents[2] / ".local"
        return cls(
            Path(os.environ.get("NBA_DATA_DIR", str(root))).resolve(),
            os.environ.get("NBA_TELEGRAM_ENABLED", "false").lower() == "true",
            os.environ.get("NBA_ODDS_ENABLED", "false").lower() == "true",
        )
