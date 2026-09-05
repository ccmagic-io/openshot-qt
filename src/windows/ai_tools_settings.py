"""
AI Tools Settings dialog and service controller.
"""

from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QWidget, QIcon, QPixmap, QtCore, QTimer, QCheckBox, QFileDialog, QThread, pyqtSignal, QObject
)
from qt_api import Qt
from classes.app import get_app
from classes.logger import log
from classes.ai_gateway_conn import AI_Gateway_Conn
import subprocess
import shlex
import json
import os


class AIToolsSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        _ = get_app()._tr

        self.src_path = os.path.dirname(os.path.realpath(__file__)).replace("windows","")

        self.setWindowTitle(_("AI Tools Settings"))
        self.setObjectName("aiToolsSettingsDialog")

        self.app = get_app()

        self._load_settings_from_store()

        self.apikeyEdit = QLineEdit(self.apikey)
        self.server_connect_button = QPushButton(_("Test API Key"))
        self.server_connect_button.clicked.connect(self._try_connect)
        self.server_status_icon = QLabel()
        self.server_status_icon.setPixmap(QPixmap(self.src_path + "themes/bze/white25.png").scaled(15, 15))
        self.token_balance_label = QLabel(_("Token Balance: N/A"))

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self._build_ui()

    def _load_settings_from_store(self):
        """Load AI settings from OpenShot's persistent settings store"""
        try:
            self.apikey= self.app.get_settings().get("ai-server-apikey") or ""
            log.info("Loaded AI settings from store")
        except Exception as ex:
            log.error(f"Failed to load AI settings: {ex}")

    def _save_to_store(self):
        """Save current settings to OpenShot's persistent settings store"""
        try:
            settings = self.app.get_settings()
            settings.set("ai-server-apikey", self.apikeyEdit.text())
            settings.save()
            log.info("AI settings saved to store")
        except Exception as ex:
            log.error(f"Failed to save AI settings: {ex}")

    def _build_ui(self):

        form_layout = QFormLayout()
        form_layout.addRow(QLabel(get_app()._tr("API Key:")), self.apikeyEdit)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        row_layout.addWidget(self.server_connect_button)
        row_layout.addWidget(self.server_status_icon)
        row_layout.addWidget(self.token_balance_label)

        form_layout.addRow(row)
        
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

        self.setWindowIcon(QIcon(self.src_path + "themes/cosmic/images/tool-generate-sparkle.svg"))
        self.setLayout(main_layout)
        self.setFixedSize(600, 150)

             

    def _try_connect(self):

        self.gateway_conn = AI_Gateway_Conn()
        self.gateway_conn.set_apikey(self.apikeyEdit.text())
        self.gateway_conn.validate_apikey(
            success_callback=self._update_gui,
            error_callback=self._handle_error
        )

    def _update_gui(self, result):
        if result.get("valid"):
            self.server_status_icon.setPixmap(
                QPixmap(self.src_path + "themes/bze/green25.png").scaled(15, 15)
            )

            if result.get("unlimited"):
                self.token_balance_label.setText("Token Balance: Unlimited")
            else:
                tokens = result.get("tokens_remaining", "N/A")
                self.token_balance_label.setText(f"Token Balance: {tokens}")
        else:
            self.server_status_icon.setPixmap(
                QPixmap(self.src_path + "themes/bze/red25.png").scaled(15, 15)
            )
    def _handle_error(self, msg):
        log.error(f"Error executing cURL: {msg}")
        self.server_status_icon.setPixmap(
            QPixmap(self.src_path + "themes/bze/red25.png").scaled(15, 15)
        )

  
    def accept(self):
        """Override accept to save settings before closing dialog"""
        self._save_to_store()
        super().accept()
    


class TokenCheckWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, curl_cmd):
        super().__init__()
        self.curl_cmd = curl_cmd

    def run(self):
        try:
            result = subprocess.run(
                shlex.split(self.curl_cmd),
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))
