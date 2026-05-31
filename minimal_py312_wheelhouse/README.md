# Minimal Python 3.12 Wheelhouse

This folder contains only the Python wheels required for the core GUI
automation workflow on Windows 64-bit with Python 3.12:

- PyQt6 dummy desktop app
- pywinauto-based GUI automation
- YAML scenario loading
- Pillow image/screenshot handling
- pytesseract Python wrapper

Install offline:

```powershell
python -m pip install --no-index --find-links .\wheels -r .\requirements_minimal_py312.txt
```

OCR still requires the Tesseract executable and tessdata files separately.
These wheels do not include `tesseract.exe`.

YOLO is not included in this minimal wheelhouse. For YOLO, use the full
`offline_bundle_py312_win64` wheelhouse instead.
