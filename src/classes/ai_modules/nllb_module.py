from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QLineEdit, QFileDialog,
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

class NLLBModule(BaseModule):

    panelText = "Text-To-Text Translation"
    category = "CCMagic AI Modules"
    footer_text = " 1 Token"
    footer_coin = True;

    def __init__(self):
        super().__init__("NLLB", size=(120, 80))
        self.inputs = [(0, 30, "Input Text")]  # Inputs on the left
        self.outputs = [(120, 30, "Output Text")]
        self._create_ports()

        self.selected_language_src = "eng_Latn"
        self.selected_language_des = "spa_Latn"
        self.output_directory = "/tmp"

        self.gateway_conn = AI_Gateway_Conn()

    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running NLLB module with inputs: {inputs}")
        result = super().run(inputs, workflow_context)
        text = inputs.get(0, "")
        # Clean the text input to remove unwanted characters and whitespace
        text = text.strip().replace("\n", " ").replace("\r", " ").replace("\t", " ").replace("'","").replace('"', "")
        try:           
            payload = {
                "text": text,
                "src_lang": self.selected_language_src,
                "des_lang": self.selected_language_des,
                }
            self.gateway_conn.nllb_task(payload,self.after_nllb, self.run_error)
        except Exception as e:
            self.log_error(f"Error processing NLLB job: {e}")
            self._last_outputs[0] = None
            super().run_after()
        
        return result
    
    def run_error(self, error_message=None):
        if error_message:
            self.log_error(f"NLLB module encountered an error during execution: {error_message}")
        else:
            self.log_error("NLLB module encountered an error during execution.")
        super().run_after()  # Reset running state after execution

    def after_nllb(self, response):
         log.info(f"NLLB server response: {response}")
         if response.get("status") == True:
            self.job_id = response.get("job")
            status = json.loads('{"status": "created"}')
            self.timer_count = 0
            self.await_nllb_result(status)

    def await_nllb_result(self, response):
        log.info(f"({self.timer_count}s) Recieved status of NLLBjob {self.job_id}: {response}")
        if response.get("status") == "done":
            self.log_info(f"NLLB job {self.job_id} completed. Downloading result...")
            self.start_download_nllb_result()
        elif response.get("status") == "error":
            self.log_error(f"NLLB job {self.job_id} failed with error: {response.get('error')}")
            self.run_error(f"NLLB job {self.job_id} failed with error: {response.get('error')}")
        else:
            time.sleep(1)
            self.timer_count += 1
            self.gateway_conn.job_status(self.job_id, self.await_nllb_result, self.run_error)

    def start_download_nllb_result(self):
        try:
            self.gateway_conn.download_job(self.job_id, self.output_directory, self.process_nllb_result, self.run_error)
        except Exception as e:
            self.log_error(f"Error downloading NLLB job result: {e}")
            self.run_error()

    def process_nllb_result(self, response):
        if response.get("status") == True:
            self.log_info(f"NLLB job {self.job_id} result downloaded successfully.")
            # Assuming the downloaded file is a zip, you might want to extract it here.
            # For now, we just log the success and call run_after to reset the module state.
            with ZipFile(self.output_directory + "/" + self.job_id + ".zip", 'r') as zip_file:
                zip_file.extractall(self.output_directory + "/" + self.job_id)
            os.remove(self.output_directory + "/" + self.job_id + ".zip")  # Clean up the zip file after extraction

            output_path = self.output_directory + "/" + self.job_id + "/" + "output.txt"
            with open(output_path, "r") as f:
                self._last_outputs[0] = f.read()
            self.log_info(f"NLLB module outputs: {self._last_outputs}")
            super().run_after()  # Reset running state after execution


    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                dialog_parent = None
                scene = self.scene()
                if scene and scene.views():
                    dialog_parent = scene.views()[0]

                dialog = QDialog(dialog_parent)
                dialog.setWindowTitle(self.panelText)
                dialog.setMinimumSize(360, 200)

                main_layout = QVBoxLayout(dialog)

                help_url = "https://www.ccmagic.io/"
                help_label = QLabel(
                    f"This module is run remotely on CCMagic AI servers.<br>" \
                        "An API key and tokens are required. Get you account <a href=\"{help_url}\">here</a>.<br><br>" \
                        "NLLB (No Language Left Behind) is a<br>" \
                        "text-to-text system language translation system<br>" \
                        "Input-text: text to be translated<br>" \
                        "Outputs: translated text<br>" \
                        "Saves all files in specified directory", dialog
                )
                help_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                help_label.setOpenExternalLinks(True)
                main_layout.addWidget(help_label)

                form_layout = QFormLayout()
                form_layout.setLabelAlignment(Qt.AlignLeft)

                language_layout = QHBoxLayout()
                language_label_src = QLabel(get_app()._tr("Source Language:"), dialog)
                self.language_combo_src = QComboBox(dialog)
                for lang_name, lang_code in AI_Languages().nllb_languages.items():
                    self.language_combo_src.addItem(get_app()._tr(lang_name), lang_code)
                current_index = self.language_combo_src.findData(self.selected_language_src)
                if current_index >= 0:
                    self.language_combo_src.setCurrentIndex(current_index)
                language_layout.addWidget(language_label_src)
                language_layout.addWidget(self.language_combo_src)
                language_layout.addStretch(1)
                form_layout.addRow(language_layout)

                language_layout = QHBoxLayout()
                language_label_des = QLabel(get_app()._tr("Destination Language:"), dialog)
                self.language_combo_des = QComboBox(dialog)
                for lang_name, lang_code in AI_Languages().nllb_languages.items():
                    self.language_combo_des.addItem(get_app()._tr(lang_name), lang_code)
                current_index = self.language_combo_des.findData(self.selected_language_des)
                if current_index >= 0:
                    self.language_combo_des.setCurrentIndex(current_index)
                language_layout.addWidget(language_label_des)
                language_layout.addWidget(self.language_combo_des)
                language_layout.addStretch(1)
                form_layout.addRow(language_layout)

                current_project_path = getattr(get_app().project, "current_filepath", None)
                project_dir = os.path.dirname(current_project_path) if current_project_path else None
                output_initial = self.output_directory or tempfile.gettempdir()

                output_layout = QHBoxLayout()
                output_label = QLabel(get_app()._tr("Output directory:"), dialog)
                self.output_dir_line = QLineEdit(output_initial, dialog)
                self.output_dir_line.setReadOnly(True)
                output_button = QPushButton(get_app()._tr("Browse..."), dialog)
            except Exception as e:
                self.log_error(f"Error creating settings dialog: {e}")
                return
        
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
                self.selected_language_src = self.language_combo_src.currentData() or "eng_Latn"
                self.selected_language_des = self.language_combo_des.currentData() or "spa_Latn"
                self.output_directory = self.output_dir_line.text().strip() or tempfile.gettempdir()
                self.log_info(
                    "NLLB settings: language_src=%s, language_des=%s, output_directory=%s",
                    self.selected_language_src,
                    self.selected_language_des,
                    self.output_directory,
                )
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {
            "selected_language_src": self.selected_language_src,
            "selected_language_des": self.selected_language_des,
            "output_directory": self.output_directory
        }

    def set_settings(self, settings):
        self.selected_language_src = settings.get("selected_language_src", "eng_Latn")
        self.selected_language_des = settings.get("selected_language_des", "spa_Latn")
        self.output_directory = settings.get("output_directory", "")
