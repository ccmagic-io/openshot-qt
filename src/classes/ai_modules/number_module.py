from qt_api import (
    QDialog, QLabel, QVBoxLayout, Qt, QLineEdit, QDialogButtonBox, QFormLayout
)
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class NumberModule(BaseModule):

    panelText = "Number Constant"   #text shown in left panel
    category = "General Modules"
    footer_text = "Number: 0"
    number = 0

    def __init__(self):
        super().__init__("Number", size=(120, 60))    # Text shown above the module box
        self.inputs = []      # Inputs on the left
        self.outputs = [(120, 30, "Number")] # Outputs on the right
        self._create_ports()
        self.number = 0

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running Number module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
      
        result[0] = self.number
        
        ##

        super().run_after()  # Reset running state after execution
        return result
    
    # This method is called when the user double-clicks the module. You can create a dialog here for user settings.
    def mouseDoubleClickEvent(self, event):
        try:
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
                    "Number constant: 4 = int(4) | 4.1 = float(4.1) | 4.1char = 0", dialog
                )
                layout.addWidget(help_label)

                form_layout = QFormLayout()
                number_input = QLineEdit(dialog)
                number_input.setText(str(self.number))
                form_layout.addRow(QLabel("Number", dialog), number_input)

                layout.addLayout(form_layout)

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)

                result = dialog.exec_()
                if result == QDialog.Accepted:
                    text = number_input.text()
                    try:
                        if "." in text:
                            self.number = float(str(text.strip()))
                        else:
                            self.number = int(str(text).strip())
                    except Exception as e:
                        self.number =0
                        self.log_error(f"Error parsing number input: {e}")
                        
                    event.accept()
                    self.footer_text = "Number: " + str(self.number)
            super().mouseDoubleClickEvent(event)
        except Exception as e:
            self.log_error(f"Error in TemplateModule: {e}")


    def get_settings(self):
        return {"number": self.number}

    def set_settings(self, settings):
        self.number = settings.get("number", 0)