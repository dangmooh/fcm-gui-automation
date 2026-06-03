import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


LAMP_COLORS = {
    "gray": "#6b7280",
    "green": "#16a34a",
    "blue": "#2563eb",
    "red": "#dc2626",
}


class StatusLamp(QFrame):
    def __init__(self, object_name: str, label: str) -> None:
        super().__init__()
        self.label = label
        self.color_name = "gray"
        self.setObjectName(object_name)
        self.setFixedSize(96, 34)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.set_color("gray")

    def set_color(self, color_name: str) -> None:
        self.color_name = color_name
        color = LAMP_COLORS[color_name]
        self.setStyleSheet(
            f"QFrame#{self.objectName()} {{"
            f"background-color: {color}; border-radius: 5px; border: 1px solid #111827;"
            "}}"
        )
        self.setAccessibleName(f"{self.label} {color_name}")


class CustomPaintedGrid(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("custom_grid")
        self.setMinimumHeight(140)
        self.headers = ["Item", "Value", "Result"]
        self.reset_rows()

    def reset_rows(self) -> None:
        self.rows = [
            ["Voltage", "12.3", "READY"],
            ["Current", "0.5", "READY"],
            ["Frequency", "1000", "READY"],
        ]
        self.update()

    def set_result(self, result: str) -> None:
        for row in self.rows:
            row[2] = result
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111827"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rows = [self.headers] + self.rows
        row_count = len(rows)
        col_count = len(self.headers)
        row_h = max(1, self.height() // row_count)
        col_w = max(1, self.width() // col_count)

        grid_pen = QPen(QColor("#94a3b8"))
        text_pen = QPen(QColor("#f8fafc"))
        header_pen = QPen(QColor("#38bdf8"))

        painter.setPen(grid_pen)
        for row in range(row_count + 1):
            y = row * row_h
            painter.drawLine(0, y, self.width(), y)
        for col in range(col_count + 1):
            x = col * col_w
            painter.drawLine(x, 0, x, self.height())

        for row_index, row in enumerate(rows):
            painter.setPen(header_pen if row_index == 0 else text_pen)
            for col_index, value in enumerate(row):
                cell_x = col_index * col_w + 10
                cell_y = row_index * row_h
                painter.drawText(
                    cell_x,
                    cell_y,
                    col_w - 20,
                    row_h,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    value,
                )


class SettingDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setting Dialog")
        self.setObjectName("setting_dialog")
        self.resize(360, 160)

        layout = QGridLayout()
        layout.addWidget(QLabel("Setting Value"), 0, 0)

        self.setting_value_input = QLineEdit()
        self.setting_value_input.setObjectName("setting_value_input")
        self.setting_value_input.setPlaceholderText("Enter setting value")
        layout.addWidget(self.setting_value_input, 0, 1, 1, 2)

        self.enable_option_checkbox = QCheckBox("Enable Option")
        self.enable_option_checkbox.setObjectName("enable_option_checkbox")
        layout.addWidget(self.enable_option_checkbox, 1, 0, 1, 3)

        ok_button = QPushButton("OK")
        ok_button.setObjectName("dialog_ok_button")
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("dialog_cancel_button")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(ok_button, 2, 1)
        layout.addWidget(cancel_button, 2, 2)

        self.setLayout(layout)


class SoconNumberDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Socon Number")
        self.setObjectName("socon_number_dialog")
        self.resize(360, 140)

        layout = QGridLayout()
        layout.addWidget(QLabel("Socon Number"), 0, 0)

        self.number_input = QLineEdit()
        self.number_input.setObjectName("socon_number_input")
        self.number_input.setPlaceholderText("Enter number")
        layout.addWidget(self.number_input, 0, 1, 1, 2)

        ok_button = QPushButton("OK")
        ok_button.setObjectName("socon_number_ok_button")
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("socon_number_cancel_button")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(ok_button, 1, 1)
        layout.addWidget(cancel_button, 1, 2)

        self.setLayout(layout)

    def number(self) -> str:
        return self.number_input.text().strip()


class ControlPanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQt Input Panel")
        self.resize(960, 840)
        self.dialogs: list[QDialog] = []
        self.socon_number = ""
        self.socon_file_path = ""
        self._build_ui()
        self.reset_state()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")

        root_layout = QVBoxLayout()
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel("Input Panel")
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        description_label = QLabel(
            "Dummy control panel for testing pywinauto, OCR, color detection, "
            "layout hierarchy, dialogs, dynamic lists, and custom-painted widgets."
        )
        description_label.setObjectName("description_label")
        description_label.setWordWrap(True)

        root_layout.addWidget(title_label)
        root_layout.addWidget(description_label)
        root_layout.addWidget(self._build_connection_group())
        root_layout.addWidget(self._build_parameter_group())
        root_layout.addWidget(self._build_operation_group())
        root_layout.addWidget(self._build_result_group())
        root_layout.addWidget(self._build_custom_grid_group())

        central_widget.setLayout(root_layout)
        self.setCentralWidget(central_widget)

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("Connection Group")
        group.setObjectName("connection_group")
        layout = QGridLayout()

        self.connection_lamp = StatusLamp("connection_lamp", "Connection")
        self.running_lamp = StatusLamp("running_lamp", "Running")
        self.error_lamp = StatusLamp("error_lamp", "Error")
        self.result_lamp = StatusLamp("result_lamp", "Result")

        lamps = [
            ("Connection", self.connection_lamp),
            ("Running", self.running_lamp),
            ("Error", self.error_lamp),
            ("Result", self.result_lamp),
        ]
        for col, (label, lamp) in enumerate(lamps):
            layout.addWidget(QLabel(label), 0, col)
            layout.addWidget(lamp, 1, col)

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("status_label")
        self.status_label.setStyleSheet("font-weight: bold;")
        self.result_label = QLabel("No result")
        self.result_label.setObjectName("result_label")
        self.result_label.setStyleSheet("font-weight: bold;")

        layout.addWidget(QLabel("Status"), 2, 0)
        layout.addWidget(self.status_label, 2, 1)
        layout.addWidget(QLabel("Result"), 2, 2)
        layout.addWidget(self.result_label, 2, 3)

        group.setLayout(layout)
        return group

    def _build_parameter_group(self) -> QGroupBox:
        group = QGroupBox("Parameter Group")
        group.setObjectName("parameter_group")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)

        self.key_input = QLineEdit()
        self.key_input.setObjectName("key_input")
        self.key_input.setPlaceholderText("Enter key")

        self.value_input = QLineEdit()
        self.value_input.setObjectName("value_input")
        self.value_input.setPlaceholderText("Enter value")

        self.extra_value_input = QLineEdit()
        self.extra_value_input.setObjectName("value2_input")
        self.extra_value_input.setPlaceholderText("Enter extra value")

        self.frequency_input = QLineEdit()
        self.frequency_input.setObjectName("frequency_input")
        self.frequency_input.setPlaceholderText("1000")

        self.power_input = QLineEdit()
        self.power_input.setObjectName("power_input")
        self.power_input.setPlaceholderText("-10")

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("mode_combo")
        self.mode_combo.addItems(["AUTO", "MANUAL", "SERVICE"])

        rows = [
            ("Key", self.key_input, "", None),
            ("Value", self.value_input, "", None),
            ("Value 2", self.extra_value_input, "", None),
            ("Frequency", self.frequency_input, "MHz", self.apply_frequency),
            ("Power", self.power_input, "dBm", self.apply_power),
            ("Mode", self.mode_combo, "", self.apply_mode),
        ]

        for row, (label_text, editor, unit, handler) in enumerate(rows):
            layout.addWidget(QLabel(label_text), row, 0)
            layout.addWidget(editor, row, 1)
            layout.addWidget(QLabel(unit), row, 2)
            if handler is not None:
                button = QPushButton("Apply")
                if label_text == "Frequency":
                    button.setObjectName("frequency_apply_button")
                elif label_text == "Power":
                    button.setObjectName("power_apply_button")
                else:
                    button.setObjectName("")
                button.clicked.connect(handler)
                layout.addWidget(button, row, 3)

        group.setLayout(layout)
        return group

    def _build_operation_group(self) -> QGroupBox:
        group = QGroupBox("Operation Group")
        group.setObjectName("operation_group")
        layout = QGridLayout()

        buttons = [
            ("Connect", "connect_button", self.connect_device),
            ("Disconnect", "disconnect_button", self.disconnect_device),
            ("Start", "start_button", self.start_operation),
            ("Stop", "stop_button", self.stop_operation),
            ("Save", "save_button", lambda: self.handle_action("save_button")),
            ("Load", "load_button", lambda: self.handle_action("load_button")),
            ("Reset", "reset_button", self.reset_state),
            ("Apply", "apply_button", lambda: self.handle_action("apply_button")),
            ("Open Dialog", "open_dialog_button", self.open_setting_dialog),
            ("Open Socon", "open_socon_button", self.open_socon_flow),
            ("Load List", "load_list_button", self.load_list),
            ("Clear List", "clear_list_button", self.clear_list),
            ("Run Test", "run_test_button", self.run_test),
        ]

        for index, (text, object_name, handler) in enumerate(buttons):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.clicked.connect(handler)
            layout.addWidget(button, index // 4, index % 4)

        group.setLayout(layout)
        return group

    def _build_result_group(self) -> QGroupBox:
        group = QGroupBox("Result Group")
        group.setObjectName("result_group")
        layout = QGridLayout()

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("result_list")

        self.status_box = QTextEdit()
        self.status_box.setObjectName("status_box")
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Action results appear here.")

        layout.addWidget(QLabel("Dynamic List"), 0, 0)
        layout.addWidget(QLabel("Status Log"), 0, 1)
        layout.addWidget(self.list_widget, 1, 0)
        layout.addWidget(self.status_box, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        group.setLayout(layout)
        return group

    def _build_custom_grid_group(self) -> QGroupBox:
        group = QGroupBox("Custom Grid Group")
        group.setObjectName("custom_grid_group")
        layout = QVBoxLayout()
        self.custom_grid = CustomPaintedGrid()
        layout.addWidget(self.custom_grid)
        group.setLayout(layout)
        return group

    def _set_log(self, lines: list[str]) -> None:
        self.status_box.setPlainText("\n".join(lines))

    def connect_device(self) -> None:
        self.connection_lamp.set_color("green")
        self.error_lamp.set_color("gray")
        self.status_label.setText("CONNECTED")
        self._set_log(["Connected to dummy target.", "Connection lamp is green."])

    def disconnect_device(self) -> None:
        self.connection_lamp.set_color("gray")
        self.running_lamp.set_color("gray")
        self.status_label.setText("DISCONNECTED")
        self._set_log(["Disconnected from dummy target."])

    def start_operation(self) -> None:
        self.running_lamp.set_color("blue")
        self.status_label.setText("RUNNING")
        self._set_log(["Operation started.", "Running lamp is blue."])

    def stop_operation(self) -> None:
        self.running_lamp.set_color("gray")
        self.status_label.setText("STOPPED")
        self._set_log(["Operation stopped.", "Running lamp is gray."])

    def apply_frequency(self) -> None:
        value = self.frequency_input.text().strip() or "(empty)"
        self._set_log([f"Frequency applied: {value} MHz"])

    def apply_power(self) -> None:
        value = self.power_input.text().strip() or "(empty)"
        self._set_log([f"Power applied: {value} dBm"])

    def apply_mode(self) -> None:
        self._set_log([f"Mode applied: {self.mode_combo.currentText()}"])

    def open_setting_dialog(self) -> None:
        dialog = SettingDialog(self)
        dialog.setModal(False)
        dialog.show()
        self.dialogs.append(dialog)
        self.status_label.setText("DIALOG OPENED")
        self._set_log(["Setting Dialog opened."])

    def open_socon_flow(self) -> None:
        dialog = SoconNumberDialog(self)
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.open_socon_file_dialog(dialog))
        dialog.rejected.connect(lambda: self._set_log(["Socon flow cancelled."]))
        dialog.show()
        self.dialogs.append(dialog)
        self.status_label.setText("SOCON NUMBER")
        self._set_log(["Socon number dialog opened."])

    def open_socon_file_dialog(self, dialog: SoconNumberDialog) -> None:
        self.socon_number = dialog.number()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Socon File",
            "",
            "Data files (*.csv *.txt *.yaml *.yml);;All files (*.*)",
        )
        if selected:
            self.socon_file_path = selected
            self.status_label.setText("SOCON FILE SELECTED")
            self._set_log(
                [
                    "Socon file selected.",
                    f"Socon Number: {self.socon_number or '(empty)'}",
                    f"File: {self.socon_file_path}",
                ]
            )
        else:
            self.status_label.setText("SOCON FILE CANCELLED")
            self._set_log(
                [
                    "Socon file selection cancelled.",
                    f"Socon Number: {self.socon_number or '(empty)'}",
                ]
            )

    def load_list(self) -> None:
        self.list_widget.clear()
        for item in ["Voltage check", "Current check", "Frequency check", "Power check"]:
            self.list_widget.addItem(item)
        self._set_log(["Loaded dynamic list items."])

    def clear_list(self) -> None:
        self.list_widget.clear()
        self._set_log(["Cleared dynamic list items."])

    def run_test(self) -> None:
        has_connection = self.connection_lamp.color_name == "green"
        has_frequency = bool(self.frequency_input.text().strip())
        has_power = bool(self.power_input.text().strip())
        passed = has_connection and has_frequency and has_power

        if passed:
            self.result_lamp.set_color("green")
            self.error_lamp.set_color("gray")
            self.result_label.setText("PASS")
            self.custom_grid.set_result("PASS")
        else:
            self.result_lamp.set_color("red")
            self.error_lamp.set_color("red")
            self.result_label.setText("FAIL")
            self.custom_grid.set_result("FAIL")

        self._set_log(
            [
                f"Run Test result: {self.result_label.text()}",
                f"Frequency: {self.frequency_input.text().strip() or '(empty)'} MHz",
                f"Power: {self.power_input.text().strip() or '(empty)'} dBm",
                f"Mode: {self.mode_combo.currentText()}",
            ]
        )

    def reset_state(self) -> None:
        self.key_input.clear()
        self.value_input.clear()
        self.extra_value_input.clear()
        self.frequency_input.clear()
        self.power_input.clear()
        self.mode_combo.setCurrentIndex(0)
        self.socon_number = ""
        self.socon_file_path = ""
        self.list_widget.clear()
        self.connection_lamp.set_color("gray")
        self.running_lamp.set_color("gray")
        self.error_lamp.set_color("gray")
        self.result_lamp.set_color("gray")
        self.status_label.setText("READY")
        self.result_label.setText("No result")
        self.custom_grid.reset_rows()
        self._set_log(["Inputs cleared.", "All lamps reset to gray."])

    def handle_action(self, action_name: str) -> None:
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        extra_value = self.extra_value_input.text().strip()
        frequency = self.frequency_input.text().strip()
        power = self.power_input.text().strip()

        action_text = {
            "save_button": "Save: reflects the current key/value values in the status area.",
            "load_button": "Load: example action that checks values using the current key.",
            "apply_button": "Apply: marks the current values as applied.",
        }.get(action_name, action_name)

        self._set_log(
            [
                f"Selected action: {action_text}",
                f"Key: {key or '(empty)'}",
                f"Value: {value or '(empty)'}",
                f"Value 2: {extra_value or '(empty)'}",
                f"Frequency: {frequency or '(empty)'}",
                f"Power: {power or '(empty)'}",
                f"Mode: {self.mode_combo.currentText()}",
            ]
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
