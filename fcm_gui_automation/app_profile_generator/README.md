# App Profile Generator

Windows GUI applications can expose many controls with repeated names. This
tool captures the current UI Automation tree and creates profile drafts that a
human can review, group, and rename before scenario authoring.

## Source Tree

```text
fcm_gui_automation/app_profile_generator/
├─ main.py
├─ cli/
│  └─ main.py
├─ runtime/
│  ├─ app_launcher.py
│  ├─ window_resolver.py
│  └─ screenshot_capture.py
├─ inspection/
│  ├─ control_dumper.py
│  └─ hierarchical_profile.py
├─ output/
│  └─ profile_writer.py
└─ imaging/
   └─ annotated_screenshot.py
```

## Run

Use a file picker:

```bash
python -m fcm_gui_automation.app_profile_generator.main
```

Use an explicit path:

```bash
python -m fcm_gui_automation.app_profile_generator.main --app-path d:\app\fcm_desktop.py
```

Run the CLI module directly:

```bash
python -m fcm_gui_automation.app_profile_generator.cli.main --app-path d:\app\fcm_desktop.py
```

## Generated Files

```text
profiles/generated/<app_name>_<timestamp>/
├─ app.yaml
├─ elements.yaml
├─ controls_dump.yaml
├─ hierarchical_profile.yaml
├─ screenshot.png
├─ annotated_screenshot.png
└─ controls_map.yaml
```

## Hierarchical Profile

`hierarchical_profile.yaml` is the main draft for manual review. Groups form a
tree: a group becomes the direct child of the smallest larger group that
contains its center point. Controls are placed under the smallest group that
contains their center point. Scenario authors should use the reviewed group
name and target name, not raw UI Automation ids.
Regions in the generated profile use `window_ratio` coordinates. `x`, `y`,
`width`, and `height` are stored as fractions of the captured window, so runtime
lookup can survive window moves, resizes, resolution changes, and DPI changes.

Example target shape:

```yaml
screens:
  main_window:
    groups:
      central_widget:
        name: central_widget
        child_groups:
          operation_group:
            name: Operation Group
            controls:
              connect:
                name: Connect
                label_no: 45
                region_units: window_ratio
                region:
                  x: 0.284375
                  y: 0.7125
                  width: 0.078125
                  height: 0.05
                scenario_ref:
                  group: Operation Group
                  target: connect
```

The scenario reference includes exactly the two values a scenario author needs:
group and target. For example:

```yaml
- action: click
  group: Operation Group
  target: connect
```

The grouping rule is spatial, not string-based:

```text
operation_group rectangle contains connect center
-> operation_group.connect
```

Target names are suggested from visible names only. The generator does not add
control-type suffixes such as `_input`, `_button`, or `_label`; duplicate names
are disambiguated with numeric suffixes for manual review.

## MFCGridCtrl Cell Detection

When pywinauto exposes a control whose class name is `MFCGridCtrl`, the
generator crops that grid from the window screenshot and uses OpenCV line
detection to split it into cells. Each detected cell is appended to the raw
control list as a synthetic `Cell` controller with `element_type: grid_cell`,
row/column metadata, and a normal profile entry.

## Scenario Discovery

The generator can run one or more scenario files once and merge newly discovered
windows, tabs, or dynamic panels into `hierarchical_profile.yaml`.

```bash
python -m fcm_gui_automation.app_profile_generator.main \
  --app-path d:\app\fcm_desktop.py \
  --discovery-scenario d:\app\fcm_gui_automation\scenarios\qt_complex_test.yaml
```

During discovery, the tool executes mutating steps such as `click` and
`set_text`. After each step it inspects visible windows for the same process.
If the UI tree changed, a new screen is added under the step's trigger target.

To start from the main profile and then run every scenario in a directory once,
use:

```bash
python -m fcm_gui_automation.app_profile_generator.main \
  --app-path d:\app\fcm_desktop.py \
  --discover-all-scenarios \
  --discovery-scenario-dir d:\app\fcm_gui_automation\scenarios
```

In this mode the initial main window is treated as already profiled. The
generator watches for additional visible windows, such as dialogs, while each
scenario runs and appends those controllers as new screens. A
`discovery_summary.yaml` file is written with per-scenario success, failure, and
new-screen counts.

For dialogs that should be profiled without completing the full runtime flow,
write an explicit `capture_profile` discovery step. The action clicks the target,
detects the newly opened dialog/window, appends its controllers to all profile
outputs, closes the dialog with `Esc`, and returns focus to the main window.

```yaml
name: capture_dialog_profiles
steps:
  - action: capture_profile
    group: Operation Group
    target: open_socon_button

  - action: capture_profile
    group: Operation Group
    target: open_dialog_button
```

If one click opens multiple windows, add an optional `window.title` hint to make
the capture unambiguous.

Example discovered screen metadata:

```yaml
discovered_by:
  type: capture_profile_action
  scenario_name: capture_dialog_profiles
  scenario_path: d:\app\fcm_gui_automation\scenarios\profile_capture_dialogs.yaml
  step_index: 1
  action: capture_profile
  trigger_target: open_dialog_button
  parent_screen: main_window
```

Reviewed names are not overwritten by this merge path; new screens are appended
for manual review.

## Manual Review Flow

1. Open `annotated_screenshot.png` and locate the control label number.
2. Open `hierarchical_profile.yaml` and review the suggested group/control names.
3. Keep scenarios in explicit `group` + `target` form.
4. Open `controls_map.yaml` only when you need raw debug details.
5. Use `--discovery-scenario` to append screens that only appear after user
   actions such as opening a dialog or switching tabs.
6. Use `--discover-all-scenarios` when you want to run the full scenario folder
   once and collect controllers from newly opened windows.
7. Use `capture_profile` steps when a main-window button should open a dialog
   only long enough to profile that dialog and then close it.

## Runtime Lookup

The automation runner does not use raw UI Automation ids as scenario locators.
It first tries to find a control by visible group name and visible target name.
If that is not enough, it reads `hierarchical_profile.yaml`, resolves the
scenario's `group` + `target` pair to a reviewed region, and picks the current
UIA control inside that region.
