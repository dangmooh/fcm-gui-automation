# PyQt Input Panel

PyQt6 sample desktop app with:

- multiple buttons
- button description text
- key input
- value input
- extra value input
- status area

## Run

```powershell
pip install -r requirements.txt
python fcm_desktop.py
```

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
