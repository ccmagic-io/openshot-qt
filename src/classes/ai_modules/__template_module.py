from qt_api import (
    QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QTextEdit
)
from qt_api import Qt
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class TemplateModule(BaseModule):

    panelText = "Template Module"   #text shown in left panel
    category = "General Modules"
    footer_text = "Template Module"
    footer_coin = False;
    template_setting = "default value"  # Example setting for the module

    def __init__(self):
        super().__init__("Template", size=(120, 60))    # Text shown above the module box
        self.inputs = [(0, 30, "A"), (0, 50, "B")]      # Inputs on the left
        self.outputs = [(120, 30, "X"), (120, 50, "Y")] # Outputs on the right
        self._create_ports()
        self.template_setting = "new default value"  # Initialize the setting with a new default value

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running Template module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
        A = inputs.get(0, None)
        B = inputs.get(1, None)
        X = A
        Y = B        
        result[0] = X
        result[1] = Y
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

                help_url = "https://www.openshot.org/"
                help_label = QLabel(
                    f"Some help text <a href=\"{help_url}\">here</a>", dialog
                )
                help_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                help_label.setOpenExternalLinks(True)
                layout.addWidget(help_label)

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)

                result = dialog.exec_()
                if result == QDialog.Accepted:
                    self.template_setting = code_box.toPlainText()  # Update the setting based on user input from the dialog
                event.accept()
            super().mouseDoubleClickEvent(event)
        except Exception as e:
            self.log_error(f"Error in TemplateModule: {e}")
                

    def get_settings(self):
        return {"template_setting": self.template_setting}

    def set_settings(self, settings):
        self.template_setting = settings.get("template_setting", "")