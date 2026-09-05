from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QRadioButton,
    QComboBox, QPushButton, QIcon, QPixmap, QtCore, QTimer, QThread, QObject, pyqtSignal,
    QSplitter, QGraphicsScene, QGraphicsView, QGraphicsItem, QRectF, QPainter, QPen, QBrush, QColor,
    QGraphicsLineItem, QPointF, QLineF, QTransform
)
from qt_api import Qt
from classes.logger import log
import os

class BaseModule(QGraphicsItem):

    panelText = "BaseModule"
    footer_text = "Base Module"
    footer_coin = False;
    _next_id = 0
    
    def __init__(self, name, inputs=None, outputs=None, size=(120, 60)):
        super().__init__()
        self.raw_name = name
        self.id = BaseModule._next_id
        BaseModule._next_id += 1
        self.name = f"{name} {self.id}"
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.inputs = list(inputs or [])  # List of input positions
        self.outputs = list(outputs or [])  # List of output positions
        self.size = tuple(size)
        self.port_items = []
        # Hover state for input/output points (indices or None)
        self._hovered_input = None
        self._hovered_output = None
        self._is_running = False  # Flag to draw yellow border during execution
        self._create_ports()

    def boundingRect(self):
        return QRectF(-70, -18, self.size[0] + 140, self.size[1] + 18)

    def paint(self, painter, option, widget):
        try:
            # Draw main border (blue or yellow if running)
            if self._is_running:
                painter.setPen(QColor(255, 255, 0))  # Yellow border during execution
            else:
                painter.setPen(QColor(147, 194, 238))  # Blue border normally
            painter.setBrush(QBrush(QColor(47, 56, 73)))
            painter.drawRoundedRect(0, 0, self.size[0], self.size[1], 5, 5)
            
            # Draw the module name above the box
            painter.setPen(QColor(147, 194, 238))
            name_rect = QRectF(0, -18, self.size[0], 18)
            painter.drawText(name_rect, Qt.AlignCenter | Qt.AlignVCenter, self.name)

            # Draw input labels to the right of connector bubble, inside box
            for inp in self.inputs:
                x, y, label = self._normalize_port(inp)
                if label:
                    painter.drawText(int(x + 5), int(y - 3), label)
            
            # Draw output labels to the left of connector bubble, inside box
            for out in self.outputs:
                x, y, label = self._normalize_port(out)
                if label:
                    # Right-align text ending before the connector
                    label_rect = QRectF(0, int(y - 8), int(x - 5), 20)
                    painter.drawText(label_rect, Qt.AlignRight, label)

            # Draw optional footer text and icon in the bottom-left corner
            footer_text = getattr(self, "footer_text", None)
            if footer_text:
                footer_rect = QRectF(20, self.size[1] - 18, self.size[0] - 24, 16)
                painter.setPen(QColor(179, 210, 255))
                painter.drawText(footer_rect, Qt.AlignLeft | Qt.AlignVCenter, str(footer_text))
                if(self.footer_coin):
                    try:
                        icon_path = os.path.join(
                            os.path.dirname(os.path.realpath(__file__)),
                            "..",
                            "..",
                            "themes",
                            "bze",
                            "yellow25.png",
                        )
                        if os.path.exists(icon_path):
                            pixmap = getattr(self, "_footer_icon_pixmap", None)
                            if pixmap is None:
                                pixmap = QPixmap(icon_path).scaled(15, 15)
                                self._footer_icon_pixmap = pixmap
                            painter.drawPixmap(4, self.size[1] - 18, pixmap)
                    except Exception:
                        pass
            # Draw a small remove '-' icon in the top-right corner
            try:
                icon_size = 12
                padding = 4
                icon_x = self.size[0] - icon_size - padding
                icon_y = padding
                # Background circle
                painter.setBrush(QBrush(QColor(68, 108, 169)))
                painter.setPen(QPen(QColor(68, 108, 169)))
                painter.drawRect(icon_x, icon_y, icon_size, 4)
                painter.setBrush(QBrush(QColor(179, 210, 255)))
                painter.setPen(QPen(QColor(179, 210, 255)))
                painter.drawRect(icon_x+1, icon_y+1, icon_size-1, 2)

                #painter.drawEllipse(icon_x, icon_y, icon_size, icon_size)
                # Minus sign
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                cx = icon_x + icon_size / 2
                cy = icon_y + icon_size / 2
                painter.drawLine(cx - 4, cy, cx + 4, cy)
            except Exception:
                pass
        except Exception as e:
            self.log_error(f"Error painting module: {e}")

    @staticmethod
    def _normalize_port(port):
        if not isinstance(port, (tuple, list)):
            return 0, 0, ""
        x = float(port[0]) if len(port) > 0 else 0.0
        y = float(port[1]) if len(port) > 1 else 0.0
        label = str(port[2]) if len(port) > 2 else ""
        return x, y, label

    def _log_prefix(self):
        return self.name

    def log_info(self, message, *args, **kwargs):
        log.info(f"[{self._log_prefix()}] {message}", *args, **kwargs)

    def log_warning(self, message, *args, **kwargs):
        log.warning(f"[{self._log_prefix()}] {message}", *args, **kwargs)

    def log_error(self, message, *args, **kwargs):
        log.error(f"[{self._log_prefix()}] {message}", *args, **kwargs)

    def log_debug(self, message, *args, **kwargs):
        log.debug(f"[{self._log_prefix()}] {message}", *args, **kwargs)

    def input_position(self, index):
        x, y, _ = self._normalize_port(self.inputs[index])
        return QPointF(x, y)

    def output_position(self, index):
        x, y, _ = self._normalize_port(self.outputs[index])
        return QPointF(x, y)

    def _create_ports(self):
        try:
            for port in self.port_items:
                scene = self.scene()
                if scene:
                    try:
                        scene.removeItem(port)
                    except Exception:
                        pass
            self.port_items = []
            for i, inp in enumerate(self.inputs):
                x, y, _ = self._normalize_port(inp)
                try:
                    port = PortItem(self, False, i, QPointF(x - 10, y - 5))
                    self.port_items.append(port)
                except Exception as e:
                    self.log_error(f"Error creating input port {i}: {e}")
            for i, out in enumerate(self.outputs):
                x, y, _ = self._normalize_port(out)
                try:
                    port = PortItem(self, True, i, QPointF(x, y - 5))
                    self.port_items.append(port)
                except Exception as e:
                    self.log_error(f"Error creating output port {i}: {e}")
        except Exception as e:
            self.log_error(f"Error in _create_ports: {e}")

    def get_settings(self):
        return {}

    def set_settings(self, settings):
        pass

    def run(self, inputs=None, workflow_context=None):
        # Set flag to draw yellow border during execution
        self._is_running = True
        self.update()  # Trigger a repaint to show the yellow border
        # Ensure the GUI has a chance to process the repaint immediately
        try:
            QtCore.QCoreApplication.processEvents()
        except Exception:
            pass
        
        if inputs is None:
            inputs = {}
        self._last_inputs = dict(inputs)
        self._last_outputs = {index: None for index in range(len(self.outputs))}
        self._workflow_context = workflow_context  # Store for subclasses to use
        
        return self._last_outputs
        
        return self._last_outputs


    def run_after(self):
        """Reset the running state and return to normal border color"""
        self._is_running = False
        self.update()  # Trigger a repaint to return to blue border
        try:
            QtCore.QCoreApplication.processEvents()
        except Exception:
            pass

    def hoverMoveEvent(self, event):
        # Change cursor to pointing hand when over the remove icon
        try:
            pos = event.pos()
            icon_size = 12
            padding = 4
            icon_rect = QRectF(self.size[0] - icon_size - padding, padding, icon_size, icon_size)
            if icon_rect.contains(pos):
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()
        except Exception:
            pass
        super().hoverMoveEvent(event)

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        try:
            self.unsetCursor()
        except Exception:
            pass
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.update()
        try:
            self.scene().update() if self.scene() else None
        except Exception:
            pass
        super().mouseDoubleClickEvent(event)   


    def mousePressEvent(self, event):
        # If the remove icon was clicked, remove this module and any connections
        try:
            pos = event.pos()
            icon_size = 12
            padding = 4
            icon_rect = QRectF(self.size[0] - icon_size - padding, padding, icon_size, icon_size)
            if icon_rect.contains(pos):
                scene = self.scene()
                if scene:
                    # Remove connections referencing this module
                    try:
                        for it in list(scene.items()):
                            if getattr(it, "from_item", None) is self or getattr(it, "to_item", None) is self:
                                try:
                                    scene.removeItem(it)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # Remove any explicit port items if present
                    try:
                        for port in list(self.port_items):
                            try:
                                scene.removeItem(port)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        scene.removeItem(self)
                    except Exception:
                        pass
                event.accept()
                return
        except Exception:
            pass
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            scene = self.scene()
            if scene:
                for it in scene.items():
                    if getattr(it, "from_item", None) is self or getattr(it, "to_item", None) is self:
                        try:
                            it.prepareGeometryChange()
                        except Exception:
                            pass
                        it.update()
                # Force views to repaint to avoid artifacts
                for view in scene.views():
                    try:
                        view.viewport().update()
                    except Exception:
                        view.update()
        return super().itemChange(change, value)
    

class PortItem(QGraphicsItem):
    def __init__(self, parent_icon, is_output, index, position):
        super().__init__(parent_icon)
        self.parent_icon = parent_icon
        self.is_output = is_output
        self.index = index
        self.setPos(position)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self._hovered = False

    def boundingRect(self):
        return QRectF(0, 0, 10, 10)

    def paint(self, painter, option, widget):
        try:
            painter.setPen(QPen(Qt.black, 1))
            if self._hovered:
                painter.setBrush(QBrush(QColor('#00cc66')))
            elif self.is_output:
                painter.setBrush(QBrush(Qt.red))
            else:
                painter.setBrush(QBrush(Qt.blue))
            painter.drawRect(self.boundingRect())
        except Exception as e:
            if getattr(self, 'parent_icon', None) is not None:
                self.parent_icon.log_error(f"Error painting PortItem: {e}")
            else:
                log.error(f"Error painting PortItem: {e}")

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.unsetCursor()
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        scene = self.scene()
        if not scene:
            return
        if self.is_output:
            scene.start_connection(self.parent_icon, self.index)
        else:
            scene.complete_connection(self.parent_icon, self.index)
        event.accept()
        return
