# =========================================================================================
#
#        DeskPainter - VERSIÓN 4.2 (TOOLBAR VISIBLE POR DEFECTO)
#
#   - MEJORA UX: La aplicación ahora se inicia con la barra de herramientas flotante
#     visible en el escritorio por defecto, para un acceso inmediato.
#   - COMPORTAMIENTO MANTENIDO: Si el usuario cierra la barra de herramientas con la 'X',
#     la ventana se oculta pero la aplicación sigue activa en la bandeja del sistema.
#   - SINCRONIZACIÓN: La opción del menú "Mostrar Barra de Herramientas" se inicia
#     marcada para reflejar el estado visible inicial.
#
# =========================================================================================

import sys
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import (QPainter, QPixmap, QPen, QColor, QGuiApplication, QCursor, 
                         QKeyEvent, QAction, QIcon, QActionGroup, QCloseEvent)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu, QSystemTrayIcon, QColorDialog, QSlider, 
    QFileDialog, QLabel, QHBoxLayout, QWidgetAction, QTextEdit, QMainWindow, 
    QPushButton, QFrame, QGraphicsDropShadowEffect
)

# =========================================================================================
# SECCIÓN 0: ESTILOS, COLORES Y VENTANAS AUXILIARES
# =========================================================================================

THEME_COLORS = {
    'primary': '#6366f1', 'primary_hover': '#5855eb', 'danger': '#ef4444',
    'background': '#ffffff', 'background_alt': '#f8fafc', 'surface': '#ffffff',
    'border': '#e2e8f0', 'text': '#1e293b', 'text_secondary': '#64748b'
}

PRESET_COLORS = {
    "Rojo": "#ef4444", "Verde": "#22c55e", "Azul": "#3b82f6", "Amarillo": "#eab308",
    "Naranja": "#f97316", "Morado": "#a855f7", "Negro": "#000000", "Blanco": "#ffffff"
}

MODERN_STYLE = f"""
QMainWindow, QWidget {{ background-color: {THEME_COLORS['background']}; font-family: 'Segoe UI', sans-serif; }}
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {THEME_COLORS['surface']}, stop:1 {THEME_COLORS['background_alt']});
    border: 2px solid {THEME_COLORS['border']}; border-radius: 10px; padding: 6px; font-size: 16px;
    font-weight: 600; color: {THEME_COLORS['text']}; min-width: 32px; min-height: 32px;
}}
QPushButton:hover {{ border-color: {THEME_COLORS['primary']}; }}
QPushButton:pressed {{ background: {THEME_COLORS['primary_hover']}; color: white; }}
QPushButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {THEME_COLORS['primary']}, stop:1 {THEME_COLORS['primary_hover']});
    border-color: {THEME_COLORS['primary']}; color: white;
}}
QPushButton:disabled {{ background-color: {THEME_COLORS['background_alt']}; color: {THEME_COLORS['text_secondary']}; }}
QSlider::groove:horizontal {{ border: 1px solid {THEME_COLORS['border']}; height: 6px; background: {THEME_COLORS['background_alt']}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {THEME_COLORS['primary']}; width: 16px; margin: -5px 0; border-radius: 8px; }}
QLabel#width-label {{ font-weight: 600; color: {THEME_COLORS['text_secondary']}; }}
QLabel#color-indicator {{ border: 2px solid {THEME_COLORS['border']}; border-radius: 10px; min-width: 32px; min-height: 32px; }}
"""

# =========================================================================================
# SECCIÓN 1: BARRA DE HERRAMIENTAS, LIENZO Y VENTANA DE AYUDA (Clases completas)
# =========================================================================================

HOTKEY_GUIDE_HTML = """
<html><body style="font-family: Segoe UI, sans-serif; font-size: 10pt; color: #1e293b;">
<h3 style="color: #6366f1;">Atajos (En Modo Dibujo)</h3><table width="100%" cellspacing="0" cellpadding="4">
<tr style="background-color:#f1f5f9;"><td><b>P</b></td><td>Lápiz</td></tr><tr><td><b>E</b></td><td>Borrador</td></tr>
<tr style="background-color:#f1f5f9;"><td><b>G</b></td><td>Modo Fantasma</td></tr><tr><td><b>+</b>/<b>↑</b></td><td>Aumentar Grosor</td></tr>
<tr style="background-color:#f1f5f9;"><td><b>-</b>/<b>↓</b></td><td>Disminuir Grosor</td></tr><tr><td><b>C</b></td><td>Selector de Color</td></tr>
<tr style="background-color:#f1f5f9;"><td><b>Ctrl+S</b></td><td>Guardar</td></tr><tr><td><b>Ctrl+Z</b></td><td>Limpiar</td></tr>
<tr style="background-color:#f1f5f9;"><td><b>Esc</b></td><td>Salir de Modo</td></tr></table></body></html>"""

class HelpWindow(QWidget):
    def __init__(self):
        super().__init__();self.setWindowTitle("Ayuda");self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint);self.setFixedSize(280, 260)
        layout = QHBoxLayout(self);text_edit = QTextEdit(self);text_edit.setReadOnly(True);text_edit.setHtml(HOTKEY_GUIDE_HTML);layout.addWidget(text_edit)

class DrawingOverlay(QWidget):
    escape_pressed = pyqtSignal();hotkey_pressed = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent);self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool);self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);total_geometry = QRect();[total_geometry := total_geometry.united(s.geometry()) for s in QGuiApplication.screens()];self.setGeometry(total_geometry);self.canvas = QPixmap(total_geometry.size());self.canvas.fill(Qt.GlobalColor.transparent);self.last_pos = QPoint();self.drawing = False;self.pen_color = QColor(PRESET_COLORS["Rojo"]);self.pen_width = 5;self.current_tool = 'pen';self.guide_background_active = False;self.guide_color = QColor(30, 30, 30, 50);self.set_drawing_mode(False)
    def set_drawing_mode(self, active):self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not active);self.setCursor(QCursor(Qt.CursorShape.CrossCursor if active else Qt.CursorShape.ArrowCursor));self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if active else Qt.FocusPolicy.NoFocus); (self.activateWindow(), self.setFocus()) if active else None
    def set_tool(self, tool): self.current_tool = tool
    def set_pen_color(self, color): self.pen_color = color if color.isValid() else self.pen_color
    def set_pen_width(self, width): self.pen_width = max(1, min(50, width))
    def toggle_guide_background(self, active): self.guide_background_active = active; self.clear_canvas()
    def clear_canvas(self): self.canvas.fill(self.guide_color if self.guide_background_active else Qt.GlobalColor.transparent); self.update()
    def save_drawing(self):
        try:
            self.hide(); QApplication.processEvents();desktop_pixmap = QGuiApplication.primaryScreen().grabWindow(0);painter = QPainter(desktop_pixmap); painter.drawPixmap(self.geometry().topLeft(), self.canvas); painter.end();self.show()
            path, _ = QFileDialog.getSaveFileName(self, "Guardar Captura", os.path.expanduser("~/captura.png"), "PNG (*.png)")
            if path: desktop_pixmap.save(path)
        except Exception as e: print(f"Error al guardar: {e}"); self.show()
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key();modifiers = event.modifiers()
        if key == Qt.Key.Key_Escape: self.escape_pressed.emit(); return
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_S: self.hotkey_pressed.emit("save"); return
            if key == Qt.Key.Key_Z: self.hotkey_pressed.emit("clear"); return
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key == Qt.Key.Key_P: self.hotkey_pressed.emit("pen"); return
            if key == Qt.Key.Key_E: self.hotkey_pressed.emit("eraser"); return
            if key == Qt.Key.Key_G: self.hotkey_pressed.emit("guide"); return
            if key == Qt.Key.Key_C: self.hotkey_pressed.emit("color_picker"); return
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Up): self.hotkey_pressed.emit("width_up"); return
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Down): self.hotkey_pressed.emit("width_down"); return
        super().keyPressEvent(event)
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton: self.drawing = True; self.last_pos = e.position().toPoint()
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self.drawing and e.buttons() == Qt.MouseButton.LeftButton:
            painter = QPainter(self.canvas); painter.setRenderHint(QPainter.RenderHint.Antialiasing);pen = QPen(self.pen_color if self.current_tool == 'pen' else self.guide_color, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin);painter.setPen(pen)
            if self.current_tool == 'pen': painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            else: painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source if self.guide_background_active else QPainter.CompositionMode.CompositionMode_Clear)
            painter.drawLine(self.last_pos, e.position().toPoint()); self.last_pos = e.position().toPoint(); self.update()
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton: self.drawing = False
    def paintEvent(self, e: QtGui.QPaintEvent):
        painter = QPainter(self); painter.drawPixmap(0, 0, self.canvas)

class ToolbarWindow(QMainWindow):
    drawing_toggled = pyqtSignal(bool); tool_selected = pyqtSignal(str)
    color_picker_requested = pyqtSignal(); guide_toggled = pyqtSignal(bool)
    width_changed = pyqtSignal(int); save_requested = pyqtSignal()
    clear_requested = pyqtSignal(); help_requested = pyqtSignal()
    closed_by_user = pyqtSignal()
    def __init__(self):
        super().__init__();self.setWindowTitle("DeskPainter Tools");self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint);self.setStyleSheet(MODERN_STYLE);self.setFixedSize(560, 75)
        central_widget = QWidget(); self.setCentralWidget(central_widget);layout = QHBoxLayout(central_widget); layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(8)
        self.toggle_draw_btn = QPushButton("✏️"); self.toggle_draw_btn.setCheckable(True);self.color_indicator = QLabel(); self.color_indicator.setObjectName("color-indicator");self.pen_btn = QPushButton("✒️"); self.pen_btn.setCheckable(True);self.eraser_btn = QPushButton("🧼"); self.eraser_btn.setCheckable(True);self.color_btn = QPushButton("🎨");self.guide_btn = QPushButton("👻"); self.guide_btn.setCheckable(True);self.width_slider = QSlider(Qt.Orientation.Horizontal, minimum=1, maximum=50);self.width_label = QLabel("5"); self.width_label.setObjectName("width-label");self.save_btn = QPushButton("💾");self.clear_btn = QPushButton("🗑️");self.help_btn = QPushButton("❓")
        self.pen_btn.clicked.connect(lambda: self.tool_selected.emit('pen'));self.eraser_btn.clicked.connect(lambda: self.tool_selected.emit('eraser'))
        self.toggle_draw_btn.toggled.connect(self.drawing_toggled);self.color_btn.clicked.connect(self.color_picker_requested);self.guide_btn.toggled.connect(self.guide_toggled);self.width_slider.valueChanged.connect(self.width_changed);self.save_btn.clicked.connect(self.save_requested);self.clear_btn.clicked.connect(self.clear_requested);self.help_btn.clicked.connect(self.help_requested)
        for w in [self.toggle_draw_btn, self.color_indicator, self.pen_btn, self.eraser_btn, self.color_btn, self.guide_btn, self.width_slider, self.width_label, self.save_btn, self.clear_btn, self.help_btn]: layout.addWidget(w)
        self.drawing_tools = [self.pen_btn, self.eraser_btn, self.color_btn, self.guide_btn, self.width_slider, self.save_btn, self.clear_btn, self.color_indicator]
    def update_drawing_mode(self, is_active): self.toggle_draw_btn.setChecked(is_active); [w.setEnabled(is_active) for w in self.drawing_tools]
    def update_active_tool(self, tool_name): is_pen = tool_name == 'pen'; self.pen_btn.setChecked(is_pen); self.eraser_btn.setChecked(not is_pen)
    def update_pen_color(self, color): self.color_indicator.setStyleSheet(f"background-color: {color.name()};")
    def update_pen_width(self, width): self.width_slider.setValue(width); self.width_label.setText(str(width))
    def update_guide_mode(self, is_active): self.guide_btn.setChecked(is_active)
    def closeEvent(self, event: QCloseEvent): event.ignore(); self.hide(); self.closed_by_user.emit()

# =========================================================================================
# SECCIÓN 2: CONTROLADOR PRINCIPAL Y BANDEJA DE SISTEMA (CON LA MODIFICACIÓN)
# =========================================================================================
class SystemTrayApp:
    def __init__(self, app):
        self.app = app;self.overlay = DrawingOverlay();self.overlay.show();self.help_window = None;self.toolbar = ToolbarWindow()
        self.tray_icon = QSystemTrayIcon(self.create_icon("✏️")); self.tray_icon.setToolTip("DeskPainter");self.menu = QMenu(); self.create_menu_actions();self.tray_icon.setContextMenu(self.menu); self.tray_icon.show()
        self.connect_signals()
        self.toolbar.update_pen_width(self.overlay.pen_width);self.toolbar.update_pen_color(self.overlay.pen_color);self.toolbar.update_drawing_mode(False);self.toolbar.update_active_tool('pen')
        
        ### <<-- MODIFICACIÓN: MOSTRAR TOOLBAR AL INICIO -->> ###
        # Esta línea activa la opción en el menú, lo que a su vez
        # llama a la función toggle_toolbar_window para mostrar la ventana.
        self.show_toolbar_action.setChecked(True)

    def connect_signals(self):
        self.overlay.escape_pressed.connect(self.handle_escape_key);self.overlay.hotkey_pressed.connect(self.handle_hotkey)
        self.toolbar.drawing_toggled.connect(self.toggle_draw_action.setChecked);self.toolbar.tool_selected.connect(self.select_tool);self.toolbar.color_picker_requested.connect(self.open_color_picker);self.toolbar.guide_toggled.connect(self.guide_action.setChecked);self.toolbar.width_changed.connect(self.width_slider.setValue);self.toolbar.save_requested.connect(self.overlay.save_drawing);self.toolbar.clear_requested.connect(self.overlay.clear_canvas);self.toolbar.help_requested.connect(self.show_help_action.toggle);self.toolbar.closed_by_user.connect(lambda: self.show_toolbar_action.setChecked(False))
    
    def create_icon(self, text_or_color):
        pixmap = QPixmap(32, 32); pixmap.fill(Qt.GlobalColor.transparent);painter = QPainter(pixmap)
        if isinstance(text_or_color, str): painter.setFont(QtGui.QFont("Segoe UI Emoji", 16)); painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text_or_color)
        elif isinstance(text_or_color, QColor): painter.setBrush(text_or_color); painter.setPen(Qt.GlobalColor.darkGray); painter.drawEllipse(4, 4, 24, 24)
        painter.end();return QIcon(pixmap)
    
    def create_menu_actions(self):
        self.toggle_draw_action = QAction("✏️ Activar Dibujo", checkable=True); self.toggle_draw_action.toggled.connect(self.toggle_drawing_mode);self.menu.addAction(self.toggle_draw_action)
        self.show_toolbar_action = QAction("🛠️ Mostrar Barra de Herramientas", checkable=True); self.show_toolbar_action.toggled.connect(self.toggle_toolbar_window);self.menu.addAction(self.show_toolbar_action);self.menu.addSeparator()
        tool_group = QActionGroup(self.menu); tool_group.setExclusive(True)
        self.pen_action = QAction("Lápiz", checkable=True, checked=True); self.pen_action.triggered.connect(lambda: self.select_tool('pen'))
        self.eraser_action = QAction("Borrador", checkable=True); self.eraser_action.triggered.connect(lambda: self.select_tool('eraser'))
        tool_group.addAction(self.pen_action); tool_group.addAction(self.eraser_action);self.menu.addAction(self.pen_action); self.menu.addAction(self.eraser_action)
        self.color_menu = QMenu("🎨 Paleta de Colores", self.menu)
        for name, hex_color in PRESET_COLORS.items(): action = QAction(name, icon=self.create_icon(QColor(hex_color))); action.triggered.connect(lambda c, h=hex_color: self.set_pen_color(QColor(h)));self.color_menu.addAction(action)
        self.color_menu.addSeparator(); picker_action = QAction("Seleccionar Otro Color..."); picker_action.triggered.connect(self.open_color_picker); self.color_menu.addAction(picker_action);self.menu.addMenu(self.color_menu)
        self.width_slider_action = QWidgetAction(self.menu); slider_widget = QWidget(); slider_layout = QHBoxLayout(slider_widget); slider_layout.setContentsMargins(10, 0, 10, 0)
        self.width_slider = QSlider(Qt.Orientation.Horizontal, minimum=1, maximum=50, value=self.overlay.pen_width); self.width_slider.valueChanged.connect(self.change_width)
        self.width_label = QLabel(str(self.overlay.pen_width)); self.width_label.setMinimumWidth(20);slider_layout.addWidget(QLabel("Grosor:")); slider_layout.addWidget(self.width_slider); slider_layout.addWidget(self.width_label);self.width_slider_action.setDefaultWidget(slider_widget); self.menu.addAction(self.width_slider_action)
        self.guide_action = QAction("👻 Modo Fantasma", checkable=True); self.guide_action.toggled.connect(self.toggle_guide_mode);self.menu.addAction(self.guide_action); self.menu.addSeparator()
        save_action = QAction("💾 Guardar"); save_action.triggered.connect(self.overlay.save_drawing);clear_action = QAction("🗑️ Limpiar"); clear_action.triggered.connect(self.overlay.clear_canvas);self.menu.addAction(save_action); self.menu.addAction(clear_action); self.menu.addSeparator()
        self.show_help_action = QAction("❓ Mostrar Ayuda", checkable=True); self.show_help_action.toggled.connect(self.toggle_help_window);quit_action = QAction("❌ Salir"); quit_action.triggered.connect(self.app.quit);self.menu.addAction(self.show_help_action); self.menu.addAction(quit_action)
        self.update_tool_enabled_state(False)

    def update_tool_enabled_state(self, enabled): [a.setEnabled(enabled) for a in [self.pen_action, self.eraser_action, self.color_menu, self.width_slider_action, self.guide_action]]
    def toggle_drawing_mode(self, checked): self.overlay.set_drawing_mode(checked); self.update_tool_enabled_state(checked);self.toolbar.update_drawing_mode(checked); (self.guide_action.setChecked(False) if not checked and self.guide_action.isChecked() else None)
    def select_tool(self, tool): self.overlay.set_tool(tool); (self.pen_action if tool == 'pen' else self.eraser_action).setChecked(True);self.toolbar.update_active_tool(tool); (self.toggle_draw_action.setChecked(True) if not self.toggle_draw_action.isChecked() else None)
    def set_pen_color(self, color): self.overlay.set_pen_color(color); self.select_tool('pen');self.color_menu.setIcon(self.create_icon(color));self.toolbar.update_pen_color(color)
    def open_color_picker(self): color = QColorDialog.getColor(self.overlay.pen_color, self.overlay, "Elige un color"); self.set_pen_color(color) if color.isValid() else None
    def change_width(self, value): self.overlay.set_pen_width(value);self.width_label.setText(str(value));self.toolbar.update_pen_width(value)
    def toggle_guide_mode(self, checked): self.overlay.toggle_guide_background(checked);self.toolbar.update_guide_mode(checked)
    def handle_escape_key(self): self.guide_action.setChecked(False) if self.guide_action.isChecked() else (self.toggle_draw_action.setChecked(False) if self.toggle_draw_action.isChecked() else None)
    def handle_hotkey(self, key): actions = {"pen": lambda: self.select_tool('pen'), "eraser": lambda: self.select_tool('eraser'),"guide": self.guide_action.toggle, "width_up": lambda: self.width_slider.setValue(self.width_slider.value() + 1),"width_down": lambda: self.width_slider.setValue(self.width_slider.value() - 1),"color_picker": self.open_color_picker, "save": self.overlay.save_drawing, "clear": self.overlay.clear_canvas}; actions[key]() if key in actions else None
    def toggle_toolbar_window(self, checked): self.toolbar.setVisible(checked); self.toolbar.activateWindow() if checked else None
    def toggle_help_window(self, checked):
        if checked and not self.help_window: self.help_window = HelpWindow(); self.help_window.show()
        elif not checked and self.help_window: self.help_window.close(); self.help_window = None

# =========================================================================================
# SECCIÓN 3: PUNTO DE ENTRADA
# =========================================================================================
def main():
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    try:
        tray_app = SystemTrayApp(app); sys.exit(app.exec())
    except Exception as e: print(f"Error al iniciar la aplicación: {e}"); sys.exit(1)

if __name__ == "__main__":
    main()