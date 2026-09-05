from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QRadioButton,
    QComboBox, QPushButton, QFont, QIcon, QPixmap, QtCore, QTimer, QThread, QObject, pyqtSignal,
    QFileDialog, QSplitter, QGraphicsScene, QGraphicsView, QGraphicsItem, QRectF, QPainter, QPen, QBrush, QColor,
    QGraphicsLineItem, QPointF, QLineF, QTransform
)
from qt_api import Qt
from classes.app import get_app
from classes.logger import log
from classes.ai_languages import AI_Languages

from datetime import date, datetime, timedelta
import importlib
import json
import pkgutil
import sys
from classes.ai_modules.__base_module import BaseModule, PortItem


class WorkflowControlContext:
    """Context object for controlling workflow execution"""
    def __init__(self):
        self.should_stop = False
    
    def stop(self):
        """Stop the workflow execution"""
        self.should_stop = True
        log.info("Workflow stop requested")


class Connection(QGraphicsItem):
    def __init__(self, from_item, from_output, to_item, to_input):
        super().__init__()
        self.from_item = from_item
        self.from_output = from_output
        self.to_item = to_item
        self.to_input = to_input
        self.setZValue(-1)  # Behind icons

    def boundingRect(self):
        start = self.from_item.pos() + self.from_item.output_position(self.from_output)
        end = self.to_item.pos() + self.to_item.input_position(self.to_input)
        rect = QRectF(start, end).normalized()
        return rect.adjusted(-5, -5, 5, 5)

    def paint(self, painter, option, widget):
        start = self.from_item.pos() + self.from_item.output_position(self.from_output)
        end = self.to_item.pos() + self.to_item.input_position(self.to_input)
        painter.setPen(QPen(QColor("#4b92ad"), 5))  # Set color and thickness
        painter.drawLine(QLineF(start, end))

class WorkflowScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.connecting_from = None
        self.temp_line = None
        log.info("Loading AI modules...")
        self.__modules__ = []
        try:
            import classes.ai_modules as ai_modules_pkg
            for finder, module_name, is_pkg in pkgutil.iter_modules(ai_modules_pkg.__path__):
                if module_name.startswith("__"):
                    continue
                full_name = f"classes.ai_modules.{module_name}"
                log.info(f"Found AI module: {full_name}")
                module = importlib.import_module(full_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseModule) and attr is not BaseModule:
                        self.__modules__.append(attr)
        except Exception as e:
            log.error(f"Error loading AI modules: {e}")
            exit()
    def start_connection(self, from_item, from_output):
        self.connecting_from = (from_item, from_output)

    def cancel_connection(self):
        self.connecting_from = None
        if self.temp_line:
            try:
                self.removeItem(self.temp_line)
            except Exception:
                pass
            self.temp_line = None

    def input_is_taken(self, to_item, to_input):
        for item in self.items():
            if isinstance(item, Connection) and item.to_item is to_item and item.to_input == to_input:
                return True
        return False

    def complete_connection(self, to_item, to_input):
        if not self.connecting_from:
            return False
        if self.input_is_taken(to_item, to_input):
            self.cancel_connection()
            return False
        connection = Connection(self.connecting_from[0], self.connecting_from[1], to_item, to_input)
        self.addItem(connection)
        self.cancel_connection()
        return True

    def mousePressEvent(self, event):
        if self.connecting_from and event.button() == Qt.RightButton:
            self.cancel_connection()
            event.accept()
            return

        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, PortItem):
            if item.is_output:
                self.connecting_from = (item.parent_icon, item.index)
            else:
                if self.connecting_from:
                    self.complete_connection(item.parent_icon, item.index)
            event.accept()
            return

        if isinstance(item, tuple(self.__modules__)):
            pos = event.scenePos() - item.pos()
            for i, inp in enumerate(item.inputs):
                if QRectF(inp[0] - 5, inp[1] - 5, 10, 10).contains(pos):
                    if self.connecting_from:
                        # Create connection
                        connection = Connection(self.connecting_from[0], self.connecting_from[1], item, i)
                        self.addItem(connection)
                        self.cancel_connection()
                    return
            for i, out in enumerate(item.outputs):
                if QRectF(out[0] - 5, out[1] - 5, 10, 10).contains(pos):
                    self.connecting_from = (item, i)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.connecting_from:
            if not self.temp_line:
                self.temp_line = QGraphicsLineItem()
                pen = QPen(QColor("red"))   # Set color
                pen.setWidth(5)             # Set thickness (pixels)
                self.temp_line.setPen(pen)
                self.addItem(self.temp_line)
            start_pos = self.connecting_from[0].pos() + self.connecting_from[0].output_position(self.connecting_from[1])
            self.temp_line.setLine(QLineF(start_pos, event.scenePos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.connecting_from and not self.temp_line:
            self.connecting_from = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.connecting_from and event.key() == Qt.Key_Escape:
            self.cancel_connection()
            event.accept()
            return
        super().keyPressEvent(event)

class AIWorkflowDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        _ = get_app()._tr

        self.setWindowTitle(_("AI Workflow"))
        self.setObjectName("aiASRJobDialog")

        self.app = get_app()

        self.controller = controller

        self.scene = WorkflowScene()
        self.view = QGraphicsView(self.scene)
        self.view.setFocusPolicy(Qt.StrongFocus)

        self._build_ui()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        self.splitter = QSplitter(Qt.Horizontal)

        # Left panel: Menu bar with AI jobs
        self.left_panel = QListWidget()
        self.left_panel.setDragEnabled(False)  # Prevent dragging items
        self.left_panel.setDragDropMode(QListWidget.NoDragDrop)  # No drag/drop at all
        self.left_panel.setFixedWidth(200) # Set a fixed width for the left panel
        # Populate with available AI modules grouped by `category`
        categories_order = ["General Modules", "CCMagic AI Modules", "External AI Modules"]
        modules_by_cat = {}
        for module in self.scene.__modules__:
            cat = getattr(module, "category", "General Modules") or "General Modules"
            modules_by_cat.setdefault(cat, []).append(module)

        for cat in categories_order:
            mods = modules_by_cat.get(cat, [])
            if not mods:
                continue
            header_item = QListWidgetItem(cat)
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            header_item.setData(Qt.UserRole, "__header__")
            header_item.setBackground(QBrush(QColor(41, 50, 65)))
            header_font = QFont()
            header_font.setPointSize(11)
            header_font.setBold(True)
            header_item.setFont(header_font)
            self.left_panel.addItem(header_item)
            for module in mods:
                item = QListWidgetItem(module.panelText)
                item.setData(Qt.UserRole, module)
                self.left_panel.addItem(item)
        # Add any modules in other categories not listed in categories_order
        for cat, mods in modules_by_cat.items():
            if cat in categories_order:
                continue
            header_item = QListWidgetItem(cat)
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            header_item.setData(Qt.UserRole, "__header__")
            header_item.setBackground(QBrush(QColor(41, 50, 65)))
            header_font = QFont()
            header_font.setPointSize(11)
            header_font.setBold(True)
            header_item.setFont(header_font)
            self.left_panel.addItem(header_item)
            for module in mods:
                item = QListWidgetItem(module.panelText)
                item.setData(Qt.UserRole, module)
                self.left_panel.addItem(item)

        self.left_panel.itemClicked.connect(self._on_item_clicked)

        # Right panel: Graphics view for icons
        self.view.setMinimumSize(400, 300)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.view)

        main_layout.addWidget(self.splitter)

        # Custom buttons
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Workflow")
        self.load_button = QPushButton("Load Workflow")
        self.run_button = QPushButton("Run")
        self.close_button = QPushButton("Close")
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.load_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.close_button)
        self.save_button.clicked.connect(self._save_workflow)
        self.load_button.clicked.connect(self._load_workflow)
        self.run_button.clicked.connect(self._run_workflow)
        self.close_button.clicked.connect(self.reject)

        main_layout.addLayout(self.button_layout)

        self.setWindowIcon(QIcon("src/themes/cosmic/images/tool-generate-sparkle.svg"))
        self.setLayout(main_layout)

    def _on_item_clicked(self, item):
        text = item.text()
        icon = None

        try:
            for module in self.scene.__modules__:
                if module.panelText == text:
                    icon = module()
                    break
        except Exception as e:
            log.error(f"Error creating module instance for '{text}': {e}")
            return

        if icon:
            try:
                icon.setPos(50, 50)
                self.scene.addItem(icon)
            except Exception as e:
                log.error(f"Error adding AI module to workflow scene: {e}")
                return

    def _save_workflow(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save AI Workflow",
            "",
            "Workflow Files (*.workflow);;All Files (*)"
        )
        if not filename:
            return

        modules = [item for item in self.scene.items() if isinstance(item, BaseModule)]
        connections = [item for item in self.scene.items() if isinstance(item, Connection)]

        module_records = []
        module_id_map = {}
        for idx, module in enumerate(modules):
            module_id = str(idx)
            module_id_map[module] = module_id
            module_records.append({
                "id": module_id,
                "class_path": f"{module.__class__.__module__}.{module.__class__.__name__}",
                "x": module.pos().x(),
                "y": module.pos().y(),
                "settings": module.get_settings(),
            })

        connection_records = []
        for connection in connections:
            if connection.from_item in module_id_map and connection.to_item in module_id_map:
                connection_records.append({
                    "from_id": module_id_map[connection.from_item],
                    "from_output": connection.from_output,
                    "to_id": module_id_map[connection.to_item],
                    "to_input": connection.to_input,
                })

        workflow_data = {
            "modules": module_records,
            "connections": connection_records,
        }

        try:
            with open(filename, "w", encoding="utf-8") as fh:
                json.dump(workflow_data, fh, indent=2)
            log.info("Workflow saved to %s", filename)
        except Exception as e:
            log.error("Failed to save workflow: %s", e)

    def _load_workflow(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load AI Workflow",
            "",
            "Workflow Files (*.workflow);;All Files (*)"
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as fh:
                workflow_data = json.load(fh)
        except Exception as e:
            log.error("Failed to load workflow: %s", e)
            return

        module_map = {
            f"{cls.__module__}.{cls.__name__}": cls
            for cls in self.scene.__modules__
        }

        self.scene.clear()

        id_to_module = {}
        for module_record in workflow_data.get("modules", []):
            class_path = module_record.get("class_path")
            module_class = module_map.get(class_path)
            if not module_class:
                log.error("Unknown module class %s in workflow file", class_path)
                continue
            try:
                module = module_class()
            except Exception as e:
                log.error("Failed to instantiate module %s: %s", class_path, e)
                continue
            module.setPos(QPointF(float(module_record.get("x", 0)), float(module_record.get("y", 0))))
            module.set_settings(module_record.get("settings", {}))
            self.scene.addItem(module)
            id_to_module[module_record.get("id")] = module

        for connection_record in workflow_data.get("connections", []):
            from_module = id_to_module.get(str(connection_record.get("from_id")))
            to_module = id_to_module.get(str(connection_record.get("to_id")))
            if not from_module or not to_module:
                log.error("Skipping invalid connection: %s", connection_record)
                continue
            connection = Connection(
                from_module,
                int(connection_record.get("from_output", 0)),
                to_module,
                int(connection_record.get("to_input", 0)),
            )
            self.scene.addItem(connection)

        log.info("Workflow loaded from %s", filename)

    def _run_workflow(self):
        modules = [item for item in self.scene.items() if isinstance(item, BaseModule)]
        connections = [item for item in self.scene.items() if isinstance(item, Connection)]

        # Build connection map and dependency graph
        module_inputs = {module: {} for module in modules}
        module_dependencies = {module: set() for module in modules}
        
        for connection in connections:
            log.info("Workflow connection: %s.%s -> %s.%s", connection.from_item.name, connection.from_output, connection.to_item.name, connection.to_input)
            if connection.to_item in module_inputs and connection.from_item in module_inputs:
                module_inputs[connection.to_item][connection.to_input] = connection
                module_dependencies[connection.to_item].add(connection.from_item)

        for module in modules:
            log.info("Workflow module %s inputs=%s", module.name, list(module_inputs[module].keys()))

        # Topological sort to determine execution order
        execution_order = []
        visited = set()
        visiting = set()
        
        def visit(module):
            if module in visited:
                return True
            if module in visiting:
                log.error(f"Circular dependency detected involving {module.name}")
                return False
            
            visiting.add(module)
            
            # Visit all dependencies first
            for dep in module_dependencies[module]:
                if not visit(dep):
                    return False
            
            visiting.remove(module)
            visited.add(module)
            execution_order.append(module)
            return True
        
        # Visit all modules
        for module in modules:
            if not visit(module):
                log.error("Topological sort failed due to circular dependencies")
                return
        
        # Log dependency graph
        log.info("=" * 60)
        log.info("WORKFLOW DEPENDENCY GRAPH:")
        log.info("=" * 60)
        for module in modules:
            if module_dependencies[module]:
                deps = ", ".join([dep.name for dep in module_dependencies[module]])
                log.info(f"  {module.name} depends on: {deps}")
            else:
                log.info(f"  {module.name} (no dependencies)")
        
        # Log execution order
        log.info("=" * 60)
        log.info("EXECUTION ORDER:")
        log.info("=" * 60)
        for i, module in enumerate(execution_order, 1):
            log.info(f"  {i}. {module.name}")
        log.info("=" * 60)

        # Create workflow control context
        workflow_context = WorkflowControlContext()
        
        # Track outputs from each module
        outputs = {}

        # Execute modules in dependency order
        for module in execution_order:
            # Prepare inputs for this module
            input_values = {}
            
            for input_index, connection in module_inputs[module].items():
                if connection.from_item in outputs:
                    upstream_outputs = outputs.get(connection.from_item, {})
                    input_values[input_index] = upstream_outputs.get(connection.from_output)
                else:
                    input_values[input_index] = None
            
            # Execute module
            try:
                log.info(f"Executing module {module.name} with inputs: {input_values}")
                result = module.run(input_values, workflow_context)
                outputs[module] = result if isinstance(result, dict) else {}
                
                log.info(f"Executed {module.name}, outputs: {outputs[module]}")
                
                # Wait for module to complete async work (if any)
                wait_count = 0
                max_wait_iterations = 60000  # ~600 seconds with 10ms sleep
                while module._is_running and wait_count < max_wait_iterations:
                    try:
                        QtCore.QCoreApplication.processEvents()
                    except Exception:
                        pass
                    QtCore.QThread.msleep(10)
                    wait_count += 1
                
                # Update outputs after async work completes
                if hasattr(module, '_last_outputs'):
                    outputs[module] = module._last_outputs if isinstance(module._last_outputs, dict) else outputs[module]
                
                log.info(f"Module {module.name} async work complete, final outputs: {outputs[module]}")
            
            except Exception as e:
                log.error(f"Error executing module {module.name}: {e}")

            # Check if workflow should stop
            if workflow_context.should_stop:
                log.info("Workflow stopped by module request")
                return
        
        log.info("Workflow ran successfully.")