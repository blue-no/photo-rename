import os.path
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from photo_rename.filing import (
    DateType,
    extract_base_name,
    replace_path_filename,
)
from photo_rename.model import MainWindowModel, PathMap
from photo_rename.shared import NamingMethod


class MainWindowViewModel(QObject):

    table_created = Signal(list)
    table_updated = Signal(int, list)
    rename_completed = Signal(list)

    def __init__(self, model: MainWindowModel) -> None:
        super().__init__()
        self.__model = model
        self.__model.path_map_created.connect(self._on_path_map_created)
        self.__model.path_map_updated.connect(self._on_path_map_updated)

    def get_type_filter(self) -> str:
        return FileTypes.get_all_filters()

    def get_default_type_filter(self) -> str:
        return FileTypes.get_filter("すべての画像ファイル")

    def update_paths(self, paths: list[str]) -> None:
        paths_ = []
        for p in paths:
            if os.path.isfile(p) and p.split(".")[1] in FileTypes.get_types():
                paths_.append(p)
        self.__model.create_path_map(paths)

    def refresh_paths(self) -> None:
        self.update_paths(self.__model.get_paths())

    def update_table_data(self, index: int, new_name: str) -> None:
        map_ = self.__model.get_path_map(index)
        if new_name == "":
            self.__model.update_path_map(index, map_.mapped_path)
        else:
            new_path = replace_path_filename(map_.original_path, new_name)
            self.__model.update_path_map(index, new_path)

    def delete_table_data(self, indices: list[int]) -> None:
        self.__model.delete_path_map(indices)

    def view_table_data(self, index: int) -> None:
        self.__model.open_file(index)

    def set_date_format(self, fmt: str) -> None:
        self.__model.date_format = fmt

    def get_date_format(self) -> str:
        return self.__model.date_format

    def set_naming_method(self, id_: int) -> None:
        self.__model.naming_method = NamingMethod(id_)

    def get_naming_method(self) -> int:
        return self.__model.naming_method.value

    def set_last_opened_folder(self, path: str) -> None:
        self.__model.last_opened_folder = Path(path)

    def get_last_opened_folder(self) -> str:
        return self.__model.last_opened_folder.as_posix()

    def get_n_files(self) -> int:
        return self.__model.get_n_files()

    def apply_renaming(self) -> None:
        results = []
        for i in range(self.get_n_files()):
            ret = self.__model.apply_path_map(i)
            results.append(ret)

        self.rename_completed.emit(results)

    def _on_path_map_created(self, mappings: list[PathMap]) -> None:
        data = []
        for map_ in mappings:
            ori_name = extract_base_name(map_.original_path)
            new_name = extract_base_name(map_.mapped_path)
            dtype = DisplayedDateType.get(map_.dtype)
            data.append([ori_name, new_name, dtype])

        self.table_created.emit(data)

    def _on_path_map_updated(self, index: int, map_: PathMap) -> None:
        new_name = extract_base_name(map_.mapped_path)
        new_dtype = DisplayedDateType.get(map_.dtype)
        self.table_updated.emit(index, [new_name, new_dtype])


class DisplayedDateType:

    __dict = {
        DateType.TAKEN: "撮影日時",
        DateType.UPDATED: "更新日時",
        DateType.CREATED: "ファイル作成日時",
        DateType.MODIFIED: "ファイル更新日時",
        DateType.MANUAL: "修正済み",
        DateType.NO_DATA: "(情報なし)",
    }

    @classmethod
    def get(cls, key: DateType) -> str:
        return cls.__dict[key]


class FileTypes:

    __all = ["jpg", "jpeg", "png", "bmp", "gif", "heic", "heif"]
    __dict = {
        "すべての画像ファイル": __all,
        "HEIFファイル": ["heic", "heif"],
        "JPEGファイル": ["jpg", "jpeg"],
        "PNGファイル": ["png"],
        "BMPファイル": ["bmp"],
        "GIFファイル": ["gif"],
    }

    @classmethod
    def get_all_filters(cls) -> str:
        filter_str = ""
        for name, suffixes in cls.__dict.items():
            suffix_str = " ".join(["*." + s for s in suffixes])
            filter_str += f";;{name} ({suffix_str})"
        return filter_str

    @classmethod
    def get_filter(cls, name: str) -> str:
        suffixes = cls.__dict[name]
        suffix_str = " ".join(["*." + s for s in suffixes])
        return f"{name} ({suffix_str})"

    @classmethod
    def get_types(cls) -> list[str]:
        return cls.__all
