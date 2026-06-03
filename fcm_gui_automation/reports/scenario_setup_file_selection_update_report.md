# Scenario Setup File Selection Update Report

작성일: 2026-06-01

## 목적

시나리오 시작 전에 공통으로 수행해야 하는 초기 진입 절차를 `setup` 섹션으로 분리하고, 번호 입력 후 Windows 파일 선택 다이얼로그에서 특정 파일을 선택하는 흐름을 자동화할 수 있도록 기능을 추가했다.

대상 흐름은 다음과 같다.

1. main 화면에서 특정 버튼 클릭
2. 새 번호 입력 창 표시
3. 번호 입력
4. 확인 버튼 클릭
5. 파일 선택 다이얼로그 표시
6. 시나리오에 지정된 파일 경로 선택
7. 본 시나리오 `steps` 실행

## 주요 변경 사항

### 1. `setup` 섹션 지원

`ScenarioRunner`가 기존 `steps` 실행 전에 `setup` 리스트를 먼저 실행하도록 수정했다.

예시:

```yaml
name: "socon_file_setup_test"
setup:
  - action: "launch_or_connect"
  - action: "click"
    target: "open_socon_button"
  - action: "wait_window"
    title: ".*Socon Number.*"
  - action: "set_text"
    target: "socon_number_input"
    value: "12345"
  - action: "click"
    target: "socon_number_ok_button"
  - action: "select_file"
    dialog_title: ".*Select Socon File.*"
    file_path: "D:\\app\\fcm_gui_automation\\test_data\\socon_sample.csv"

steps:
  - action: "verify_text"
    target: "status_label"
    value: "SOCON FILE SELECTED"
```

`setup`은 번호 입력, 파일 선택, 로그인, 초기 화면 이동처럼 시나리오 본문 전에 필요한 준비 동작을 담는 용도로 사용한다.

### 2. `wait_window` action 추가

새 창 또는 자식 다이얼로그가 표시될 때까지 기다리는 action을 추가했다.

```yaml
- action: "wait_window"
  title: ".*Socon Number.*"
  timeout: 10
```

PyQt의 child dialog처럼 top-level window가 아닌 형태도 잡을 수 있도록 main window descendants의 `Window` control도 함께 검사한다.

### 3. `select_file` action 추가

Windows 파일 선택 다이얼로그에서 시나리오에 지정한 파일 경로를 입력하고 확인 버튼을 누르는 action을 추가했다.

```yaml
- action: "select_file"
  dialog_title: ".*Select Socon File.*"
  file_path: "D:\\app\\fcm_gui_automation\\test_data\\socon_sample.csv"
  timeout: 10
```

처리 방식:

- 파일 경로 존재 여부 확인
- 파일 선택 다이얼로그 대기
- 파일명 입력 컨트롤 탐색
- 전체 파일 경로 입력
- Enter 또는 열기 버튼으로 확정
- 다이얼로그가 닫힐 때까지 대기

Windows 공용 파일 다이얼로그의 파일명 입력 컨트롤은 automation id `1148`을 우선한다.

### 4. target matching 개선

기존 pywinauto target matching은 visible name 중심이었다.

이번 수정으로 아래 값을 모두 후보로 사용한다.

- visible name
- automation id 전체
- automation id segment
- automation id 마지막 leaf
- class name

따라서 시나리오에서 `open_socon_button`, `socon_number_input`, `socon_number_ok_button`처럼 Qt objectName 기반 target을 직접 사용할 수 있다.

### 5. click 중복 실행 방지

기존 click 동작은 `click_input`, `invoke`, `click`, `ENTER`를 순차적으로 계속 시도했다.

일부 버튼에서는 같은 클릭이 여러 번 발생할 수 있어, 하나의 방식이 성공하면 즉시 반환하도록 수정했다.

## 데모 앱 변경 사항

검증용 앱 `fcm_desktop.py`에 Socon 파일 선택 흐름을 추가했다.

추가된 UI:

- `Open Socon` 버튼
- `Socon Number` 다이얼로그
- `socon_number_input`
- `socon_number_ok_button`
- `QFileDialog` 기반 `Select Socon File` 파일 선택 다이얼로그

파일 선택 완료 후 main 화면에 다음 상태를 표시한다.

- `status_label`: `SOCON FILE SELECTED`
- `status_box`: 입력 번호와 선택 파일 경로

## 추가 파일

검증 시나리오:

```text
fcm_gui_automation/scenarios/socon_file_setup_test.yaml
```

검증용 데이터 파일:

```text
fcm_gui_automation/test_data/socon_sample.csv
```

## 검증 결과

실행 명령:

```powershell
python fcm_gui_automation\main.py --app-path d:\app\fcm_desktop.py --scenario d:\app\fcm_gui_automation\scenarios\socon_file_setup_test.yaml
```

결과: 성공

확인된 로그 핵심:

```text
setup step 3/11: wait_window
Detected child window: Socon Number
setup step 6/11: select_file
Selected file in dialog: D:\app\fcm_gui_automation\test_data\socon_sample.csv
steps step 7/11: verify_text
Verified text: SOCON FILE SELECTED
steps step 8/11: verify_text
Verified text: Socon Number: 12345
steps step 9/11: verify_text
Verified text: socon_sample.csv
All scenarios completed successfully.
```

추가 문법 검증:

```powershell
python -m py_compile fcm_gui_automation\core\scenario_runner.py fcm_gui_automation\core\action_executor.py fcm_gui_automation\recognition\pywinauto_adapter.py fcm_desktop.py
```

결과: 통과

## 사용 가이드

실제 사용 시 시나리오 시작 부분에 아래와 같은 `setup`을 작성하면 된다.

```yaml
setup:
  - action: "launch_or_connect"
  - action: "click"
    target: "open_socon_button"
  - action: "wait_window"
    title: ".*Socon Number.*"
  - action: "set_text"
    target: "socon_number_input"
    value: "12345"
  - action: "click"
    target: "socon_number_ok_button"
  - action: "select_file"
    dialog_title: ".*Open.*|.*열기.*|.*Select.*"
    file_path: "D:\\data\\target_file.csv"
```

번호나 파일 경로가 scenario마다 달라지는 경우에는 각 scenario YAML에서 `value`, `file_path`만 바꾸면 된다.

## 결론

이제 `fcm_gui_automation`은 시나리오 시작 전에 필요한 번호 입력 및 파일 선택 절차를 `setup`으로 표현할 수 있다.

파일 선택은 좌표 클릭이 아니라 pywinauto 기반 Windows 파일 다이얼로그 제어로 처리하므로 창 위치, DPI, 해상도 변화에 비교적 강하다.
