import os

from qt_api import QDialog
from qt_api import Qt
from classes.app import get_app
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

class ImportModule(BaseModule):

    panelText = "Files: To Project"   #text shown in left panel
    category = "General Modules"
    footer_text = None

    def __init__(self):
        super().__init__("Import File to Project", size=(120, 60))    # Text shown above the module box
        self.inputs = [(0, 30, "File Path")]      # Inputs on the left
        self.outputs = [] # Outputs on the right
        self._create_ports()

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        self.log_info(f"Running Import module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
        input_path = inputs.get(0, None)
        if not input_path or not os.path.isfile(input_path):
                self.log_error("Input file not found in Import module: %s", input_path)
                result[0] = None
                return result

        try:
            app = get_app()
            # Add the selected file to the current OpenShot project
            app.window.files_model.add_files(input_path, quiet=True)
            result[0] = input_path
            self.log_info("Imported file into project: %s", input_path)
        except Exception as e:
            self.log_error("Failed to import file to project: %s", e, exc_info=1)
            result[0] = None

        super().run_after()  # Reset running state after execution
        return result