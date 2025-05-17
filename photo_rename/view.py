from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
)

from photo_rename.filing import (
    extract_base_name,
    extract_invalid_chars,
    extract_invalid_formats,
)
from photo_rename.shared import RenameResult
from photo_rename.vm import MainWindowViewModel


class ColumnIndex:

    BEFORE = 0
    AFTER = 1
    DATE = 2
    TYPE = 3


class MainWindow(QMainWindow):

    def __init__(self, vm: MainWindowViewModel, ui_file: QFile) -> None:
        super().__init__()
        self.__vm = vm
        self.__ui_file = ui_file
        self._init_ui()

        self.__vm.table_created.connect(self._on_table_created)
        self.__vm.table_updated.connect(self._on_table_updated)
        self.__vm.rename_completed.connect(self._on_rename_completed)

    def _init_ui(self) -> None:
        self.__ui_file.open(QFile.ReadOnly)
        ui = QUiLoader().load(self.__ui_file, self)
        self.__ui_file.close()
        self.setCentralWidget(ui)

        self.button_select_files = ui.findChild(QPushButton, "btnSelectFiles")
        self.button_reset = ui.findChild(QPushButton, "btnReset")
        self.button_apply = ui.findChild(QPushButton, "btnApply")
        self.label_num_files = ui.findChild(QLabel, "lblNumFiles")
        self.table_file_names = ui.findChild(QTableWidget, "tblFileNames")
        self.text_date_format = ui.findChild(QLineEdit, "txtDateFormat")
        self.radio_group = QButtonGroup()
        self.radio_group.addButton(
            ui.findChild(QRadioButton, "rbtnDateOnly"),
            id=0,
        )
        self.radio_group.addButton(
            ui.findChild(QRadioButton, "rbtnDateAftOri"),
            id=1,
        )
        self.radio_group.addButton(
            ui.findChild(QRadioButton, "rbtnDateBefOri"),
            id=2,
        )

        self.table_file_names.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.button_select_files.clicked.connect(self._on_file_button_clicked)
        self.button_reset.clicked.connect(self._on_reset_button_clicked)
        self.table_file_names.itemChanged.connect(self._on_table_item_changed)
        self.table_file_names.itemDoubleClicked.connect(
            self._on_table_item_double_clicked
        )
        self.text_date_format.editingFinished.connect(self._on_date_fmt_changed)
        self.radio_group.idClicked.connect(self._on_radio_clicked)
        self.button_apply.clicked.connect(self._on_apply_button_clicked)

        self.text_date_format.setText(self.__vm.get_date_format())
        self.radio_group.button(self.__vm.get_naming_method()).setChecked(True)

    def _on_file_button_clicked(self) -> None:
        dialog = QFileDialog(
            self,
            caption="ファイルを選択",
            directory=self.__vm.get_last_opened_folder(),
            filter=self.__vm.get_type_filter(),
        )
        dialog.selectNameFilter(self.__vm.get_default_type_filter())
        dialog.setFileMode(QFileDialog.ExistingFiles)

        if dialog.exec():
            file_paths = dialog.selectedFiles()
            self.__vm.update_paths(file_paths)
            self.__vm.set_last_opened_folder(dialog.directory().absolutePath())

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        self.__vm.update_table_data(item.data(Qt.UserRole), item.text())

    def _on_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        if item.column() != ColumnIndex.BEFORE:
            return
        self.__vm.view_table_data(item.data(Qt.UserRole))

    def _on_table_created(self, table: list[str]) -> None:
        n_rows = len(table)
        self.table_file_names.blockSignals(True)
        self.table_file_names.setSortingEnabled(False)
        self.table_file_names.clearContents()
        self.table_file_names.setRowCount(0)

        self.table_file_names.setRowCount(n_rows)

        for index, row in enumerate(table):
            items = []
            for icol, data in enumerate(row):
                item = QTableWidgetItem(data)
                item.setData(Qt.UserRole, index)
                if icol == 1:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table_file_names.setItem(index, icol, item)
                items.append(item)

        self.table_file_names.setSortingEnabled(True)
        self.table_file_names.blockSignals(False)

        if n_rows > 0:
            self.label_num_files.setText(f"選択済み: {n_rows} ファイル")
        else:
            self.label_num_files.setText("")

    def _on_table_updated(self, index: int, data: list[str]) -> None:
        self.table_file_names.blockSignals(True)
        self.table_file_names.setSortingEnabled(False)

        for irow in range(self.table_file_names.rowCount()):
            item1 = self.table_file_names.item(irow, ColumnIndex.AFTER)
            item2 = self.table_file_names.item(irow, ColumnIndex.DATE)
            if item1.data(Qt.UserRole) != index:
                continue

            item1.setText(data[0])
            item2.setText(data[1])
            break

        self.table_file_names.setSortingEnabled(True)
        self.table_file_names.blockSignals(False)

    def _on_date_fmt_changed(self) -> None:
        text = self.text_date_format.text()

        if not text:
            self.text_date_format.setText(self.__vm.get_date_format())
            return

        invalid_chars = extract_invalid_chars(text)
        invalid_fmts = extract_invalid_formats(text)
        invalids_strs = [f'"{s}"' for s in (invalid_chars + invalid_fmts)]
        if invalids_strs:
            QMessageBox.warning(
                self,
                "無効な文字・書式",
                "無効な文字・書式が含まれています:"
                f" \n{', '.join(invalids_strs)}",
            )
            self.text_date_format.setText(self.__vm.get_date_format())
            return

        self.__vm.set_date_format(self.text_date_format.text())
        self.__vm.refresh_paths()

    def _on_radio_clicked(self, id_: int) -> None:
        self.__vm.set_naming_method(id_)
        self.__vm.refresh_paths()

    def _on_reset_button_clicked(self) -> None:
        self.__vm.refresh_paths()

    def _on_apply_button_clicked(self) -> None:
        if self.__vm.get_n_files() == 0:
            return

        reply = QMessageBox.question(
            self,
            "名前の変更",
            "名前を書き換えますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.No:
            return

        self.__vm.apply_renaming()

    def _on_rename_completed(
        self, results: list[tuple[str, RenameResult]]
    ) -> None:
        success_indices = []
        failure_names = []
        for i, (path, result) in enumerate(results):
            if result == RenameResult.SUCCESS:
                success_indices.append(i)
            elif result == RenameResult.FAILURE:
                failure_names.append(extract_base_name(path))

        self.__vm.delete_table_data(success_indices)

        message = f"{len(success_indices)} 件のファイル名を変更しました"
        if len(failure_names) > 0:
            failure_names_str = "\n".join(failure_names)
            message += f"\n\n以下のファイル名の変更に失敗しました:\n{failure_names_str}"

        QMessageBox.information(self, "名前の変更", message)
