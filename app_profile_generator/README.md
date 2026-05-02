# App Profile Generator

Windows GUI 프로그램을 실행한 뒤 `pywinauto` UIA backend로 컨트롤 목록을 추출하고,
자동화 프로필 초안과 주석이 달린 스크린샷을 생성하는 도구입니다.

## Source Tree

```text
app_profile_generator/
├─ main.py                     # Backward-compatible CLI wrapper
├─ cli/
│  └─ main.py                  # CLI parsing and generation workflow orchestration
├─ runtime/
│  ├─ app_launcher.py          # Target app process launch
│  ├─ window_resolver.py       # Main window discovery and manual fallback
│  └─ screenshot_capture.py    # Raw target-window screenshot capture
├─ inspection/
│  └─ control_dumper.py        # UIA descendant dump and element draft creation
├─ output/
│  └─ profile_writer.py        # Output directory and YAML profile writers
└─ imaging/
   └─ annotated_screenshot.py  # Control bounding boxes and controls_map generation
```

## 실행

파일 탐색기로 선택:

```bash
python -m app_profile_generator.main
```

경로 지정:

```bash
python -m app_profile_generator.main --app-path d:\app\fcm_desktop.py
```

새 CLI 모듈 직접 실행:

```bash
python -m app_profile_generator.cli.main --app-path d:\app\fcm_desktop.py
```

## 생성 파일

```text
profiles/generated/<app_name>_<timestamp>/
├─ app.yaml
├─ elements.yaml
├─ controls_dump.yaml
├─ screenshot.png
├─ annotated_screenshot.png
└─ controls_map.yaml
```

## 사용 흐름

1. `annotated_screenshot.png`에서 화면 위 컨트롤 번호를 확인합니다.
2. `controls_map.yaml`에서 번호에 해당하는 `automation_id`, `name`, `control_type`, 좌표를 확인합니다.
3. `elements.yaml`의 `auto_button_001` 같은 임시 이름을 `save_button`처럼 의미 있는 이름으로 바꿉니다.
