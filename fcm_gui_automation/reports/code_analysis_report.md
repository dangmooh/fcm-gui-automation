# 시나리오/액션 확장 및 Python 파일 분석 보고서

작성일: 2026-04-27
대상 프로젝트: `D:\app\fcm_gui_automation`
대상 앱: `D:\app\fcm_desktop.py`

## 1. 문서 목적

이 문서는 현재 자동화 프로젝트에서 사용자가 직접 동작을 바꾸는 방법과, 새로운 `action`을 추가하는 방법, 그리고 각 Python 파일이 맡고 있는 역할을 분석한 문서다.

특히 아래 질문에 답하도록 구성했다.

- 시나리오를 바꾸려면 어디를 수정해야 하는가
- 새로운 action을 추가하려면 어떤 파일을 고쳐야 하는가
- 각 Python 파일은 어떤 책임을 가지는가
- 앞으로 확장할 때 어디에 코드를 넣는 것이 맞는가

## 2. 전체 동작 구조

현재 프로젝트는 크게 네 층으로 나뉜다.

- 대상 GUI 앱: `fcm_desktop.py`
- 실행 진입점: `fcm_gui_automation/main.py`
- 실행 코어: `core/*.py`
- 인식/제어 계층: `recognition/*.py`

전체 실행 흐름은 아래와 같다.

1. `main.py`가 `config.yaml`과 `basic_test.yaml`을 읽는다.
2. `ActionExecutor`가 시나리오의 `steps`를 위에서 아래로 순서대로 처리한다.
3. 각 step의 `action` 이름에 따라 `PyWinAutoAdapter` 메서드가 호출된다.
4. 어댑터가 실제 PyQt 창에 연결하고 입력, 클릭, 텍스트 검증을 수행한다.
5. 실패하면 `FailSafeManager`가 스크린샷과 안전 종료를 수행한다.

## 3. 사용자가 가장 자주 수정할 파일

실제로 사용자가 자주 손대게 되는 파일은 아래 세 개다.

- `fcm_gui_automation/scenarios/basic_test.yaml`
- `fcm_gui_automation/config.yaml`
- `fcm_desktop.py`

### 3-1. `basic_test.yaml`

이 파일은 "무슨 행동을 어떤 순서로 할 것인가"를 정의한다.
즉, 자동화의 시나리오 본문이다.

현재 예시는 아래 순서를 가진다.

- 앱 실행 또는 연결
- key 입력
- value 입력
- value2 입력
- save 버튼 클릭
- 상태창에 특정 텍스트가 있는지 검증
- 스크린샷 저장
- 종료

이 파일에서 바꿀 수 있는 대표 요소는 다음과 같다.

- `action`: 어떤 동작을 실행할지
- `target`: 어떤 입력창/버튼/결과창을 대상으로 할지
- `value`: 입력값 또는 검증 문자열

### 3-2. `config.yaml`

이 파일은 자동화 엔진의 실행 조건을 관리한다.

- `backend`: 현재는 `uia`
- `title_re`: 연결할 창 제목 정규식
- `python_command`: 앱 실행에 사용할 Python 명령
- `script_path`: 대상 앱 경로
- `start_timeout`, `focus_timeout`: 연결 대기 시간

즉, 시나리오가 "무엇을 할지"라면, `config.yaml`은 "어떤 앱에 어떤 방식으로 붙을지"를 정한다.

### 3-3. `fcm_desktop.py`

이 파일은 실제 자동화 대상 앱이다.
버튼 이름과 입력창 이름이 여기서 결정되기 때문에, UI 구조가 바뀌면 시나리오와 어댑터도 함께 영향을 받는다.

## 4. 새로운 action을 추가하는 방법

새 action을 추가할 때는 보통 세 파일을 함께 본다.

- `core/action_executor.py`
- `recognition/base.py`
- `recognition/pywinauto_adapter.py`

추가 절차는 아래 순서가 가장 안전하다.

1. YAML에서 사용할 action 이름을 정한다.
2. `ActionExecutor.run()`에 해당 action 분기를 추가한다.
3. `RecognitionAdapter`에 메서드 시그니처를 추가한다.
4. `PyWinAutoAdapter`에 실제 구현을 넣는다.
5. 시나리오 파일에서 새 action을 사용한다.

예를 들어 `wait` action을 만든다고 가정하면 구조는 다음과 같다.

- `action_executor.py`에서 `elif action == "wait": self.adapter.wait(step["value"])`
- `base.py`에 `wait(self, seconds: float)` 추가
- `pywinauto_adapter.py`에 `time.sleep(float(seconds))` 구현
- YAML에서 `action: "wait"` 사용

즉, 실행기 파일은 "분기", 어댑터 파일은 "실제 행동", 시나리오 파일은 "사용"을 담당한다.

## 5. 현재 지원되는 action 분석

현재 `ActionExecutor` 기준으로 지원되는 action은 여섯 개다.

- `launch_or_connect`
- `set_text`
- `click`
- `verify_text`
- `screenshot`
- `safe_close`

각 action의 의미는 다음과 같다.

- `launch_or_connect`: 이미 열린 창이 있으면 연결하고, 없으면 실행
- `set_text`: 대상 입력창에 문자열 입력
- `click`: 대상 버튼 클릭
- `verify_text`: 결과 영역에 특정 문자열이 있는지 확인
- `screenshot`: 현재 창 스크린샷 저장
- `safe_close`: 창 종료 또는 프로세스 종료

이 구조의 장점은 단순하다는 점이다.
반면 액션 종류가 늘어나면 현재의 `if/elif` 구조는 점점 길어지므로, 이후에는 액션 테이블 방식으로 바꾸는 것도 고려할 수 있다.

## 6. 대상 앱에서 사용할 수 있는 target 이름

현재 `fcm_desktop.py`에서 자동화 타깃으로 쓰는 주요 이름은 아래와 같다.

- `key_input`
- `value_input`
- `value2_input`
- `save_button`
- `load_button`
- `reset_button`
- `apply_button`
- `status_box`

시나리오에서 `target` 값을 쓸 때는 이 이름을 기준으로 적는다.

## 7. Python 파일별 분석

### 7-1. `fcm_desktop.py`

역할:
- 자동화 대상이 되는 PyQt 데스크톱 앱

핵심 구성:
- `ControlPanelWindow` 클래스
- `_build_ui()`에서 입력창, 버튼, 상태창 생성
- `handle_action()`에서 버튼별 상태 텍스트 반영

중요 포인트:
- `setObjectName()`으로 각 위젯에 안정적인 이름을 부여했다.
- 이 이름이 자동화 시나리오의 `target` 설계 기준이 된다.

확장 포인트:
- 새로운 버튼/입력창 추가
- 버튼 클릭 시 실제 비즈니스 로직 연결
- 상태창 대신 테이블/로그 패널 확장

주의점:
- UI 구조를 바꾸면 자동화 `target`도 함께 재검토해야 한다.

### 7-2. `fcm_gui_automation/main.py`

역할:
- 자동화 실행의 진입점

핵심 구성:
- `config.yaml` 로딩
- `basic_test.yaml` 로딩
- `PyWinAutoAdapter`, `FailSafeManager`, `ActionExecutor` 조립
- 성공/실패 종료 코드 반환

장점:
- 전체 의존성을 한곳에서 연결해 흐름을 이해하기 쉽다.

개선 포인트:
- 현재는 시나리오 파일이 `basic_test.yaml`로 고정되어 있다.
- 나중에는 명령행 인자로 시나리오 파일을 받도록 확장하는 것이 좋다.

### 7-3. `core/action_executor.py`

역할:
- 시나리오 step를 순서대로 읽고 action을 실행하는 오케스트레이터

핵심 구성:
- `run(scenario)`
- `scenario["steps"]` 반복
- action 이름에 따른 분기 처리

장점:
- 시나리오가 어떻게 실행되는지 한 파일에서 명확히 보인다.

개선 포인트:
- action이 늘어나면 `if/elif`가 커진다.
- 추후에는 딕셔너리 디스패치 구조로 리팩터링할 수 있다.

### 7-4. `core/fail_safe.py`

역할:
- 실패 시 스크린샷 저장과 안전 종료를 담당

핵심 구성:
- `handle_failure(error)`
- `safe_close()`

장점:
- 실패 처리 로직이 분리되어 있어 `main.py`가 단순하다.

개선 포인트:
- 실패 유형별로 다른 후속 조치를 넣고 싶다면 여기서 분기할 수 있다.
- 예를 들어 재시도, 팝업 탐지, 추가 로그 수집 등을 추가할 수 있다.

### 7-5. `core/logger.py`

역할:
- 로그 파일과 콘솔 로그를 동시에 구성

핵심 구성:
- `build_logger(log_dir)`

장점:
- 실행 이력을 `automation.log`에 남기므로 원인 추적이 쉽다.

개선 포인트:
- 로그 레벨 분리
- 파일 회전
- 시나리오별 로그 파일명 분기

### 7-6. `core/scenario_loader.py`

역할:
- YAML 파일을 읽어 Python dict로 변환

핵심 구성:
- `_load_yaml(path)`
- `load_config(path)`
- `load_scenario(path)`

장점:
- 설정과 시나리오 로딩 로직이 재사용 가능하다.

개선 포인트:
- 현재는 구조 검증이 단순하다.
- 앞으로는 schema 검증을 넣어 잘못된 YAML을 더 빨리 잡을 수 있다.

### 7-7. `core/screenshot.py`

역할:
- 스크린샷 파일 경로를 일관되게 생성

핵심 구성:
- `build_screenshot_path(base_dir, name)`

장점:
- 시간 기반 파일명으로 덮어쓰기 충돌을 줄인다.

개선 포인트:
- 시나리오 이름, step 번호 등을 파일명에 포함할 수 있다.

### 7-8. `recognition/base.py`

역할:
- 인식/제어 어댑터의 공통 인터페이스 역할

핵심 구성:
- `launch_or_connect`
- `set_text`
- `click`
- `verify_text`
- `capture_window`
- `close`

장점:
- 나중에 OpenCV나 OCR 기반 어댑터를 붙일 때 기준점이 된다.

개선 포인트:
- 새 action이 늘어나면 이 추상 인터페이스도 함께 업데이트해야 한다.

### 7-9. `recognition/pywinauto_adapter.py`

역할:
- 실제 Windows UI 제어를 담당하는 핵심 구현체

핵심 구성:
- 앱 실행/연결
- 자식 컨트롤 탐색
- 텍스트 입력
- 버튼 클릭
- 상태 검증
- 창 캡처
- 종료

중요 설계 포인트:
- `connect` 실패 시 `start`로 전환
- `wait_for_idle=False`로 PyQt 실행 안정성 확보
- `auto_id.endswith(".{target}")`로 PyQt UIA 식별자 대응

장점:
- 현재 프로젝트에서 가장 실질적인 자동화 로직이 집중된 파일이다.

개선 포인트:
- `double_click`, `clear_text`, `wait`, `exists`, `verify_empty` 같은 메서드를 추가하기 좋다.
- 컨트롤 탐색 결과를 캐시하면 반복 실행 성능이 좋아질 수 있다.

### 7-10. `recognition/opencv_adapter.py`

역할:
- 향후 이미지 매칭 인식용 확장 지점

현재 상태:
- 아직 `NotImplementedError`

의미:
- 지금은 사용되지 않지만, 버튼 이미지 탐지나 비표준 UI 자동화를 도입할 때 들어갈 자리다.

### 7-11. `recognition/ocr_adapter.py`

역할:
- 향후 OCR 기반 텍스트 인식 확장 지점

현재 상태:
- 아직 `NotImplementedError`

의미:
- 상태창 텍스트를 컨트롤 속성 대신 화면 기준으로 검증해야 할 때 사용할 수 있다.

### 7-12. `tools/check_environment.py`

역할:
- 실행 전 필수 모듈과 경로 환경을 점검

장점:
- 설치 누락을 본 실행 전에 확인할 수 있다.

개선 포인트:
- Python 버전 체크
- 폰트/권한/UIA 접근 가능 여부 체크
- 대상 앱 실행 가능 여부 체크

### 7-13. `tools/collect_templates.py`

역할:
- 이미지 매칭 단계에서 템플릿 수집용 자리

현재 상태:
- 안내 메시지 출력만 수행

의미:
- OpenCV 단계로 확장할 경우 실제 수집 기능이 들어갈 수 있다.

### 7-14. `tools/generate_pdf_report.py`

역할:
- Markdown 문서를 PDF로 렌더링하는 유틸리티

현재 기능:
- 텍스트 보고서 렌더링
- 선택적 이미지 페이지 추가
- 기본 보고서와 별도 PDF 출력

의미:
- 자동화 결과 보고서나 코드 분석 보고서를 반복 생성할 수 있는 도구다.

개선 포인트:
- 목차
- 페이지 번호
- 코드 블록 전용 서식
- 명령행 옵션 확장

## 8. 지금 구조에서 새 기능을 넣을 위치

기능별로 수정 위치는 아래처럼 보면 된다.

- 새 버튼/새 입력창 추가: `fcm_desktop.py`
- 새 시나리오 추가: `scenarios/*.yaml`
- 새 action 이름 추가: `core/action_executor.py`
- 새 action 실제 구현: `recognition/pywinauto_adapter.py`
- 공통 인터페이스 선언: `recognition/base.py`
- 실패 처리 강화: `core/fail_safe.py`
- 새 인식 방식 도입: `recognition/opencv_adapter.py`, `recognition/ocr_adapter.py`

## 9. 추천 확장 순서

현재 구조에서 가장 실용적인 다음 단계는 아래 순서다.

1. `main.py`가 시나리오 파일명을 인자로 받도록 수정
2. `wait`, `clear_text`, `verify_empty`, `double_click` action 추가
3. YAML schema 검증 추가
4. 결과 리포트 자동 생성 연결
5. OpenCV/OCR 보조 인식 추가

## 10. 결론

현재 프로젝트는 "작지만 확장 가능한 자동화 프레임" 형태다.
사용자는 우선 `basic_test.yaml`만 바꿔도 동작 순서를 조정할 수 있고, 조금 더 확장하려면 `action_executor.py`와 `pywinauto_adapter.py`를 함께 수정해 새로운 action을 추가하면 된다.

가장 중요한 파일은 세 개다.

- `fcm_desktop.py`
- `core/action_executor.py`
- `recognition/pywinauto_adapter.py`

이 세 파일을 이해하면 현재 시스템의 대부분을 이해했다고 봐도 된다.
