from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QPushButton
)
from qt_api import Qt
from classes.app import get_app
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class FilesModule(BaseModule):
    
    panelText = "Files: From Project"
    category = "General Modules"
    footer_text = None
    filePath = ""
    
    def __init__(self):
        super().__init__("File From Project", size=(120, 60))
        self.outputs = [(120, 30, "File Path")]
        self._create_ports()

    def run(self, inputs=None, workflow_context=None):
        if inputs is None:
            inputs = {}
        self.log_info(f"Running Files module with inputs: {inputs}")
        result = super().run(inputs, workflow_context)
        result[0] = self.filePath
        self.log_info(f"Files module output: {result}")
        super().run_after()  # Reset running state after execution
        return result

    def mouseDoubleClickEvent(self, event):
        max_length= 18;
        if event.button() == Qt.LeftButton:
            dialog_parent = None
            scene = self.scene()
            if scene and scene.views():
                dialog_parent = scene.views()[0]

            dialog = QDialog(dialog_parent)
            dialog.setWindowTitle(self.panelText)
            dialog.setMinimumSize(600, 300)
            layout = QVBoxLayout(dialog)

            file_list = QListWidget(dialog)
            file_list.setSelectionMode(QAbstractItemView.SingleSelection)
            file_list.setUniformItemSizes(True)
            file_list.setAlternatingRowColors(True)

            media_files = self._all_media_files()
            if media_files:
                for file_id, label, file_path in media_files:
                    item = QListWidgetItem(label)
                    item.setData(Qt.UserRole, file_id)
                    item.setToolTip(file_path)
                    file_list.addItem(item)
                file_list.setCurrentRow(0)
            else:
                no_item = QListWidgetItem(get_app()._tr("No imported video or audio files available."))
                no_item.setFlags(no_item.flags() & ~Qt.ItemIsSelectable)
                file_list.addItem(no_item)

            layout.addWidget(file_list)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            result = dialog.exec_()

            if result == QDialog.Accepted:
                cur = file_list.currentItem()
                if cur:
                    self.filePath = cur.toolTip() or ""
            self.footer_text = self.filePath if self.filePath else None
            if len(self.footer_text) > max_length:
                self.footer_text = "..." + self.footer_text[-(max_length-3):]
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
    
    def _all_media_files(self):
        app = getattr(self, "app", None) or get_app()
        files = app.project.get("files") if app and getattr(app, "project", None) else None
        media_files = []
        if not isinstance(files, list):
            return media_files

        for file_data in files:
            if not isinstance(file_data, dict):
                continue
            media_type = str(file_data.get("media_type", "") or "").strip().lower()
            if media_type not in {"audio", "video"}:
                continue

            file_path = str(file_data.get("path") or file_data.get("resource") or "")
            name = str(file_data.get("name") or file_path or file_data.get("id") or "")
            label = f"{media_type.capitalize()} — {name}"
            media_files.append((str(file_data.get("id") or file_path), label, file_path))

        media_files.sort(key=lambda item: (item[1].lower(), item[2].lower()))
        return media_files
    
    def get_settings(self):
        return {"filePath": self.filePath}

    def set_settings(self, settings):
        self.filePath = settings.get("filePath", "")
