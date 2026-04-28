# PyQt GUI 자동화 POC 작업 보고서

작성일: 2026-04-27
대상 프로젝트: `D:\app\fcm_gui_automation`
대상 애플리케이션: `D:\app\fcm_desktop.py`

## 1. 목적

이번 작업의 목적은 PyQt로 만든 데스크톱 애플리케이션을 `pywinauto`로 자동 제어하는 최소 동작 POC를 만드는 것이었다.
목표 범위는 다음 7가지였다.

- 프로그램 실행 또는 이미 실행된 창 연결
- 화면 캡처
- 버튼 또는 입력창 식별
- 클릭 수행
- 값 입력
- 결과 텍스트 확인
- 실패 시 스크린샷 저장 후 안전 종료

## 2. 초기 조건

처음 상태에서 대상 앱은 PyQt6 기반 입력 패널 형태였고, 자동화 프로젝트 구조는 존재하지 않았다.
따라서 대상 앱을 자동화 친화적으로 정리한 뒤, 별도의 자동화 프로젝트 디렉터리를 만들고 최소 실행 흐름을 구현했다.

## 3. 수행 환경

- 운영체제: Windows
- Python: 3.12.0
- GUI 프레임워크: PyQt6
- 자동화 방식: `pywinauto` with `backend="uia"`
- 설정 파일: `config.yaml`
- 시나리오 파일: `scenarios/basic_test.yaml`

## 4. 구현한 구조

아래 구조로 최소 POC를 구성했다.

- `main.py`: 설정과 시나리오를 읽고 전체 실행을 시작
- `core/action_executor.py`: step 단위 액션 실행
- `core/fail_safe.py`: 실패 시 스크린샷과 안전 종료 처리
- `core/logger.py`: 로그 파일 생성
- `core/screenshot.py`: 스크린샷 경로 생성
- `recognition/pywinauto_adapter.py`: 실제 윈도우 연결, 입력, 클릭, 검증 담당
- `scenarios/basic_test.yaml`: 최소 검증 시나리오
- `tools/check_environment.py`: 환경 점검

## 5. 대상 앱 수정 내용

자동화를 안정적으로 수행하기 위해 대상 PyQt 앱에 다음 내용을 반영했다.

- 창 제목을 `PyQt Input Panel`로 고정
- 주요 위젯에 `objectName` 부여
- 입력창 이름을 `key_input`, `value_input`, `value2_input`으로 부여
- 버튼 이름을 `save_button`, `load_button`, `reset_button`, `apply_button`으로 부여
- 상태 영역 이름을 `status_box`로 부여

이 작업은 `pywinauto`가 컨트롤을 더 안정적으로 찾도록 하기 위한 전처리 단계였다.

## 6. 시나리오 설계

최소 시나리오는 아래 순서로 설계했다.

1. 실행 중인 창에 연결하거나 없으면 앱 시작
2. `key_input`에 `sample-key` 입력
3. `value_input`에 `sample-value` 입력
4. `value2_input`에 `extra-value` 입력
5. `save_button` 클릭
6. `status_box` 안에 `Key: sample-key` 텍스트가 포함되는지 검증
7. 성공 스크린샷 저장
8. 안전 종료

## 7. 실제 문제와 해결 과정

### 7-1. `pywinauto` 미설치

초기 환경 점검에서 `pywinauto` 모듈이 없다는 결과가 확인되었다.
그래서 사용자 영역 기준으로 `pywinauto`를 설치해 해결했다.

### 7-2. `comtypes_cache` 권한 문제

`UIA` 백엔드 사용 시 `comtypes`가 캐시 파일을 생성하는 과정에서 권한 오류가 발생했다.
이를 해결하기 위해 다음 두 가지를 적용했다.

- 프로젝트 내부 `.cache/comtypes` 경로를 준비
- 사용자 `AppData\Roaming\Python\Python312\comtypes_cache` 폴더를 생성

이 과정으로 `pywinauto`의 UIA 초기화가 진행될 수 있게 만들었다.

### 7-3. 실행 중 창 연결 실패

2026-04-27 22:42:18에 첫 시도에서 기존 창 연결이 실패했고 `TimeoutError`가 기록되었다.
이후 연결 실패를 정상 분기로 처리하도록 수정해, 연결 실패 시 곧바로 앱 시작으로 넘어가도록 바꾸었다.

### 7-4. `WaitForInputIdle` 실패

2026-04-27 22:42:46에 `python "D:\app\fcm_desktop.py"` 실행 후 `WaitForInputIdle` 관련 오류가 발생했다.
원인은 Python 인터프리터를 통해 PyQt 앱을 띄운 상태에서 `wait_for_idle` 동작이 안정적으로 맞지 않았기 때문이다.
해결 방법으로 `Application.start(command, wait_for_idle=False)`를 적용했다.

### 7-5. 컨트롤 식별 실패

2026-04-27 22:43:25에 `key_input`을 직접 `auto_id`로 찾으려 했지만 실패했다.
이후 실행 중인 창의 UIA 트리를 덤프해서 실제 식별자를 조사했다.
확인 결과 PyQt 컨트롤은 단순한 `key_input`이 아니라 다음 형태로 노출되었다.

- `QApplication.ControlPanelWindow.central_widget.input_group.key_input`
- `QApplication.ControlPanelWindow.central_widget.input_group.value_input`
- `QApplication.ControlPanelWindow.central_widget.input_group.value2_input`

이 문제를 해결하기 위해 정확한 전체 문자열만 요구하지 않고, `auto_id.endswith(".{target}")` 방식의 후방 일치 탐색으로 어댑터를 수정했다.

### 7-6. 래퍼 중복 처리 오류

2026-04-27 22:45:23에 `EditWrapper object has no attribute wrapper_object` 오류가 발생했다.
원인은 이미 래핑된 컨트롤에 다시 `wrapper_object()`를 호출했기 때문이다.
해결을 위해 `_child()`가 반환한 컨트롤을 그대로 사용하도록 `set_text`, `click`, `verify_text`를 수정했다.

### 7-7. 실패 처리 개선

초기 실패 처리에서는 창 연결 자체가 안 된 상태에서 스크린샷을 찍으려다 예외가 연쇄 발생했다.
그래서 실패 스크린샷 저장 단계도 예외를 흡수하고, 마지막에는 항상 `safe_close()`로 넘어가도록 보완했다.

## 8. 최종 성공 결과

최종 실행은 2026-04-27 22:45:38부터 22:45:43 사이에 수행되었고, 로그 기준으로 전 단계가 성공했다.
핵심 성공 로그는 아래와 같다.

- `Step 1: launch_or_connect`
- `Starting target app: python "D:\app\fcm_desktop.py"`
- `Step 2: set_text`
- `Step 3: set_text`
- `Step 4: set_text`
- `Step 5: click`
- `Step 6: verify_text`
- `Verified text: Key: sample-key`
- `Step 7: screenshot`
- `Step 8: safe_close`
- `Scenario completed successfully.`

## 9. 생성된 산출물

- 성공 로그: `D:\app\fcm_gui_automation\reports\logs\automation.log`
- 실패 스크린샷 1: `20260427_224325_failure.png`
- 실패 스크린샷 2: `20260427_224523_failure.png`
- 성공 스크린샷: `20260427_224542_basic_test_success.png`

## 10. 결론

이번 POC는 `pywinauto`만으로도 PyQt 앱에 대해 다음 흐름이 가능함을 검증했다.

- 대상 창 실행 또는 연결
- 입력창 텍스트 입력
- 버튼 클릭
- 결과 텍스트 확인
- 스크린샷 저장
- 실패 시 안전 종료

이후 다음 단계에서는 시나리오 문법 확장, 더 많은 컨트롤 타입 지원, 복수 케이스 실행, 보고서 자동화, OCR 또는 이미지 매칭 보조 인식 추가로 확장할 수 있다.
