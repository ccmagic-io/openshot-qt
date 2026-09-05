from qt_api import QDialog
from qt_api import Qt
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class FeedbackModule(BaseModule):

    panelText = "Feedback"   #text shown in left panel
    category = "General Modules"

    def __init__(self):
        super().__init__("Feedback", size=(120, 30))
        self.inputs = [(130, 20, "A")]
        self.outputs = [(-10, 20, "X")]
        self._create_ports()
    def run(self, inputs=None, workflow_context=None):
        result = super().run(inputs, workflow_context)        
        result[0] = inputs.get(0, None) if inputs else None
        super().run_after()  # Reset running state after execution
        return result
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        pass

    def set_settings(self, settings):
        pass