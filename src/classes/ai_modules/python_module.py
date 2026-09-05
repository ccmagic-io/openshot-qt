from qt_api import (
    QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QTextEdit
)
from qt_api import Qt
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class PythonModule(BaseModule):

    panelText = "Python"
    category = "General Modules"
    footer_text = None
    user_code = ""
    
    def __init__(self):
        super().__init__("Python", size=(120, 60))
        self.inputs = [(0, 20, "A"), (0, 40, "B")]
        self.outputs = [(120, 20, "X"), (120, 40, "Y")]
        self._create_ports()
        # User-editable code for this module
        self.user_code = (
            "# Example code using inputs A and B to produce outputs X and Y\n"
            "import time # Import python packages as normal\n"
            "if A:\n" 
            "    X = A.upper()\n"
            "if B:\n"
            "    Y = B.lower()\n"
            "time.sleep(1)"
        )

    def run(self, inputs=None, workflow_context=None):
        if inputs is None:
            inputs = {}
        self.log_info(f"Running Python module with inputs: {inputs}")
        
        result = super().run(inputs, workflow_context)
        
        # Get input A from connected FilesModule output
        A = inputs.get(0, None)
        B = inputs.get(1, None)
        X = None
        Y = None
        
        ### Run user-defined Python code here ###
        local_ns = {}
        local_ns["A"] = A
        local_ns["B"] = B
        
        # Inject workflow object so user code can call workflow.stop()
        if workflow_context:
            local_ns["workflow"] = workflow_context
        
        try:
            exec(self.user_code or "", local_ns, local_ns)
        except Exception as e:
            self.log_error(f"Error running user code in PythonModule: {e}")
        X = local_ns.get("X", None)
        Y = local_ns.get("Y", None)

        ###   ### 
        
        result[0] = X
        result[1] = Y
        self.log_info(f"Python module outputs: {result}")
        super().run_after()  # Reset running state after execution
        return result

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog_parent = None
            scene = self.scene()
            if scene and scene.views():
                dialog_parent = scene.views()[0]
            dialog = QDialog(dialog_parent)
            dialog.setWindowTitle(self.panelText)
            dialog.setMinimumSize(600, 300)
            layout = QVBoxLayout(dialog)

            help_label = QLabel(
                "A and B are inputs; set variables `X` and `Y` as outputs.\n"
                "Use Python code to transform inputs into outputs.", dialog
            )
            layout.addWidget(help_label)

            code_box = QTextEdit(dialog)
            code_box.setPlainText(self.user_code)
            layout.addWidget(code_box)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            result = dialog.exec_()
            if result == QDialog.Accepted:
                self.user_code = code_box.toPlainText()
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {"user_code": self.user_code}

    def set_settings(self, settings):
        self.user_code = settings.get("user_code", "")