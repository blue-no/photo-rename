import os.path
import posixpath
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil import parser
from PIL import Image
from pillow_heif import register_heif_opener
from pymediainfo import MediaInfo

register_heif_opener()


class DateType(Enum):
    TAKEN = auto()
    UPDATED = auto()
    CREATED = auto()
    MODIFIED = auto()
    MANUAL = auto()
    NO_DATA = auto()


@dataclass
class DateProperty:
    dt: datetime | None
    dtype: DateType


def extract_base_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def extract_suffix(path: str) -> str:
    return os.path.splitext(path)[1]


def extract_invalid_formats(date_str: str) -> list[str]:
    invalid_fms = [r"%c", r"%x", r"%X"]
    return list(set(f for f in invalid_fms if f in date_str))


def extract_invalid_chars(path: str) -> list[str]:
    invalid_chars = r'<>:"/\|?*'
    return list(set(c for c in path if c in invalid_chars))


def replace_path_filename(path: str, f_name: str) -> str:
    dir_name, base = os.path.split(path)
    name, ext = os.path.splitext(base)

    return posixpath.join(dir_name, f"{f_name}{ext}".format(name=name))


def _get_dateproperty_from_metadata(path: str) -> DateProperty:
    """Get DateTimeOriginal or DateTime from metadata"""
    try:
        with Image.open(path) as image:
            exif_data = image.getexif()
            return _parse_image_metadata(exif_data)
    except Exception:
        pass

    try:
        tag_data = MediaInfo.parse(path)
        return _parse_media_metadata(tag_data)
    except Exception:
        pass

    return DateProperty(None, DateType.NO_DATA)


def _parse_image_metadata(meta_data: Image.Exif) -> DateProperty:
    if not meta_data:
        return DateProperty(None, DateType.NO_DATA)

    try:
        return DateProperty(  # DateTimeOriginal
            _parse_datetime_str_to_jst(meta_data.get_ifd(34665)[36867]),
            DateType.TAKEN,
        )
    except KeyError:
        pass

    try:
        return DateProperty(  # DateTime
            _parse_datetime_str_to_jst(meta_data[306]),
            DateType.UPDATED,
        )
    except KeyError:
        pass

    return DateProperty(None, DateType.NO_DATA)


def _parse_media_metadata(meta_data: MediaInfo) -> DateProperty:
    track = next(
        (t for t in meta_data.tracks if t.track_type == "General"), None
    )

    date = track.encoded_date
    if date is not None:
        return DateProperty(
            _parse_datetime_str_to_jst(str(date)),
            DateType.TAKEN,
        )

    date = track.tagged_date
    if date is not None:
        return DateProperty(
            _parse_datetime_str_to_jst(str(date)),
            DateType.UPDATED,
        )

    return DateProperty(None, DateType.NO_DATA)


def _parse_datetime_str_to_jst(datetime_str: str) -> datetime:
    date_, *time_ = datetime_str.split(" ")
    datetime_str = " ".join((date_.replace(":", "-"), *time_))
    dt = parser.parse(datetime_str)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
    return dt.astimezone(ZoneInfo("Asia/Tokyo"))


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


def resolve_best_datetime(path: str) -> DateProperty:
    """Select the best available datetime in priority: EXIF > creation > modified"""
    dpropety = _get_dateproperty_from_metadata(path)
    if dpropety.dtype != DateType.NO_DATA:
        return dpropety
    else:
        return _get_dateproperty_from_system(path)


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
