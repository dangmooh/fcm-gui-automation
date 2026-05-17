# PyQt Input Panel

PyQt6 dummy desktop app for Windows GUI automation framework testing.

This app stands in for a real target program when the real device/control
software is not available. It is intentionally built with a mixture of normal
Qt controls, repeated button names, dynamic visual states, a popup dialog, a
list area, and a custom-painted grid so these tools can be tested together:

- profile generator
- pywinauto target lookup
- OCR name resolver
- color adapter
- scenario recorder
- layout hierarchy resolver
- scenario runner

## Run

```powershell
pip install -r requirements.txt
python fcm_desktop.py
```

## Test Surface

The app contains these groups:

- `Connection Group`: connection, running, error, and result lamps plus status/result text.
- `Parameter Group`: Key, Value, Value2, Frequency, Power, and Mode rows.
- `Operation Group`: Connect, Disconnect, Start, Stop, Save, Load, Reset, Apply, Open Dialog, Load List, Clear List, and Run Test.
- `Result Group`: a dynamic `QListWidget` and status log.
- `Custom Grid Group`: a `CustomPaintedGrid` widget that paints grid lines and text manually.

The repeated `Apply` buttons are deliberate. Frequency and Power have stable
object names for direct automation, while the Mode row keeps a blank
`objectName` so OCR/layout-based name resolution has an ambiguous case to solve.

## Button Behavior

- `Connect`: sets `connection_lamp` green and `status_label` to `CONNECTED`.
- `Disconnect`: resets connection/running lamps and sets `status_label` to `DISCONNECTED`.
- `Start`: sets `running_lamp` blue and `status_label` to `RUNNING`.
- `Stop`: sets `running_lamp` gray and `status_label` to `STOPPED`.
- `Run Test`: sets `result_label` to `PASS` when connected with Frequency and Power values, otherwise `FAIL`; it also updates `result_lamp` and the custom grid result column.
- `Reset`: clears inputs/list state, resets all lamps gray, and restores `status_label` to `READY`.
- `Open Dialog`: opens a non-modal `Setting Dialog` with OK, Cancel, Setting Value, and Enable Option controls.
- `Load List` / `Clear List`: add and remove dynamic list items.

## Complex Scenario

`fcm_gui_automation/scenarios/qt_complex_test.yaml` exercises the main dummy
workflow:

- connect and verify green lamp
- enter Frequency and Power
- start and verify blue running lamp
- run test and verify PASS/green result
- open dialog and capture a screenshot
- reset and close

## verify_color Scenario Action

`verify_color` checks whether a named scenario target currently contains enough
pixels similar to the expected color. In v1.1.0, `red`, `green`, and `blue` are
supported. The target region is defined in the scenario `elements` section.

```yaml
name: "color_test"
elements:
  status_lamp:
    type: "indicator"
    region:
      x: 20
      y: 105
      width: 660
      height: 70
steps:
  - action: "launch_or_connect"
  - action: "verify_color"
    name: "status lamp blue check"
    target: "status_lamp"
    expected_color: "blue"
    min_ratio: 0.3
```

`detected_ratio` is calculated from the cropped target region using HSV hue
ranges. Low-saturation or low-value pixels are ignored before the ratio is
calculated.
