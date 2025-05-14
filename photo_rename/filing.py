import os.path
import posixpath
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

from PIL import ExifTags, Image
from pillow_heif import register_heif_opener

register_heif_opener()


class DateType(Enum):
    TAKEN = auto()
    CREATED = auto()
    MODIFIED = auto()
    MANUAL = auto()
    NO_DATA = auto()


@dataclass
class DateProperty:
    dt: datetime | None
    dtype: DateType


def parse_datestr(date_str: str) -> datetime:
    date_chars = ["Y", "y", "m", "d", "H", "M", "S"]
    return "".join([("%" + s if s in date_chars else s) for s in str(date_str)])


def format_datestr(date_str: str) -> str:
    return "".join([s.lstrip("%") for s in str(date_str)])


def extract_base_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def extract_invalid_chars(path: str) -> list[str]:
    invalid_chars = r'<>:"/\|?*'
    return [c for c in path if c in invalid_chars]


def replace_path_filename(path: str, f_name: str) -> str:
    dir_name, base = os.path.split(path)
    name, ext = os.path.splitext(base)

    return posixpath.join(dir_name, f"{f_name}{ext}".format(name=name))


def _get_dateproperty_from_exif(path: str) -> DateProperty:
    """Get DateTimeOriginal or DateTime from image EXIF metadata"""
    dt = DateProperty(None, DateType.NO_DATA)
    try:
        with Image.open(path) as img:
            exif_data = img.getexif()
            if not exif_data:
                return DateProperty(None, DateType.NO_DATA)

            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag == "DateTimeOriginal":
                    return DateProperty(
                        datetime.strptime(value, "%Y:%m:%d %H:%M:%S"),
                        DateType.TAKEN,
                    )
                elif tag == "DateTime":
                    dt = DateProperty(
                        datetime.strptime(value, "%Y:%m:%d %H:%M:%S"),
                        DateType.TAKEN,
                    )
        return dt
    except Exception:
        return dt


def _get_dateproperty_from_system(path: str) -> DateProperty:
    """Get file creation time or last modified time using filesystem metadata"""
    path_ = Path(path)
    try:
        ctime = datetime.fromtimestamp(path_.stat().st_ctime)
        mtime = datetime.fromtimestamp(path_.stat().st_mtime)

        if ctime <= mtime:
            return DateProperty(ctime, DateType.CREATED)
        else:
            return DateProperty(mtime, DateType.MODIFIED)

    except Exception as e:
        return DateProperty(None, DateType.NO_DATA)


def resolve_best_datetime(path: Path) -> DateProperty:
    """Select the best available datetime in priority: EXIF > creation > modified"""
    dpropety = _get_dateproperty_from_exif(path)
    if dpropety.dtype != DateType.NO_DATA:
        return dpropety
    else:
        return _get_dateproperty_from_system(path)


def format_filename_with_datetime(path: Path, dt: datetime) -> Path:
    """Generate a new filename by appending datetime to the original name"""
    timestamp = dt.strftime("%Y%m%d_%H%M%S")
    new_name = f"{path.stem}_{timestamp}{path.suffix}"
    return path.with_name(new_name)


def rename_image_file(path: Path) -> Path | None:
    """Rename image file by appending datetime to filename, if applicable"""
    dt = resolve_best_datetime(path)
    if not dt:
        return None

    new_path = format_filename_with_datetime(path, dt)
    if new_path != path:
        path.rename(new_path)
    return new_path


def batch_rename_images(paths: list[Path]) -> list[tuple[Path, Path | None]]:
    """Process a list of image files and rename them accordingly"""
    return [(p, rename_image_file(p)) for p in paths]


def get_unique_path(path: str, other_paths: list[str]) -> str:
    """Generate a unique filename by appending a counter if necessary"""
    dir_name, base = os.path.split(path)
    name, ext = os.path.splitext(base)
    counter = 1
    while True:
        if os.path.exists(path) or path in other_paths:
            path = posixpath.join(dir_name, f"{name} ({counter}){ext}")
            counter += 1
            continue
        return path
