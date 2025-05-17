import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from photo_rename.shared import NamingMethod

APP_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "Photo Rename"
CONFIG_PATH = Path(os.getenv("APPDATA"), APP_NAME, "config.json")


@dataclass
class Config:
    last_opened_folder: Path = Path.home()
    date_format: str = "%Y-%m-%d_%H-%M-%S"
    naming_method: NamingMethod = NamingMethod.DATE_ONLY
    first_use: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.last_opened_folder, Path):
            self.last_opened_folder = Path(self.last_opened_folder)
        if not isinstance(self.naming_method, NamingMethod):
            self.naming_method = NamingMethod(self.naming_method)

        if not self.last_opened_folder.exists():
            self.last_opened_folder = Path.home()
        if not self.last_opened_folder.is_dir():
            self.last_opened_folder = self.last_opened_folder.parent


def load_config(fp: str | Path = CONFIG_PATH) -> Config:
    fp = Path(fp)
    if not fp.exists():
        return Config()

    with fp.open("r") as f:
        data = json.load(f)
    return Config(**data)


def save_config(config: Config, fp: str | Path = CONFIG_PATH) -> None:
    fp = Path(fp)
    fp.parent.mkdir(parents=True, exist_ok=True)
    str_config = asdict(config)
    for key, value in str_config.items():
        if isinstance(value, Path):
            str_config[key] = value.as_posix()
        elif isinstance(value, Enum):
            str_config[key] = value.value

    with fp.open("w") as f:
        json.dump(str_config, f, indent=4, ensure_ascii=False)


def try_save_config(config: Config, fp: str | Path = CONFIG_PATH) -> None:
    try:
        save_config(config, fp)
    except Exception:
        pass
