from qt_api import (QObject, QThread, pyqtSignal)

import requests
import json
from classes.logger import log
from classes.app import get_app


import shlex
import subprocess


class AI_Gateway_Conn:
    """
    This class defines the connection settings for the AI gateway in OpenShot.
    It includes the API key and the base URL for the AI services.
    """
    apikey: str
    url: str = "https://gateway.ccmagic.io:8443"

    def __init__(self):
        self.app = get_app()
        self.apikey= self.app.get_settings().get("ai-server-apikey") or ""

    def set_apikey(self, apikey: str):
        """Set the API key for the AI gateway if different from stored value."""
        self.apikey = apikey
    
    def get_apikey(self) -> str:
        """Return the current API key."""
        return self.apikey
    
    def check_apikey(self) -> bool:
        self.apikey = (self.app.get_settings().get("ai-server-apikey") or "").strip()
        if self.apikey:
            return True

        from windows.ai_tools_settings import AIToolsSettingsDialog

        log.info("API key not set. Prompting user to enter API key.")
        win = AIToolsSettingsDialog(None)
        result = win.exec_()

        if result == 1:
            self.apikey = (self.app.get_settings().get("ai-server-apikey") or "").strip()
            if self.apikey:
                return True

        log.info("API key dialog was cancelled or closed without a valid key.")
        return False
    
    def validate_apikey(self, success_callback=None, error_callback=None):
        """Validate the provided API key by sending a request to the AI gateway."""      
        curl_cmd = "curl -s -X POST " + self.url + "/auth/validate-key -H 'Content-Type: application/json' -d '{\"api_key\": \"" + self.apikey + "\"}'"
        CurlThreadRunner.run(curl_cmd, success_callback, error_callback)

    def job_status(self, job_id: str, success_callback=None, error_callback=None):
        curl_cmd = f"curl -s -X POST " + self.url + "/job/status -H \"Authorization: Bearer " + self.apikey + "\" -H \"Content-Type: application/json\" -d '{\"job\": \"" + job_id + "\"}'"
        CurlThreadRunner.run(curl_cmd, success_callback, error_callback)

    def download_job(self, job_id: str, output_dir: str, success_callback=None, error_callback=None):
        curl_cmd = f"curl -s -X POST " + self.url + "/job/download -H \"Authorization: Bearer " + self.apikey + "\" -H \"Content-Type: application/json\" -d '{\"job\": \"" + job_id + "\", \"type\": \"output\"}' -o \"" + output_dir + "/" + job_id + ".zip\""
        CurlThreadRunner.run(curl_cmd, success_callback, error_callback, False)

    def whisper_task(self, data, success_callback=None, error_callback=None):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary.")
            if not self.check_apikey():
                raise ValueError("API key is required to run this AI task.")
            """Submit a whisper task to the AI gateway."""
            curl_cmd = f"curl -s -X POST {self.url}/api/whisper -H \"Authorization: Bearer {self.apikey}\" -F \"file=@{data.get('file')}\" -F \"task={data.get('task')}\" -F \"language={data.get('language')}\""
            CurlThreadRunner.run(curl_cmd, success_callback, error_callback)
        except Exception as e:
            log.error(f"Error in whisper_task: {e}")
            if error_callback:
                error_callback(str(e))
    
    def xtts_task(self, data, success_callback=None, error_callback=None):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary.")
            if not self.check_apikey():
                raise ValueError("API key is required to run this AI task.")
            """Submit a xtts task to the AI gateway."""
            curl_cmd = f"curl -s -X POST {self.url}/api/xtts -H \"Authorization: Bearer {self.apikey}\" -F \"reference=@{data.get('reference')}\" -F \"text=\'{data.get('text')}\'\" -F \"language={data.get('language')}\""
            CurlThreadRunner.run(curl_cmd, success_callback, error_callback)
        except Exception as e:
            log.error(f"Error in xtts_task: {e}")
            if error_callback:
                error_callback(str(e))

    def llm_task(self, data, success_callback=None, error_callback=None):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary.")
            if not self.check_apikey():
                raise ValueError("API key is required to run this AI task.")
            """Submit a llm task to the AI gateway."""
            curl_cmd = f"curl -s -X POST {self.url}/api/llm -H \"Authorization: Bearer {self.apikey}\" -F \"prompt=\'{data.get('prompt')}\'\" -F \"model={data.get('model')}\""
            CurlThreadRunner.run(curl_cmd, success_callback, error_callback)
        except Exception as e:
            log.error(f"Error in llm_task: {e}")
            if error_callback:
                error_callback(str(e))

class CurlWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, curl_cmd):
        super().__init__()
        self.curl_cmd = curl_cmd
        self.capture_output=True

    def run(self):
        try:
            result = subprocess.run(
                shlex.split(self.curl_cmd),
                capture_output=self.capture_output,
                text=True,
                check=True
            )
            if self.capture_output:
                data = json.loads(result.stdout)
                self.finished.emit(data)
            else:
                self.finished.emit({"status": True})
        except Exception as e:
            log.error(f"Error executing cURL command: {e}")
            self.error.emit(str(e))

                
class CurlThreadRunner:
    """
    Static helper to run CurlWorker in a QThread.
    Call from any dialog or widget:
        CurlThreadRunner.run(curl_cmd, on_success, on_error)
    """
    @staticmethod
    def run(curl_cmd, success_callback, error_callback=None, capture_output=True):
        try:
            thread = QThread()
            worker = CurlWorker(curl_cmd)
            worker.capture_output=capture_output
            worker.moveToThread(thread)

            # Keep strong references so the QThread wrapper isn't garbage-collected
            # while the underlying Qt thread is still running.
            worker._thread = thread
            thread._worker = worker


            # Connect signals
            thread.started.connect(worker.run)
            
            success_callback = success_callback or self.null_callback
            error_callback=error_callback or self.null_callback
            worker.finished.connect(success_callback)
            worker.error.connect(error_callback)
            
            # Cleanup
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.start()
        except Exception as ex:
            log.error(f"Error in thread runner: {ex}")
        return thread  # optional: return if caller wants to track thread
    

    def null_callback(self, *args, **kwargs):
        """A no-op callback to prevent errors if no callback is provided."""
        pass
