import sys

from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ControlPanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQt Input Panel")
        self.resize(700, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")

        root_layout = QVBoxLayout()
        root_layout.setSpacing(16)
        root_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Input Panel")
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        description_label = QLabel(
            "This sample app contains multiple buttons, descriptions, and key/value fields."
        )
        description_label.setObjectName("description_label")
        description_label.setWordWrap(True)

        # v1.1.0: sample status indicator for target-based color verification.
        self.status_lamp = QLabel("Status Lamp: READY")
        self.status_lamp.setObjectName("status_lamp")
        self.status_lamp.setFixedHeight(42)
        self.status_lamp.setStyleSheet(
            "background-color: #1f6feb; color: white; font-weight: bold; "
            "border-radius: 8px; padding-left: 12px;"
        )

        input_group = QGroupBox("Input Area")
        input_group.setObjectName("input_group")
        input_layout = QGridLayout()

        key_label = QLabel("Key")
        self.key_input = QLineEdit()
        self.key_input.setObjectName("key_input")
        self.key_input.setPlaceholderText("Enter key")

        value_label = QLabel("Value")
        self.value_input = QLineEdit()
        self.value_input.setObjectName("value_input")
        self.value_input.setPlaceholderText("Enter value")

        extra_value_label = QLabel("Value 2")
        self.extra_value_input = QLineEdit()
        self.extra_value_input.setObjectName("value2_input")
        self.extra_value_input.setPlaceholderText("Enter extra value")

        input_layout.addWidget(key_label, 0, 0)
        input_layout.addWidget(self.key_input, 0, 1)
        input_layout.addWidget(value_label, 1, 0)
        input_layout.addWidget(self.value_input, 1, 1)
        input_layout.addWidget(extra_value_label, 2, 0)
        input_layout.addWidget(self.extra_value_input, 2, 1)
        input_group.setLayout(input_layout)

        button_group = QGroupBox("Actions")
        button_group.setObjectName("button_group")
        button_layout = QGridLayout()

        self.button_info = {
            "save_button": "Save: reflects the current key/value values in the status area.",
            "load_button": "Load: example action that checks values using the current key.",
            "reset_button": "Reset: clears every input field.",
            "apply_button": "Apply: marks the current values as applied.",
        }

        save_button = QPushButton("Save")
        save_button.setObjectName("save_button")
        load_button = QPushButton("Load")
        load_button.setObjectName("load_button")
        reset_button = QPushButton("Reset")
        reset_button.setObjectName("reset_button")
        apply_button = QPushButton("Apply")
        apply_button.setObjectName("apply_button")

        save_button.clicked.connect(lambda: self.handle_action("save_button"))
        load_button.clicked.connect(lambda: self.handle_action("load_button"))
        reset_button.clicked.connect(lambda: self.handle_action("reset_button"))
        apply_button.clicked.connect(lambda: self.handle_action("apply_button"))

        button_layout.addWidget(save_button, 0, 0)
        button_layout.addWidget(QLabel(self.button_info["save_button"]), 0, 1)
        button_layout.addWidget(load_button, 1, 0)
        button_layout.addWidget(QLabel(self.button_info["load_button"]), 1, 1)
        button_layout.addWidget(reset_button, 2, 0)
        button_layout.addWidget(QLabel(self.button_info["reset_button"]), 2, 1)
        button_layout.addWidget(apply_button, 3, 0)
        button_layout.addWidget(QLabel(self.button_info["apply_button"]), 3, 1)
        button_group.setLayout(button_layout)

        status_title = QLabel("Status")
        status_title.setObjectName("status_title")
        status_title.setStyleSheet("font-weight: bold;")

        self.status_box = QTextEdit()
        self.status_box.setObjectName("status_box")
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Action results appear here.")

        root_layout.addWidget(title_label)
        root_layout.addWidget(description_label)
        root_layout.addWidget(self.status_lamp)
        root_layout.addWidget(input_group)
        root_layout.addWidget(button_group)
        root_layout.addWidget(status_title)
        root_layout.addWidget(self.status_box)

        central_widget.setLayout(root_layout)
        self.setCentralWidget(central_widget)

    def handle_action(self, action_name: str) -> None:
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        extra_value = self.extra_value_input.text().strip()

        if action_name == "reset_button":
            self.key_input.clear()
            self.value_input.clear()
            self.extra_value_input.clear()
            self.status_box.setPlainText("Inputs cleared.")
            return

        action_text = self.button_info[action_name]
        lines = [
            f"Selected action: {action_text}",
            f"Key: {key or '(empty)'}",
            f"Value: {value or '(empty)'}",
            f"Value 2: {extra_value or '(empty)'}",
        ]
        self.status_box.setPlainText("\n".join(lines))


def main() -> None:
    app = QApplication(sys.argv)
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
