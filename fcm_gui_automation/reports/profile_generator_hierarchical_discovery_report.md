# Profile Generator Hierarchical Discovery Report

작성일: 2026-05-16
대상 프로젝트: D:\app
대상 기능: app_profile_generator의 계층형 grouping 및 scenario discovery 확장

## 1. 보고서 목적

이 보고서는 새로 수정한 profile generator 기능을 파일 구성부터 내부 코드 동작까지 단계적으로 설명한다.

이번 변경의 핵심 목표는 두 가지다.

- 컨트롤을 단순한 평면 목록으로 저장하지 않고, 화면 영역 기준으로 group 안에 배치한다.
- 시나리오를 한 번 실행하면서 새 창, 탭, 동적 패널이 나타나면 해당 화면을 기존 profile에 누적한다.

기존 방식은 UIA 컨트롤 목록을 그대로 추출하고, `automation_id`를 참고하여 사람이 이름을 고치는 구조였다. 이번 변경 이후에는 사람이 이름을 정하는 원칙은 유지하되, generator가 먼저 의미 있는 계층 구조를 제안한다.

## 2. 전체 파일 구성

현재 app_profile_generator의 주요 구성은 다음과 같다.

```text
app_profile_generator/
├─ main.py
├─ cli/
│  └─ main.py
├─ runtime/
│  ├─ app_launcher.py
│  ├─ window_resolver.py
│  └─ screenshot_capture.py
├─ inspection/
│  ├─ control_dumper.py
│  ├─ hierarchical_profile.py
│  └─ scenario_discovery.py
├─ output/
│  └─ profile_writer.py
└─ imaging/
   └─ annotated_screenshot.py
```

각 파일의 역할은 다음과 같다.

| 파일 | 역할 |
| --- | --- |
| `main.py` | 기존 실행 명령을 유지하기 위한 wrapper |
| `cli/main.py` | CLI 옵션 처리, 앱 실행, profile 생성 흐름 총괄 |
| `runtime/app_launcher.py` | `.py` 또는 `.exe` 대상 앱 실행 |
| `runtime/window_resolver.py` | 실행된 앱의 메인 창 찾기 |
| `runtime/screenshot_capture.py` | 원본 창 스크린샷 저장 |
| `inspection/control_dumper.py` | pywinauto UIA descendants를 dict 목록으로 dump |
| `inspection/hierarchical_profile.py` | 영역 포함 기준으로 group/control 계층 profile 생성 |
| `inspection/scenario_discovery.py` | 시나리오를 실행하며 새 화면을 발견하고 profile에 merge |
| `output/profile_writer.py` | YAML 산출물 저장 |
| `imaging/annotated_screenshot.py` | 컨트롤 박스와 label 번호가 표시된 screenshot 생성 |

## 3. 기존 생성 흐름

기본 profile 생성 흐름은 다음과 같다.

```text
사용자가 app path 선택
-> 대상 앱 실행
-> 메인 window resolve
-> UIA descendants dump
-> app.yaml, elements.yaml, controls_dump.yaml 생성
-> hierarchical_profile.yaml 생성
-> screenshot.png 생성
-> annotated_screenshot.png, controls_map.yaml 생성
```

CLI 진입점은 `app_profile_generator/cli/main.py`이다.

핵심 흐름은 다음 코드에서 확인할 수 있다.

```python
print("[4] Dumping UIA controls...")
controls = dump_controls(window)
elements = build_elements_from_controls(controls)

window_info = dump_window_info(window)

app_info = {
    "name": app_name,
    "app_path": str(app_path_obj),
    "launch_type": launched_app.launch_type,
    "process_id": launched_app.pid,
    "window_title": window_info["window_title"],
    "backend": "uia",
    "window_rect": window_info["window_rect"],
    "default_timeout": 10,
}
hierarchical_profile = build_hierarchical_profile(
    app_info=app_info,
    controls=controls,
)
```

여기서 중요한 점은 `controls_dump.yaml`과 `hierarchical_profile.yaml`의 관계다.

- `controls_dump.yaml`은 원본에 가까운 UIA dump이다.
- `hierarchical_profile.yaml`은 사람이 검토하고 target 이름을 확정하기 위한 계층형 초안이다.

## 4. 생성 산출물

profile generator가 만드는 산출물은 다음과 같다.

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

각 산출물의 목적은 다음과 같다.

| 산출물 | 목적 |
| --- | --- |
| `app.yaml` | 앱 경로, 창 제목, window rect, backend 등 앱 단위 정보 |
| `elements.yaml` | 기존 방식의 자동화 element 초안 |
| `controls_dump.yaml` | UIA 컨트롤 원본 dump |
| `hierarchical_profile.yaml` | group.control 형태의 계층형 target profile |
| `screenshot.png` | 원본 창 이미지 |
| `annotated_screenshot.png` | 컨트롤 label과 bounding box가 그려진 이미지 |
| `controls_map.yaml` | label 번호와 컨트롤 상세 정보 매핑 |

이번 변경에서 가장 중요한 신규 산출물은 `hierarchical_profile.yaml`이다.

## 5. 계층형 profile의 목적

GUI 자동화에서는 같은 이름의 컨트롤이 여러 개 나올 수 있다.

예를 들어 화면에 `Apply` 버튼이 여러 개 있으면 단순히 `apply_button`이라고 부르는 것은 위험하다.

따라서 target은 다음처럼 group을 포함해야 한다.

```text
parameter_group.frequency_apply_button
parameter_group.power_apply_button
operation_group.apply_button
```

이 방식의 장점은 다음과 같다.

- 같은 이름의 컨트롤을 group 경로로 구분할 수 있다.
- 사람이 시나리오를 읽을 때 어느 영역의 컨트롤인지 이해하기 쉽다.
- Fail-Safe V2의 target resolver가 profile을 기준으로 안정적으로 target을 찾을 수 있다.

## 6. Grouping 기준 변경

초기 설계에서는 `automation_id` 문자열의 prefix를 보고 group을 판단했다.

예를 들어 다음 id를 보고 `operation_group`을 parent로 추론하는 방식이었다.

```text
QApplication.ControlPanelWindow.central_widget.operation_group.connect_button
```

하지만 이 방식은 UIA id 구조가 항상 의미 있는 계층을 보장한다는 가정에 기대고 있다.

이번 변경에서는 grouping 기준을 영역 기반으로 바꾸었다.

새 기준은 다음과 같다.

```text
컨트롤의 중심점이 어떤 group rectangle 안에 들어가는가?
여러 group 안에 들어가면 가장 작은 group을 선택한다.
```

예를 들어 `operation_group`의 영역이 있고, `connect_button`의 중심점이 그 안에 있으면 다음 target이 생성된다.

```text
operation_group.connect_button
```

## 7. Group 후보 판정

모든 컨트롤이 group이 되는 것은 아니다. group 후보는 다음 기준 중 하나를 만족해야 한다.

```python
GROUP_CONTROL_TYPES = {"Group", "Pane", "Window", "Tab", "TabItem"}
```

또는 PyQt의 `QGroupBox`처럼 class 이름이 group box 계열이면 group 후보가 된다.

```python
if class_name.endswith("GroupBox"):
    return True
```

또는 automation id의 마지막 segment가 `_group`으로 끝나면 group으로 본다.

```python
return automation_id.split(".")[-1].endswith("_group") if automation_id else False
```

이 기준은 group 후보를 잡기 위한 기준일 뿐이다. 실제 소속 판정은 automation id 문자열이 아니라 rectangle containment로 수행한다.

## 8. 영역 기반 포함 판정 코드

영역 기반 grouping의 핵심 함수는 `_center`, `_contains_point`, `_smallest_containing_group`이다.

```python
def _center(control: Dict[str, Any]) -> tuple[float, float]:
    region = _region(control)
    return (
        region["x"] + (region["width"] / 2),
        region["y"] + (region["height"] / 2),
    )
```

`_center()`는 컨트롤 rectangle의 중심점을 계산한다.

```python
def _contains_point(container: Dict[str, Any], point: tuple[float, float]) -> bool:
    region = _region(container)
    x, y = point
    return (
        region["x"] <= x <= region["x"] + region["width"]
        and region["y"] <= y <= region["y"] + region["height"]
    )
```

`_contains_point()`는 특정 point가 container rectangle 안에 들어가는지 검사한다.

```python
def _smallest_containing_group(
    control: Dict[str, Any],
    groups: list[tuple[str, Dict[str, Any]]],
) -> str:
    point = _center(control)
    control_index = control.get("index")
    candidates = [
        (group_path, group_control)
        for group_path, group_control in groups
        if group_control.get("index") != control_index
        and _contains_point(group_control, point)
    ]
    if not candidates:
        return "ungrouped"
    return min(candidates, key=lambda item: _area(item[1]))[0]
```

`_smallest_containing_group()`는 컨트롤을 포함하는 group 후보 중 면적이 가장 작은 group을 선택한다.

이 방식은 중첩 group이 있을 때 중요하다.

예를 들어 전체 window, central widget, operation group이 모두 connect button을 포함할 수 있다. 이때 가장 작은 operation group을 선택해야 실제 의미상 group에 가까워진다.

## 9. Profile 생성 과정

`build_hierarchical_profile()`은 다음 순서로 동작한다.

```text
1. profile 기본 구조 생성
2. group 후보 수집
3. group끼리도 containment를 계산하여 child_groups 생성
4. 일반 control을 가장 작은 포함 group에 배치
5. target_index 생성
6. 이름 충돌이 있으면 pending_manual_review에 기록
```

profile 기본 구조는 다음과 같다.

```python
profile: Dict[str, Any] = {
    "profile_version": 1,
    "naming_policy": {
        "mode": "manual_review",
        "description": (
            "Generator groups controls by rectangle containment and suggests names from automation_id. "
            "A human should review names before scenario authoring."
        ),
    },
    "screens": {
        screen_key: {
            "title": app_info.get("window_title", ""),
            "discovered_by": discovered_by,
            "window_rect": app_info.get("window_rect", {}),
            "grouping_strategy": "smallest_containing_group_by_rectangle",
            "groups": {
                "ungrouped": {
                    "group_path": "ungrouped",
                    "naming_status": "generated",
                    "controls": {},
                    "child_groups": {},
                }
            },
        }
    },
    "target_index": {},
    "pending_manual_review": [],
}
```

여기서 `naming_policy.mode`는 `manual_review`이다. 이것은 generator가 최종 이름을 확정하지 않는다는 의미다. generator는 이름을 제안하고, 사람은 automation id와 screenshot을 보고 최종 naming을 결정한다.

## 10. Control record 구조

각 control은 다음 형태로 저장된다.

```python
def _control_record(control: Dict[str, Any], target_path: str) -> Dict[str, Any]:
    return {
        "target_path": target_path,
        "naming_status": "suggested",
        "label_no": control.get("index"),
        "automation_id": control.get("automation_id", ""),
        "name": control.get("name", ""),
        "control_type": control.get("control_type", ""),
        "element_type": control.get("element_type", ""),
        "class_name": control.get("class_name", ""),
        "region": _region(control),
        "find_by": {
            "priority": ["uia", "region"],
            "uia": {
                "automation_id": control.get("automation_id", ""),
                "title": control.get("name", ""),
                "control_type": control.get("control_type", ""),
                "class_name": control.get("class_name", ""),
            },
            "region": _region(control),
        },
    }
```

중요 필드는 다음과 같다.

| 필드 | 의미 |
| --- | --- |
| `target_path` | group.control 형태의 최종 후보 target |
| `naming_status` | 사람이 검토해야 하는지 여부 |
| `label_no` | annotated screenshot 및 controls_dump와 대조할 수 있는 index |
| `automation_id` | UIA 기반 우선 locator |
| `region` | 화면 영역 기반 fallback locator |
| `find_by.priority` | target resolver가 locator를 시도할 순서 |

## 11. 이름 제안 방식

이름 제안은 여전히 `automation_id`를 우선 사용한다.

```python
def _suggest_control_name(control: Dict[str, Any]) -> str:
    automation_id = control.get("automation_id", "") or ""
    name = control.get("name", "") or ""
    element_type = control.get("element_type", "control") or "control"
    index = control.get("index", "unknown")
    segments = _automation_segments(automation_id)
    if segments:
        return _slug(segments[-1], f"{element_type}_{index}")
    return _slug(name, f"{element_type}_{index}")
```

예를 들어 automation id가 다음과 같으면:

```text
QApplication.ControlPanelWindow.central_widget.operation_group.connect_button
```

마지막 segment인 `connect_button`을 control 이름 후보로 사용한다.

하지만 이것은 자동 확정이 아니다. 사람이 `hierarchical_profile.yaml`을 열어 보고 실제 의미에 맞게 이름을 수정할 수 있다.

## 12. 이름 충돌 처리

같은 group 안에서 동일한 이름이 두 번 나오면 `_unique_key()`가 suffix를 붙인다.

```python
def _unique_key(base_key: str, used_keys: set[str]) -> str:
    if base_key not in used_keys:
        used_keys.add(base_key)
        return base_key

    counter = 2
    while f"{base_key}_{counter}" in used_keys:
        counter += 1
    key = f"{base_key}_{counter}"
    used_keys.add(key)
    return key
```

예를 들어 같은 group 안에 `apply_button`이 두 개 있으면 두 번째는 `apply_button_2`가 된다.

이 경우 `pending_manual_review`에 기록된다.

```python
profile["pending_manual_review"].append(
    {
        "reason": "duplicate_control_name_in_group",
        "target_path": target_path,
        "suggested_name": suggested_name,
        "label_no": control.get("index"),
    }
)
```

이 목록은 사람이 반드시 검토해야 할 지점을 알려준다.

## 13. Scenario Discovery 기능

두 번째 신규 기능은 scenario discovery이다.

기본 profile generator는 현재 보이는 화면만 분석할 수 있다. 하지만 실제 GUI는 버튼을 누르거나 탭을 바꿔야 새 창, 새 탭, popup, 동적 panel이 나타난다.

따라서 새 기능은 시나리오를 한 번 실행하면서 화면 변화를 관찰한다.

전체 흐름은 다음과 같다.

```text
초기 profile 생성
-> scenario YAML 로드
-> click / set_text 같은 조작 step 실행
-> step 이후 같은 process의 visible window 목록 확인
-> UI tree signature가 처음 보는 형태이면 새 screen으로 추가
-> discovered_by에 어떤 step에서 발견됐는지 기록
```

CLI 옵션은 다음과 같다.

```bash
python -m app_profile_generator.main \
  --app-path d:\app\fcm_desktop.py \
  --discovery-scenario d:\app\fcm_gui_automation\scenarios\qt_complex_test.yaml
```

여러 시나리오를 반복 지정할 수도 있다.

```bash
python -m app_profile_generator.main \
  --app-path d:\app\fcm_desktop.py \
  --discovery-scenario scenario_a.yaml \
  --discovery-scenario scenario_b.yaml
```

## 14. Scenario Discovery 대상 action

모든 action을 실행하지는 않는다.

현재 discovery가 실행하는 action은 다음 두 가지다.

```python
DISCOVERY_ACTIONS = {"click", "set_text"}
```

읽기 전용 action은 건너뛴다.

```python
READ_ONLY_ACTIONS = {"launch_or_connect", "verify_text", "verify_color", "screenshot"}
```

종료 action이 나오면 discovery를 중단한다.

```python
STOP_ACTIONS = {"safe_close"}
```

이 설계는 profile discovery가 불필요한 검증 action까지 반복 실행하지 않도록 하기 위한 것이다.

## 15. Scenario Discovery 메인 흐름

`discover_profile_from_scenario()`가 핵심 함수다.

```python
def discover_profile_from_scenario(
    profile: Dict[str, Any],
    initial_window,
    scenario: Dict[str, Any],
    delay: float = 0.5,
) -> Dict[str, Any]:
    pid = initial_window.process_id()
    seen_signatures = _profile_signatures(profile)
    seen_signatures.add(_controls_signature(dump_controls(initial_window)))
    steps = scenario.get("steps", [])
```

먼저 현재 process id를 가져온다. 이후 기존 profile의 signature와 초기 window signature를 저장한다. signature는 이미 본 UI tree를 다시 새 screen으로 추가하지 않기 위한 fingerprint이다.

각 step은 다음 조건을 통과해야 실행된다.

```python
action = step.get("action")
if action in STOP_ACTIONS:
    break
if action in READ_ONLY_ACTIONS:
    continue
if action not in DISCOVERY_ACTIONS:
    continue
```

그 다음 target을 찾아 action을 실행한다.

```python
trigger_target = step.get("target")
_execute_step_for_discovery(pid, step)
time.sleep(delay)
```

action 이후 같은 process의 visible window를 다시 조사한다.

```python
for window_index, window in enumerate(_visible_windows_for_pid(pid)):
    controls = dump_controls(window)
    signature = _controls_signature(controls)
    if signature in seen_signatures:
        continue
```

처음 보는 signature이면 새 screen으로 profile을 만든다.

```python
discovered_profile = build_hierarchical_profile(
    app_info={
        "window_title": window_info["window_title"],
        "window_rect": window_info["window_rect"],
    },
    controls=controls,
    screen_key=screen_key,
    discovered_by={
        "type": "scenario_step",
        "step_index": step_index,
        "action": action,
        "trigger_target": trigger_target,
        "parent_screen": "main_window",
    },
)
```

마지막으로 기존 profile에 merge한다.

```python
_merge_profile_screen(profile, discovered_profile, screen_key)
seen_signatures.add(signature)
```

## 16. Target 찾기 방식

Discovery 실행 중에는 scenario step의 target을 실제 UI control로 찾아야 한다.

이를 위해 `_find_control()`을 사용한다.

```python
def _find_control(pid: int, target: str):
    target_leaf = target.split(".")[-1]
    for window in _visible_windows_for_pid(pid):
        for control in window.descendants():
            info = control.element_info
            automation_id = getattr(info, "automation_id", "") or ""
            name = getattr(info, "name", "") or ""
            if (
                automation_id == target
                or automation_id.endswith(f".{target}")
                or automation_id.endswith(f".{target_leaf}")
                or name == target
            ):
                return control
    raise ValueError(f"Discovery target not found: {target}")
```

여기서 `target_leaf`가 중요하다.

예를 들어 scenario target이 `operation_group.connect_button`이면 leaf는 `connect_button`이다. 실제 automation id가 긴 형태여도 마지막 segment가 맞으면 찾을 수 있다.

```text
scenario target: operation_group.connect_button
target leaf: connect_button
automation id: QApplication.ControlPanelWindow.central_widget.operation_group.connect_button
```

따라서 discovery는 기존 짧은 target과 새 group.control target을 모두 어느 정도 수용할 수 있다.

## 17. Action 실행 방식

Discovery에서 click은 여러 방법을 순서대로 시도한다.

```python
def _click(control) -> None:
    for method_name in ("click", "click_input", "invoke"):
        try:
            control.set_focus()
            getattr(control, method_name)()
            return
        except Exception:
            pass
    control.set_focus()
    control.type_keys("{SPACE}", set_foreground=True)
```

이 방식은 GUI framework마다 click 방식이 다를 수 있기 때문에 fallback을 여러 개 둔 것이다.

`set_text`는 먼저 `set_edit_text()`를 시도하고, 실패하면 키 입력 fallback을 사용한다.

```python
if step["action"] == "set_text":
    value = str(step.get("value", ""))
    control.set_focus()
    try:
        control.set_edit_text(value)
    except Exception:
        control.type_keys("^a{BACKSPACE}", set_foreground=True)
        control.type_keys(value, with_spaces=True, set_foreground=True)
    return
```

## 18. UI Tree Signature

새 화면인지 판단하기 위해 controls dump를 signature로 바꾼다.

```python
def _controls_signature(controls: List[Dict[str, Any]]) -> tuple:
    values = []
    for control in controls:
        if "error" in control:
            continue
        rect = control.get("rectangle", {}) or {}
        values.append(
            (
                control.get("automation_id", ""),
                control.get("name", ""),
                control.get("control_type", ""),
                rect.get("x"),
                rect.get("y"),
                rect.get("width"),
                rect.get("height"),
            )
        )
    return tuple(sorted(values))
```

signature는 다음 값을 포함한다.

- automation id
- name
- control type
- x
- y
- width
- height

이 값들이 달라지면 새로운 UI 상태로 본다.

## 19. Screen Key 생성

새 screen은 어떤 step에서 발견됐는지 알 수 있도록 key를 만든다.

```python
def _screen_key(step_index: int, action: str, target: str | None, window_index: int) -> str:
    target_name = (target or "unknown").replace(".", "_")
    return f"step_{step_index:03d}_{action}_{target_name}_window_{window_index}"
```

예를 들어 18번째 step에서 `open_dialog_button`을 click해 새 창이 나오면 다음과 같은 key가 만들어질 수 있다.

```text
step_018_click_open_dialog_button_window_1
```

같은 key가 이미 있으면 `_unique_screen_key()`가 suffix를 붙인다.

## 20. Merge 방식

새 screen은 기존 profile의 `screens` 아래에 추가된다.

```python
def _merge_profile_screen(
    profile: Dict[str, Any],
    discovered_profile: Dict[str, Any],
    screen_key: str,
) -> None:
    profile.setdefault("screens", {})[screen_key] = discovered_profile["screens"][screen_key]
```

target index는 screen key를 prefix로 붙여 충돌을 피한다.

```python
for target_path, target_info in discovered_profile.get("target_index", {}).items():
    index_key = f"{screen_key}.{target_path}"
    profile.setdefault("target_index", {})[index_key] = target_info
```

이 방식은 메인 화면과 새 창에 같은 group/control 이름이 있어도 index 충돌을 피할 수 있다.

## 21. CLI 옵션 변경

`cli/main.py`에 discovery 옵션이 추가됐다.

```python
parser.add_argument(
    "--discovery-scenario",
    action="append",
    default=[],
    help="Scenario YAML to run once and merge newly discovered screens into hierarchical_profile.yaml.",
)
parser.add_argument("--discovery-delay", type=float, default=0.5)
```

`--discovery-scenario`는 여러 번 지정할 수 있다.

`--discovery-delay`는 action 실행 후 UI가 안정화될 시간을 지정한다. 기본값은 0.5초다.

## 22. CLI에서 Discovery 호출

기본 profile 파일을 먼저 쓴 뒤, discovery가 요청되면 scenario를 실행하고 `hierarchical_profile.yaml`을 다시 저장한다.

```python
discovery_status = "not requested"
if args.discovery_scenario:
    discovered_count_before = len(hierarchical_profile.get("screens", {}))
    for scenario_path in args.discovery_scenario:
        scenario = load_discovery_scenario(Path(scenario_path).expanduser().resolve())
        hierarchical_profile = discover_profile_from_scenario(
            profile=hierarchical_profile,
            initial_window=window,
            scenario=scenario,
            delay=args.discovery_delay,
        )
    write_yaml(output_dir / "hierarchical_profile.yaml", hierarchical_profile)
    discovered_count_after = len(hierarchical_profile.get("screens", {}))
    discovery_status = (
        f"merged {discovered_count_after - discovered_count_before} discovered screens"
    )
```

이 구조는 discovery 중 새 screen이 추가된 뒤 최종 profile 파일이 최신 상태로 다시 저장되도록 한다.

## 23. Annotated Screenshot Label 개선

이번 작업 범위 안에는 `annotated_screenshot.py`의 label 기준 개선도 포함되어 있다.

기존에는 annotation 번호가 단순히 1부터 다시 붙었다. 지금은 control dump의 원본 index를 label 번호로 사용한다.

```python
for fallback_i, control in enumerate(controls):
    if "error" in control:
        continue
    control_index = int(control.get("index", fallback_i))
```

이 변경의 장점은 다음과 같다.

- `annotated_screenshot.png`의 label 번호
- `controls_map.yaml`의 `label_no`
- `controls_dump.yaml`의 `index`

위 세 값이 서로 대응되기 쉬워진다.

## 24. 기대되는 hierarchical_profile.yaml 예시

생성될 profile의 핵심 구조는 다음과 같다.

```yaml
profile_version: 1
naming_policy:
  mode: manual_review
screens:
  main_window:
    title: PyQt Input Panel
    grouping_strategy: smallest_containing_group_by_rectangle
    groups:
      operation_group:
        group_path: operation_group
        controls:
          connect_button:
            target_path: operation_group.connect_button
            naming_status: suggested
            automation_id: QApplication.ControlPanelWindow.central_widget.operation_group.connect_button
            control_type: Button
            class_name: QPushButton
target_index:
  operation_group.connect_button:
    screen: main_window
    group: operation_group
    control: connect_button
```

시나리오 실행 중 새 창이 발견되면 다음처럼 screen이 추가된다.

```yaml
screens:
  step_018_click_open_dialog_button_window_1:
    title: Setting Dialog
    discovered_by:
      type: scenario_step
      step_index: 18
      action: click
      trigger_target: open_dialog_button
      parent_screen: main_window
```

## 25. 현재 검증한 내용

이번 변경 후 다음 검증을 수행했다.

```powershell
python -m py_compile app_profile_generator\main.py app_profile_generator\cli\main.py app_profile_generator\inspection\hierarchical_profile.py app_profile_generator\inspection\scenario_discovery.py app_profile_generator\inspection\control_dumper.py app_profile_generator\output\profile_writer.py
```

결과: 문법 오류 없음.

또한 CLI help를 확인했다.

```powershell
python -m app_profile_generator.main --help
```

출력에 다음 옵션이 추가된 것을 확인했다.

```text
--discovery-scenario DISCOVERY_SCENARIO
--discovery-delay DISCOVERY_DELAY
```

기존 controls dump 샘플로 계층 target 생성도 확인했다.

```text
connection_group.result_lamp
parameter_group.frequency_input
parameter_group.power_input
operation_group.connect_button
operation_group.disconnect_button
```

## 26. 현재 한계

현재 구현은 1차 MVP다. 다음 한계가 있다.

- 실제 GUI discovery 전체 실행은 아직 자동 검증하지 않았다.
- 새 screen merge는 append 중심이며, 사람이 수정한 이름과 기존 screen을 정교하게 diff/merge하는 기능은 아직 없다.
- UI tree signature가 좌표까지 포함하므로 창 위치가 바뀌면 다른 screen으로 판단할 수 있다.
- `click`, `set_text` 외 action은 discovery에서 실행하지 않는다.
- tab 전환처럼 같은 window 안에서 일부 panel만 바뀌는 경우도 새 signature로 잡히지만, panel 단위 merge는 아직 screen 단위 merge로 처리된다.
- popup이 다른 process에서 뜨는 프로그램은 현재 pid 기준 window 검색으로는 잡히지 않을 수 있다.

## 27. 다음 개선 방향

다음 단계는 다음 순서가 적절하다.

1. `hierarchical_profile.yaml`을 사람이 수정한 뒤 다시 discovery를 실행해도 수정된 이름을 보존하는 merge 정책 추가
2. screen 단위가 아니라 group 또는 panel 단위 diff 추가
3. target resolver를 만들어 Fail-Safe V2에서 `group.control` target을 직접 사용할 수 있게 연결
4. discovery action을 `select_tab`, `open_menu`, `double_click` 등으로 확장
5. signature에서 절대 좌표 의존도를 낮추고 automation id 중심 fingerprint 추가
6. discovery 실행 결과에 screenshot과 controls_map도 screen별로 저장

## 28. 결론

이번 변경으로 profile generator는 단순 UIA dump 도구에서 한 단계 발전했다.

가장 중요한 변화는 grouping 기준이 사람이 이해하기 쉬운 화면 영역 기준으로 바뀐 것이다. 이제 `operation_group` 영역 안에 있는 `connect_button`은 `operation_group.connect_button`으로 profile에 기록된다.

또한 scenario discovery가 추가되어, 처음 화면에 없는 새 창이나 탭도 시나리오 실행 중 발견하여 profile에 누적할 수 있는 기반이 생겼다.

이 구조는 Fail-Safe V2의 target resolver와 잘 맞는다. Fail-Safe는 `fault_flag`, `voltage_value`, `operation_group.connect_button` 같은 target을 신뢰해야 하며, profile generator는 그 target이 실제 UIA control과 화면 region으로 연결되는 근거를 제공한다.

따라서 현재 구현은 최종 완성본이라기보다 다음 단계의 핵심 기반이다.

```text
profile generator
-> hierarchical profile
-> scenario-driven screen discovery
-> target resolver
-> Fail-Safe V2 monitor and decision engine
```

이 흐름으로 연결하면, 모든 주요 시나리오를 한 번 실행해 프로그램 전체의 화면 구조와 controller profile을 점진적으로 완성하는 목표에 가까워진다.
