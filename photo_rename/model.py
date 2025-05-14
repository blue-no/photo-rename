import os
from collections import namedtuple
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from photo_rename.config import Config, try_save_config
from photo_rename.filing import (
    DateType,
    get_unique_path,
    replace_path_filename,
    resolve_best_datetime,
)
from photo_rename.shared import NamingMethod, RenameResult

PathMap = namedtuple(
    "FilePathMap",
    [
        "original_path",
        "mapped_path",
        "dtype",
    ],
)


class MainWindowModel(QObject):
    path_map_created = Signal(list)
    path_map_updated = Signal(int, PathMap)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.__config = config

        self._path_map: list[PathMap] = []
        self._paths: list[str] = []

    def create_path_map(self, paths: str) -> None:
        map_ = []
        other_paths = []
        for path in paths:
            dproperty = resolve_best_datetime(path)
            if dproperty.dtype != DateType.NO_DATA:
                f_date = dproperty.dt.strftime(self.__config.date_format)

                method = self.__config.naming_method
                if method == NamingMethod.DATE_ONLY:
                    new_path = replace_path_filename(path, f"{f_date}")
                elif method == NamingMethod.DATE_BEFORE_ORIGINAL:
                    new_path = replace_path_filename(path, f"{f_date}{{name}}")
                elif method == NamingMethod.DATE_AFTER_ORIGINAL:
                    new_path = replace_path_filename(path, f"{{name}}{f_date}")

                if path != new_path:
                    new_path = get_unique_path(new_path, other_paths)
                else:
                    new_path = path
            else:
                new_path = path

            map_.append(PathMap(path, new_path, dproperty.dtype))
            other_paths.append(new_path)

        self._path_map = map_
        self._paths = paths
        self.path_map_created.emit(map_)

    def update_path_map(self, index: int, new_path: str) -> None:
        original_path = self._path_map[index].original_path
        if new_path != original_path:
            other_paths = [
                path for i, path in enumerate(self._path_map) if i != index
            ]
            new_path = get_unique_path(new_path, other_paths)
        new_map = PathMap(original_path, new_path, DateType.MANUAL)

        self._path_map[index] = new_map
        self.path_map_updated.emit(index, new_map)

    def delete_path_map(self, indices: list[int]) -> None:
        for index in sorted(indices, reverse=True):
            self._path_map.pop(index)
            self._paths.pop(index)
        self.path_map_created.emit(self._path_map)

    def apply_path_map(self, index: int) -> tuple[str, RenameResult]:
        map_ = self._path_map[index]
        old_path = map_.original_path
        new_path = map_.mapped_path
        try:
            if old_path != new_path:
                os.rename(old_path, new_path)
            return (old_path, RenameResult.SUCCESS)
        except Exception:
            return (old_path, RenameResult.FAILURE)

    def get_path_map(self, index: int) -> PathMap:
        return self._path_map[index]

    def get_paths(self) -> list[str]:
        return self._paths

    def get_n_files(self) -> int:
        return len(self._paths)

    @property
    def date_format(self) -> str:
        return self.__config.date_format

    @date_format.setter
    def date_format(self, value: str) -> None:
        self.__config.date_format = value
        try_save_config(self.__config)

    @property
    def naming_method(self) -> NamingMethod:
        return self.__config.naming_method

    @naming_method.setter
    def naming_method(self, value: NamingMethod) -> None:
        self.__config.naming_method = value
        try_save_config(self.__config)

    @property
    def last_opened_folder(self) -> Path:
        return self.__config.last_opened_folder

    @last_opened_folder.setter
    def last_opened_folder(self, value: Path) -> None:
        self.__config.last_opened_folder = value
        try_save_config(self.__config)
