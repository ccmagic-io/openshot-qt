from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QFileDialog,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox,
    Qt
)
from classes.logger import log
from classes.app import get_app
from classes.ai_modules.__base_module import BaseModule


import os
import sys
import tempfile

# Add vendor directory to path to import yt_dlp
vendor_path = os.path.join(os.path.dirname(__file__), '..', '..', 'vendor')
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

import yt_dlp

class YoutubeModule(BaseModule):

    panelText = "Youtube Downloader"   #text shown in left panel
    category = "General Modules"
    footer_text = None
    output_path = ""  # Example setting for the module
    video_format = "mp4"  # Example setting for the module

    def __init__(self):
        super().__init__("Youtube", size=(120, 50))    # Text shown in the module box
        self.inputs = [(0, 30, "URL")]      # Inputs on the left
        self.outputs = [(120, 40, "Output Path")] # Outputs on the right
        self._create_ports()
        self.output_path = ""
        self.video_format = "mp4"  # Default video format

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running Youtube module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
        try:
            url = inputs.get(0, 0)

            ydl_opts = {
                'outtmpl': f'{self.output_path}/%(title)s.%(ext)s',  # Save as "title.ext"
                'format': 'bestvideo+bestaudio/best',          # Best quality
                'merge_output_format': self.video_format,                  # Merge into specified format
                'noplaylist': True,                            # Single video only
                'quiet': True,                                # Show progress
                'ignoreerrors': True,                          # Skip errors
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            result[0] = ydl_opts['outtmpl']
        except Exception as e:
            self.log_error(f"Error in Youtube module: {e}")
            result[0] = None
        ##

        super().run_after()  # Reset running state after execution
        return result
    
    # This method is called when the user double-clicks the module. You can create a dialog here for user settings.
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog_parent = None
            scene = self.scene()
            if scene and scene.views():
                dialog_parent = scene.views()[0]

            dialog = QDialog(dialog_parent)
            dialog.setWindowTitle(self.panelText)
            dialog.setMinimumSize(320, 120)

            current_project_path = getattr(get_app().project, "current_filepath", None)
            project_dir = os.path.dirname(current_project_path) if current_project_path else None
            output_initial = self.output_path or project_dir or ""

            main_layout = QVBoxLayout(dialog)
            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignLeft)

            output_layout = QHBoxLayout()
            output_label = QLabel(get_app()._tr("Output directory:"), dialog)
            self.output_dir_line = QLineEdit(output_initial, dialog)
            self.output_dir_line.setReadOnly(True)
            output_button = QPushButton(get_app()._tr("Browse..."), dialog)

            def choose_output_dir():
                start_dir = project_dir or os.path.expanduser("~")
                path = QFileDialog.getExistingDirectory(dialog, get_app()._tr("Select Output Directory"), start_dir)
                if path:
                    self.output_dir_line.setText(path)

            output_button.clicked.connect(choose_output_dir)
            output_layout.addWidget(self.output_dir_line)
            output_layout.addWidget(output_button)
            form_layout.addRow(output_label, output_layout)

            # Add video format dropdown
            format_label = QLabel(get_app()._tr("Video Format:"), dialog)
            self.format_combo = QComboBox(dialog)
            video_formats = ["avi", "flv", "mkv", "mov", "mp4", "webm"]
            self.format_combo.addItems(video_formats)
            self.format_combo.setCurrentText(self.video_format)
            form_layout.addRow(format_label, self.format_combo)

            main_layout.addLayout(form_layout)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)

            if dialog.exec_() == QDialog.Accepted:
                self.output_path = self.output_dir_line.text().strip() or tempfile.gettempdir()
                self.video_format = self.format_combo.currentText()
                self.log_info("Youtube module output directory: %s", self.output_path)
                self.log_info("Youtube module video format: %s", self.video_format)
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {"output_path": self.output_path, "video_format": self.video_format}

    def set_settings(self, settings):
        self.output_path = settings.get("output_path", "")
        self.video_format = settings.get("video_format", "mp4")