from unittest import result

from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QRadioButton, QComboBox, QPushButton, QLineEdit, QFileDialog,
    Qt
)
from classes.logger import log
from classes.app import get_app
from classes.ai_modules.__base_module import BaseModule
from classes.ai_languages import AI_Languages
from classes.ai_gateway_conn import AI_Gateway_Conn

import os
import tempfile
from datetime import date, datetime, timedelta
import json
from zipfile import ZipFile


# TODO: use QT time, not time.sleep, to prevent openshot crashes
import time

class WhisperModule(BaseModule):

    panelText = "Whisper ASR"
    category = "CCMagic AI Modules"
    footer_text = " 1 Token"
    footer_coin = True;

    def __init__(self):
        super().__init__("Whisper ASR", size=(120, 120))
        self.inputs = [(0, 30, "Audio Path")]
        self.outputs = [(120, 20, "txt"),(120, 40, "srt"),(120, 60, "vtt"),(120, 80, "json"),(120, 100, "tsv")]  # Outputs on the right
        self._create_ports()

        self.selected_task = "transcribe"
        self.selected_language = "en"
        self.output_directory = ""

        self.gateway_conn = AI_Gateway_Conn()

    def run(self, inputs=None, workflow_context=None):


    
        self.log_info(f"Running Whisper module with inputs: {inputs}")
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
        self.filepath = inputs.get(0, None)
        if os.path.isfile(self.filepath):
            try:
                self.log_info(f"File found: {self.filepath}")
                payload = {
                    "file": self.filepath,
                    "task": self.selected_task,
                    "language": self.selected_language,
                    }
                self.gateway_conn.whisper_task(payload,self.after_whisper, self.run_error)

            except Exception as e:
                self.log_error(f"Error during Whisper module execution: {e}")
                result[0] = None # txt
                result[1] = None # srt
                result[2] = None # vtt
                result[3] = None # json
                result[4] = None # tsv
                return result

        else:
            self.log_error(f"File not found: {self.filepath}")
            result[0] = None # txt
            result[1] = None # srt
            result[2] = None # vtt
            result[3] = None # json
            result[4] = None # tsv
            return result
        
    def run_error(self):
        self.log_error("Whisper module encountered an error during execution.")
        super().run_after()  # Reset running state after execution

    def after_whisper(self, response):
         log.info(f"Whisper server response: {response}")
         if response.get("status") == True:
            self.job_id = response.get("job")
            status = json.loads('{"status": "created"}')
            self.timer_count = 0
            self.await_whisper_result(status)

    
    
    def await_whisper_result(self, response):
        log.info(f"({self.timer_count}s) Recieved status of Whisper job {self.job_id}: {response}")
        if response.get("status") == "done":
            self.log_info(f"Whisper job {self.job_id} completed. Downloading result...")
            self.start_download_whisper_result()
        elif response.get("status") == "error":
            self.log_error(f"Whisper job {self.job_id} failed with error: {response.get('error')}")
            self.run_error()
        else:
            time.sleep(1)
            self.timer_count += 1
            self.gateway_conn.job_status(self.job_id, self.await_whisper_result, self.run_error)

    def start_download_whisper_result(self):
        try:
            self.gateway_conn.download_job(self.job_id, self.output_directory, self.process_whisper_result, self.run_error)
        except Exception as e:
            self.log_error(f"Error downloading Whisper job result: {e}")
            self.run_error()

    def process_whisper_result(self, response):
        if response.get("status") == True:
            self.log_info(f"Whisper job {self.job_id} result downloaded successfully.")
            # Assuming the downloaded file is a zip, you might want to extract it here.
            # For now, we just log the success and call run_after to reset the module state.
            with ZipFile(self.output_directory + "/" + self.job_id + ".zip", 'r') as zip_file:
                zip_file.extractall(self.output_directory + "/" + self.job_id)
            os.remove(self.output_directory + "/" + self.job_id + ".zip")  # Clean up the zip file after extraction

            # Get the base name (last part of the path)
            base_name = os.path.basename(self.filepath)
            # Split into name and extension
            name, ext = os.path.splitext(base_name)

            with open(os.path.join(self.output_directory, self.job_id, name + ".txt"), "r") as f:
                self._last_outputs[0] = f.read()
            with open(os.path.join(self.output_directory, self.job_id, name + ".srt"), "r") as f:
                self._last_outputs[1] = f.read()
            with open(os.path.join(self.output_directory, self.job_id, name + ".vtt"), "r") as f:
                self._last_outputs[2] = f.read()
            with open(os.path.join(self.output_directory, self.job_id, name + ".json"), "r") as f:
                self._last_outputs[3] = f.read()
            with open(os.path.join(self.output_directory, self.job_id, name + ".tsv"), "r") as f:
                self._last_outputs[4] = f.read()

            self.log_info(f"Whisper module outputs: {self._last_outputs}")
            super().run_after()  # Reset running state after execution
            

        


    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog_parent = None
            scene = self.scene()
            if scene and scene.views():
                dialog_parent = scene.views()[0]

            dialog = QDialog(dialog_parent)
            dialog.setWindowTitle(self.panelText)
            dialog.setMinimumSize(360, 260)

            main_layout = QVBoxLayout(dialog)

            help_url = "https://www.ccmagic.io/"
            help_label = QLabel(
                f"This module is run remotely on CCMagic AI servers.<br>" \
                    "An API key and tokens are required. Get you account <a href=\"{help_url}\">here</a>.<br><br>" \
                    "OpenAI Whisper is an automatic speech recognition (ASR) system<br>" \
                    "capable of transcribing spoken language from audio inputs with high accuracy.<br>" \
                    "Input: File path<br>" \
                    "Outputs: various forms of text as strings<br>" \
                    "Saves all files in specified directory", dialog
            )
            help_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            help_label.setOpenExternalLinks(True)
            main_layout.addWidget(help_label)

            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignLeft)

            task_layout = QHBoxLayout()
            task_label = QLabel(get_app()._tr("Task:"), dialog)
            self.transcribe_radio = QRadioButton(get_app()._tr("Transcribe"), dialog)
            self.translate_radio = QRadioButton(get_app()._tr("Translate"), dialog)
            self.transcribe_radio.setChecked(self.selected_task == "transcribe")
            self.translate_radio.setChecked(self.selected_task == "translate")
            task_layout.addWidget(task_label)
            task_layout.addWidget(self.transcribe_radio)
            task_layout.addWidget(self.translate_radio)
            task_layout.addStretch(1)
            form_layout.addRow(task_layout)

            language_layout = QHBoxLayout()
            language_label = QLabel(get_app()._tr("Language:"), dialog)
            self.language_combo = QComboBox(dialog)
            for lang_name, lang_code in AI_Languages().asr_languages.items():
                self.language_combo.addItem(get_app()._tr(lang_name), lang_code)
            current_index = self.language_combo.findData(self.selected_language)
            if current_index >= 0:
                self.language_combo.setCurrentIndex(current_index)
            language_layout.addWidget(language_label)
            language_layout.addWidget(self.language_combo)
            language_layout.addStretch(1)
            form_layout.addRow(language_layout)


            current_project_path = getattr(get_app().project, "current_filepath", None)
            project_dir = os.path.dirname(current_project_path) if current_project_path else None
            output_initial = self.output_directory or project_dir or ""

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

            main_layout.addLayout(form_layout)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)

            if dialog.exec_() == QDialog.Accepted:
                self.selected_task = "translate" if self.translate_radio.isChecked() else "transcribe"
                self.selected_language = self.language_combo.currentData() or "en"
                self.output_directory = self.output_dir_line.text().strip() or tempfile.gettempdir()
                self.log_info(
                    "Whisper settings: task=%s, language=%s, output_dir=%s",
                    self.selected_task,
                    self.selected_language,
                    self.output_directory,
                )
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {"selected_task": self.selected_task, "selected_language": self.selected_language, "output_directory": self.output_directory}

    def set_settings(self, settings):
        self.selected_task = settings.get("selected_task", "transcribe")
        self.selected_language = settings.get("selected_language", "en")
        self.output_directory = settings.get("output_directory", "")
