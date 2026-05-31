# Profile Generator Ratio/Grid/OCR Update Report

작성일: 2026-06-01

## 1. 변경 목적

이번 변경의 목적은 GUI 자동화 프로필 생성 방식을 실제 운영 환경에 더 안정적으로 맞추는 것이다.

기존 구조는 UIA 컨트롤 덤프와 절대 좌표 기반 region을 중심으로 동작했고, 일부 복잡한 내부 컨트롤은 YOLO 기반 child scan으로 보완하는 흐름이 있었다. 이번 변경에서는 YOLO를 제거하고, 창 이동/리사이즈/DPI 변화에 강한 비율 좌표를 기본 좌표계로 사용하도록 바꾸었다. 또한 `MFCGridCtrl`처럼 pywinauto가 내부 셀을 직접 노출하지 못하는 컨트롤은 OpenCV로 셀 경계를 분석해 각 셀을 독립적인 controller로 프로필에 저장하도록 확장했다.

OCR은 범위를 줄여 숫자 값을 읽는 용도로만 사용하도록 정리했다.

## 2. 주요 변경 요약

### 2.1 YOLO 제거

변경 파일:

- `app_profile_generator/cli/main.py`
- `app_profile_generator/inspection/yolo_children.py`

변경 내용:

- `--yolo-model`, `--yolo-conf`, `--yolo-iou`, `--yolo-imgsz`, `--yolo-device`, `--no-yolo` CLI 옵션 제거
- profile 생성 및 sync 과정에서 YOLO child scan 분기 제거
- `app_profile_generator/inspection/yolo_children.py` 삭제
- CLI 출력에서 YOLO scan 상태 대신 `MFCGridCtrl cell scan` 상태를 출력하도록 변경

결과:

- profile generator 실행 경로에서 YOLO 의존성이 사라졌다.
- 모델 파일 유무, Ultralytics 설정, YOLO 추론 실패에 영향을 받지 않는다.

### 2.2 비율 좌표계 도입

변경 파일:

- `app_profile_generator/inspection/hierarchical_profile.py`
- `app_profile_generator/inspection/control_dumper.py`
- `app_profile_generator/imaging/annotated_screenshot.py`
- `fcm_gui_automation/recognition/pywinauto_adapter.py`
- `app_profile_generator/README.md`

변경 내용:

- `hierarchical_profile.yaml` 최상위에 `coordinate_system: window_ratio` 추가
- group/control의 `region`을 절대 좌표가 아니라 창 기준 비율 좌표로 저장
- 각 profile control에 `region_units: window_ratio` 추가
- `elements.yaml`의 `find_by.region`도 window rect가 주어지면 비율 좌표로 생성
- `controls_map.yaml`에는 기존 절대 좌표/창 상대 좌표와 함께 `window_ratio_region` 추가
- `controls_raw.yaml`과 `controls_dump.yaml`에도 각 controller의 `rectangle_ratio`와 `rectangle_ratio_units: window_ratio` 추가
- 런타임 `PyWinAutoAdapter`가 `window_ratio` region을 현재 창 크기와 위치에 맞춰 다시 실제 좌표로 변환하도록 변경
- 색상 검증에서도 비율 좌표 region을 screenshot 픽셀 좌표로 변환하도록 보강

예시:

```yaml
coordinate_system: window_ratio
screens:
  main_window:
    groups:
      ungrouped:
        controls:
          validation_grid_cell_1_1:
            region:
              x: 0.15
              y: 0.18
              width: 0.15
              height: 0.08
            region_units: window_ratio
```

의미:

- `x: 0.15`는 창 왼쪽에서 전체 창 너비의 15% 지점이라는 뜻이다.
- `width: 0.15`는 컨트롤 너비가 전체 창 너비의 15%라는 뜻이다.

결과:

- 창 위치가 바뀌어도 프로필 region이 깨지지 않는다.
- 창 크기, 해상도, DPI 변화가 있어도 같은 상대 위치를 기준으로 target을 복원할 수 있다.

### 2.3 MFCGridCtrl 셀 검출 추가

변경 파일:

- `app_profile_generator/inspection/grid_cells.py`
- `app_profile_generator/inspection/control_dumper.py`
- `app_profile_generator/inspection/hierarchical_profile.py`
- `app_profile_generator/requirements.txt`
- `app_profile_generator/README.md`

추가 의존성:

```text
opencv-python
```

동작 방식:

1. pywinauto로 UIA descendants를 순회한다.
2. 순회 도중 `class_name == "MFCGridCtrl"`인 control을 발견하면 즉시 window screenshot을 준비한다.
3. 해당 control의 rectangle 영역을 screenshot에서 crop한다.
4. OpenCV adaptive threshold와 morphology 연산으로 수평/수직 grid line을 찾는다.
5. 인접한 수평선/수직선 사이를 cell 영역으로 계산한다.
6. 각 cell을 synthetic control로 만들어 현재 수집 중인 controller 목록에 바로 추가한다.
7. 이후 `controls_raw.yaml`, `controls_dump.yaml`, `elements.yaml`, `hierarchical_profile.yaml` 생성 단계에서는 이 cell들도 기존 controller와 같은 입력으로 처리된다.

생성되는 synthetic cell control 예시:

```yaml
name: Validation Grid cell 1,1
control_type: Cell
element_type: grid_cell
automation_id: validation_grid_r1_c1
class_name: MFCGridCtrlCell
parent_class_name: MFCGridCtrl
source: opencv_mfc_grid_cell
grid_cell:
  row: 1
  column: 1
rectangle_ratio:
  x: 0.15
  y: 0.18
  width: 0.15
  height: 0.08
rectangle_ratio_units: window_ratio
```

결과:

- pywinauto가 내부 셀을 controller로 노출하지 않는 `MFCGridCtrl`도 profile target으로 다룰 수 있다.
- 시나리오에서는 셀을 기존 controller와 같은 방식의 target으로 참조할 수 있는 기반이 생겼다.

### 2.4 OCR 숫자 전용화

변경 파일:

- `fcm_gui_automation/recognition/ocr_adapter.py`

변경 내용:

- Tesseract 기본 config에 숫자 전용 whitelist 적용

```text
--psm 6 -c tessedit_char_whitelist=0123456789.-+
```

- `read_number()` 추가
- CLI 실행 시 텍스트 전체가 아니라 숫자 값을 읽어 출력하도록 변경

결과:

- OCR은 일반 텍스트 판독보다 numeric value 판독에 집중한다.
- 숫자, 소수점, 부호만 허용하므로 불필요한 문자 오인식 가능성이 줄어든다.

## 3. 검증 산출물

검증 스크립트:

```text
app_profile_generator/tools/validate_new_features.py
```

실행 명령:

```powershell
python -m app_profile_generator.tools.validate_new_features
```

생성된 검증 output:

```text
profiles/validation/2026-06-01_071525/
```

주요 파일:

- `validation_summary.yaml`
- `README.md`
- `mfc_grid_input.png`
- `numeric_ocr_input.png`
- `controls_raw.yaml`
- `controls_dump.yaml`
- `elements.yaml`
- `hierarchical_profile.yaml`

검증 결과:

```yaml
grid:
  expected_cell_count: 12
  detected_cell_count: 12
coordinate_system:
  profile_coordinate_system: window_ratio
  first_cell_region:
    x: 0.15
    y: 0.18
    width: 0.15
    height: 0.08
  first_cell_region_units: window_ratio
ocr:
  expected_number: 123.45
  actual_number: 123.45
  status: pass
```

검증 의미:

- 합성 `MFCGridCtrl` 이미지에서 4행 x 3열, 총 12개 cell을 모두 검출했다.
- 검출된 첫 번째 cell이 절대 좌표가 아니라 `window_ratio` 좌표로 profile에 저장되었다.
- 숫자 OCR 이미지에서 `123.45`를 정상적으로 읽었다.

## 4. 검증 중 확인한 사항

정상 확인:

- `python -m py_compile`로 수정 파일 컴파일 통과
- `python -m app_profile_generator.cli.main --help` 실행 시 YOLO 옵션 제거 확인
- `--discover-all-scenarios`와 `--discovery-scenario-dir` CLI 옵션 확인
- OpenCV import 확인
- 검증 스크립트 실행 결과 `Detected MFCGridCtrl cells: 12 / 12`
- OCR numeric status `pass`
- 실제 더미 앱에서 전체 시나리오 discovery 실행 확인
- `qt_complex_test`의 `open_dialog_button` 클릭 후 `Setting Dialog` embedded window controller가 새 screen으로 추가됨

주의 사항:

- 실제 pywinauto runtime import 검증 중 `comtypes`가 시스템 site-packages의 `comtypes/gen` 경로에 캐시 파일을 쓰려다 권한 오류가 발생했다.
- 이 문제는 이번 변경 코드의 문법/로직 오류가 아니라 기존 pywinauto/comtypes 캐시 생성 권한 문제다.
- 실제 Windows GUI 연결 검증을 하려면 comtypes cache directory 권한 또는 사용자 writable cache 설정을 먼저 정리하는 것이 좋다.
- `basic_test.yaml`은 현재 생성 profile의 target naming과 맞지 않는 `parameter_group_3`, `parameter_group_5` target을 사용해 discovery summary에 step error가 기록된다.

전체 시나리오 discovery 검증 output:

```text
profiles/generated/fcm_desktop_2026-06-01_073333/
```

핵심 결과:

```yaml
scenario_count: 3
completed:
  - name: qt_complex_test
    new_screens: 1
failed: []
screens_before: 1
screens_after: 2
discovered_screen_count: 1
```

추가된 screen:

```yaml
qt_complex_test_step_015_click_open_dialog_button_embedded_0:
  title: Setting Dialog
  discovered_by:
    window_source: embedded_window_control
    scenario_name: qt_complex_test
    trigger_target: open_dialog_button
```

## 5. 남은 작업 제안

1. 실제 대상 앱에서 `MFCGridCtrl`이 pywinauto dump에 어떤 `class_name`, `control_type`, rectangle로 잡히는지 확인한다.
2. 실제 grid line 스타일이 합성 이미지와 다르면 OpenCV threshold/kernel 값을 조정한다.
3. 셀 target naming 정책을 업무 의미에 맞게 확장한다. 예: `row_1_voltage`, `row_2_current`.
4. OCR numeric value target을 profile region과 연결하는 시나리오 action을 추가한다.
5. 오래된 시나리오 target 이름을 새 profile naming에 맞게 정리한다.
6. pywinauto/comtypes cache 권한 문제를 자동화 실행 전 환경 점검에 포함한다.

## 6. 결론

이번 변경으로 profile generator는 YOLO 모델에 의존하지 않고, pywinauto + OpenCV + 비율 좌표 기반으로 동작하도록 정리되었다.

가장 중요한 변화는 profile의 좌표 안정성이다. 이제 profile에 저장되는 target region은 창의 절대 위치가 아니라 창 내부 상대 비율이므로, 창 이동, 창 크기 변경, 해상도 변경, DPI 변경에 더 강하다.

또한 `MFCGridCtrl` 내부 셀을 synthetic controller로 저장하는 기반이 추가되어, 기존 UIA tree만으로는 접근하기 어려운 grid cell을 자동화 target으로 삼을 수 있게 되었다.
