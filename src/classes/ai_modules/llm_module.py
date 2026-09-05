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
import re

# TODO: use QT time, not time.sleep, to prevent openshot crashes
import time

class XTTSModule(BaseModule):

    panelText = "Large Languge Model"
    category = "CCMagic AI Modules"
    footer_text = " 1 Token"
    footer_coin = True;

    def __init__(self):
        super().__init__("LLM", size=(120, 60))
        self.inputs = []  # Inputs on the left
        self.outputs = [(120, 30, "Response")]
        self._create_ports()

        self.selected_model = "llama3.2"
        self.output_directory = "/tmp"
        self.prompt = ""

        self.gateway_conn = AI_Gateway_Conn()

    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running LLM module with inputs: {inputs}")
        result = super().run(inputs, workflow_context)

        try:           
            payload = {
                "prompt": self.prompt,
                "model": self.selected_model,
                }
            self.log_info(f"Sending payload to LLM gateway: {payload}")
            self.gateway_conn.llm_task(payload,self.after_llm, self.run_error)
        except Exception as e:
            self.log_error(f"Error processing LLM job: {e}")
            self._last_outputs[0] = None
            super().run_after()
        
        return result
    
    def run_error(self, error_message=None):
        if error_message:
            self.log_error(f"LLM module encountered an error during execution: {error_message}")
        else:
            self.log_error("LLM module encountered an error during execution.")
        super().run_after()  # Reset running state after execution

    def after_llm(self, response):
         log.info(f"LLM server response: {response}")
         if response.get("status") == True:
            self.job_id = response.get("job")
            status = json.loads('{"status": "created"}')
            self.timer_count = 0
            self.await_llm_result(status)

    def await_llm_result(self, response):
        log.info(f"({self.timer_count}s) Recieved status of LLMjob {self.job_id}: {response}")
        if response.get("status") == "done":
            self.log_info(f"LLM job {self.job_id} completed. Downloading result...")
            self.start_download_llm_result()
        elif response.get("status") == "error":
            self.log_error(f"LLM job {self.job_id} failed with error: {response.get('error')}")
            self.run_error(f"LLM job {self.job_id} failed with error: {response.get('error')}")
        else:
            time.sleep(1)
            self.timer_count += 1
            self.gateway_conn.job_status(self.job_id, self.await_llm_result, self.run_error)

    def start_download_llm_result(self):
        try:
            log.info(f"Starting download of LLM job {self.job_id} result to directory: {self.output_directory}")
            self.gateway_conn.download_job(self.job_id, self.output_directory, self.process_llm_result, self.run_error)
        except Exception as e:
            self.log_error(f"Error downloading LLM job result: {e}")
            self.run_error()

    def process_llm_result(self, response):
        if response.get("status") == True:
            try:
                self.log_info(f"LLM job {self.job_id} result downloaded successfully.")
                # Assuming the downloaded file is a zip, you might want to extract it here.
                # For now, we just log the success and call run_after to reset the module state.
                self.log_info(f"Extracting LLM job {self.job_id} result...")
                with ZipFile(self.output_directory + "/" + self.job_id + ".zip", 'r') as zip_file:
                    zip_file.extractall(self.output_directory + "/" + self.job_id)
                os.remove(self.output_directory + "/" + self.job_id + ".zip")  # Clean up the zip file after extraction
                
                self.log_info(f"Reading output from LLM job {self.job_id}...")
                with open(os.path.join(self.output_directory, self.job_id, self.job_id + "-output.txt"), "r") as f:
                    def strip_non_ascii(text: str) -> str:
                        return ''.join(ch for ch in text if ord(ch) < 128)
                    t = f.read()
                    # Remove any text within parentheses to clean up the output
                    t = re.sub(r'\([^)]*\)', '', t)
                    self._last_outputs[0] = strip_non_ascii(t)

                self.log_info(f"LLM module outputs: {self._last_outputs}")
                super().run_after()  # Reset running state after execution
            except Exception as e:
                self.log_error(f"Error extracting and reading LLM job result: {e}")
                self.run_error()

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
                    f"This module is run remotely on CCMagic AI servers.<br>"
                    "An API key and tokens are required. Get you account <a href=\"{help_url}\">here</a>.<br><br>"
                    "Large Language Models are proficient in understanding and generating human-like text that covers a wide<br>"
                    "range of topics with nuanced language capabilities for tasks such as script writing or content creation.<br>"
                    "Outputs: text in the form of a string<br>"
                    "Saves all files in specified directory", dialog
                )
                help_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                help_label.setOpenExternalLinks(True)
                main_layout.addWidget(help_label)

                form_layout = QFormLayout()
                form_layout.setLabelAlignment(Qt.AlignLeft)

                model_layout = QHBoxLayout()
                model_label = QLabel(get_app()._tr("Model:"), dialog)
                self.model_combo = QComboBox(dialog)

                self.model_combo.addItem(get_app()._tr("Llama 3.2: Best general‑purpose writer"), "llama3.2")
                self.model_combo.addItem(get_app()._tr("Phi-4: Fastest + best for short scripts"), "phi4")
                self.model_combo.addItem(get_app()._tr("Gemma3: Best overall for narrative quality"), "gemma3")
                self.model_combo.addItem(get_app()._tr("Ministral-3: Best for creative storytelling"), "ministral-3")


                model_layout.addWidget(model_label)
                model_layout.addWidget(self.model_combo)
                model_layout.addStretch(1)
                form_layout.addRow(model_layout)

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

            prompt_label = QLabel(get_app()._tr("Prompt:"), dialog)
            self.prompt_line = QLineEdit(self.prompt, dialog)
            form_layout.addRow(prompt_label, self.prompt_line)

            main_layout.addLayout(form_layout)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)

            if dialog.exec_() == QDialog.Accepted:
                self.selected_model = self.model_combo.currentData() or "llama3.2"
                self.output_directory = self.output_dir_line.text().strip() or tempfile.gettempdir()
                self.prompt = self.prompt_line.text()
                self.log_info(
                    "LLM settings: model=%s, output_directory=%s, prompt=%s",
                    self.selected_model,
                    self.output_directory,
                    self.prompt,
                )
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {
            "selected_model": self.selected_model,
            "output_directory": self.output_directory,
            "prompt": self.prompt,
        }

    def set_settings(self, settings):
        self.selected_model = settings.get("selected_model", "llama3.2")
        self.output_directory = settings.get("output_directory", "")
        self.prompt = settings.get("prompt", "")
