# Python 파일 핵심 설명 보고서

작성일: 2026-04-28
대상 프로젝트: `D:\app\fcm_gui_automation`

## 1. 문서 목적

이 문서는 Python 문법이 익숙하지 않은 사람을 위해, 현재 프로젝트의 각 Python 파일이 무엇을 하는지와 그 안에서 자주 나오는 핵심 문법이 무엇을 의미하는지를 쉽게 설명하기 위한 보고서다.

이번 문서는 아래 두 질문에 답하는 방식으로 구성했다.

- 이 파일은 왜 존재하는가
- 이 파일 안에 있는 Python 문법은 무슨 뜻인가

코드의 세세한 구현보다, "이 문법을 이렇게 읽으면 된다"는 관점으로 설명한다.

## 2. 먼저 알아두면 좋은 Python 기본 문법

프로젝트를 읽을 때 자주 보이는 Python 문법은 아래 정도다.

### 2-1. `import`

예:

- `import os`
- `from pathlib import Path`

의미:
- 다른 모듈의 기능을 가져와서 사용하겠다는 뜻이다.

읽는 방법:
- `import os`: `os`라는 모듈 전체를 가져온다.
- `from pathlib import Path`: `pathlib` 안에 있는 `Path`만 꺼내서 쓴다.

### 2-2. 함수 정의 `def`

예:

- `def main() -> int:`

의미:
- `main`이라는 함수를 만든다는 뜻이다.

읽는 방법:
- `()` 안은 입력값
- `-> int`는 이 함수가 정수를 돌려준다는 타입 힌트
- 끝의 `:` 아래 들여쓴 부분이 함수 본문

### 2-3. 클래스 정의 `class`

예:

- `class ActionExecutor:`
- `class PyWinAutoAdapter(RecognitionAdapter):`

의미:
- 관련 있는 데이터와 기능을 하나로 묶는 구조다.

읽는 방법:
- `class 이름:` 형태로 시작
- `(RecognitionAdapter)`처럼 괄호가 있으면 다른 클래스를 상속받는다는 뜻

### 2-4. 생성자 `__init__`

예:

- `def __init__(self, adapter, logger, fail_safe) -> None:`

의미:
- 클래스 객체가 처음 만들어질 때 실행되는 초기 설정 함수다.

읽는 방법:
- `self`는 "이 객체 자기 자신"을 뜻한다.
- `self.adapter = adapter`는 받은 값을 객체 안에 저장하는 문장이다.

### 2-5. 조건문 `if / elif / else`

예:

- `if action == "click":`
- `elif action == "verify_text":`
- `else:`

의미:
- 조건에 따라 다른 동작을 하게 만든다.

### 2-6. 반복문 `for`

예:

- `for index, step in enumerate(steps, start=1):`

의미:
- `steps` 안의 내용을 하나씩 꺼내 반복한다.

읽는 방법:
- `enumerate`는 순번과 값을 같이 꺼내는 함수다.
- `start=1`은 번호를 1부터 시작하겠다는 뜻이다.

### 2-7. 예외 처리 `try / except`

예:

- `try:`
- `except Exception as error:`

의미:
- 실행 중 에러가 날 수 있는 구간을 감싸고, 실패했을 때 다른 동작을 하게 만든다.

### 2-8. 딕셔너리와 리스트

예:

- `config["app"]`
- `scenario.get("steps", [])`

의미:
- 딕셔너리는 `키: 값` 구조의 데이터다.
- 리스트는 여러 값을 순서대로 담는 구조다.

## 3. 프로젝트 전체를 한 줄로 설명하면

이 프로젝트는 "YAML 시나리오를 읽어서 Windows GUI 프로그램을 자동으로 조작하는 Python 자동화 실행기"다.

즉, 사람 대신 Python이 아래 행동을 한다.

- 프로그램 실행
- 버튼 클릭
- 입력창에 값 넣기
- 결과 텍스트 확인
- 화면 캡처
- 종료

## 4. 파일별 핵심 설명

## 4-1. `fcm_gui_automation/main.py`

### 이 파일의 역할

이 파일은 프로그램의 시작점이다.
사용자가 `python main.py`처럼 실행하면 가장 먼저 이 파일이 돌아간다.

### 여기서 중요한 문법

#### `argparse`

이 파일은 `argparse`를 써서 명령행 옵션을 받는다.

예:

- `--app-path`
- `--scenario`

이 뜻은 사용자가 실행할 때 옵션을 붙일 수 있다는 말이다.

#### `Path`

`Path`는 파일 경로를 안전하게 다루기 위한 Python 도구다.

예:

- `Path(__file__).resolve().parent`

읽는 방법:
- `__file__`: 지금 이 파일 자신의 경로
- `.resolve()`: 절대 경로로 바꿈
- `.parent`: 상위 폴더

즉, "현재 파일이 있는 폴더"를 구하는 코드다.

#### 함수 분리

이 파일은 기능을 여러 함수로 나눴다.

- `parse_args()`
- `choose_app_path()`
- `choose_scenario_path()`
- `resolve_app_path()`
- `resolve_scenario_path()`
- `main()`

이렇게 나누는 이유는 한 함수가 한 가지 일만 하게 만들어 읽기 쉽게 하려는 것이다.

### 이 파일을 읽는 핵심 포인트

- `main()`이 전체 흐름을 시작한다.
- `parse_args()`는 사용자가 준 실행 옵션을 읽는다.
- `resolve_*` 함수는 실제 사용할 파일 경로를 정한다.
- 마지막에는 `ActionExecutor`가 시나리오를 실행한다.

## 4-2. `core/action_executor.py`

### 이 파일의 역할

시나리오 YAML에 적힌 action을 순서대로 실행하는 파일이다.

쉽게 말하면:
- "무엇을 해야 하는지 적힌 종이"를 한 줄씩 읽고 실행하는 관리자

### 여기서 중요한 문법

#### 클래스

`class ActionExecutor:`는 실행 담당 객체를 만든다는 뜻이다.

#### 생성자

`__init__` 안에서 `adapter`, `logger`, `fail_safe`를 저장한다.

이 뜻은:
- UI 조작 담당
- 로그 담당
- 실패 처리 담당

이 세 가지 도구를 ActionExecutor가 계속 쓴다는 말이다.

#### `scenario.get("steps", [])`

이 문장은 딕셔너리에서 `steps`를 꺼내되, 없으면 빈 리스트를 쓰겠다는 뜻이다.

#### `raise ValueError(...)`

이건 "이 상태는 잘못됐다"라고 강제로 에러를 만드는 문법이다.

예:
- 시나리오에 step가 하나도 없으면 실행할 것이 없으므로 에러를 낸다.

### 핵심 포인트

이 파일은 "무슨 action이 들어오면 어떤 메서드를 호출할지"를 정한다.

예:
- `set_text`면 `adapter.set_text(...)`
- `click`이면 `adapter.click(...)`

따라서 새로운 action을 추가할 때 가장 먼저 손대는 파일 중 하나다.

## 4-3. `core/fail_safe.py`

### 이 파일의 역할

실패했을 때 프로그램이 어떻게 마무리될지 정하는 파일이다.

### 중요한 문법

#### `try / except / finally`

이 파일에는 이런 흐름이 들어 있다.

- 먼저 스크린샷 저장 시도
- 스크린샷도 실패하면 경고 로그
- 마지막에는 어쨌든 종료 시도

즉, 실패 상황에서도 프로그램이 덜 어지럽게 끝나도록 만든다.

### 핵심 포인트

이 파일은 "실패했을 때의 안전장치"다.
자동화는 실패 가능성이 높기 때문에 이런 파일이 매우 중요하다.

## 4-4. `core/logger.py`

### 이 파일의 역할

로그를 남기는 설정 파일이다.

### 중요한 문법

#### `logging`

Python의 표준 로그 도구다.

예:
- `logger.info(...)`
- `logger.warning(...)`
- `logger.error(...)`

뜻:
- `info`: 일반 정보
- `warning`: 경고
- `error`: 오류

#### 핸들러

이 파일은 두 군데에 로그를 남긴다.

- 콘솔 화면
- `automation.log` 파일

즉, 화면으로도 보고 나중에 파일로도 다시 볼 수 있게 만든다.

## 4-5. `core/scenario_loader.py`

### 이 파일의 역할

YAML 파일을 읽어서 Python 데이터로 바꾸는 파일이다.

### 중요한 문법

#### `with path.open(...) as file:`

이 문법은 파일을 안전하게 열고 자동으로 닫는 문법이다.

읽는 방법:
- `with` 블록 안에서 파일 사용
- 블록이 끝나면 자동 정리

#### `yaml.safe_load`

YAML 문서를 Python 딕셔너리/리스트로 바꿔준다.

### 핵심 포인트

이 파일 덕분에 시나리오를 Python 코드가 아니라 YAML로 관리할 수 있다.

## 4-6. `core/screenshot.py`

### 이 파일의 역할

스크린샷 저장 파일명을 만드는 유틸리티다.

### 중요한 문법

#### `datetime.now().strftime(...)`

현재 시간을 문자열로 바꾸는 문법이다.

예:
- `20260428_103000` 같은 형태

이걸 파일명 앞에 붙이면 스크린샷이 덮어써지지 않는다.

## 4-7. `recognition/base.py`

### 이 파일의 역할

어댑터가 어떤 메서드를 가져야 하는지 약속처럼 정의하는 파일이다.

### 중요한 문법

#### `raise NotImplementedError`

이건 "이 함수는 아직 실제 구현이 없다"는 뜻이다.

즉, base 파일은 실제 동작보다 인터페이스 역할을 한다.

### 핵심 포인트

나중에 `pywinauto` 말고 `opencv`나 `ocr` 방식으로 바꿔도, 기본 메서드 이름을 맞추면 같은 구조를 유지할 수 있다.

## 4-8. `recognition/pywinauto_adapter.py`

### 이 파일의 역할

실제로 Windows GUI를 조작하는 가장 중요한 파일이다.

### 중요한 문법

#### 상속

`class PyWinAutoAdapter(RecognitionAdapter):`

읽는 방법:
- `RecognitionAdapter`의 약속을 따르는 클래스라는 뜻

#### `@property`

예:
- `@property`
- `def app_config(self) -> dict:`

뜻:
- 함수처럼 만들었지만 사용할 때는 속성처럼 쓸 수 있게 해준다.

즉:
- `self.app_config()`가 아니라
- `self.app_config`처럼 사용

#### 예외 여러 개 묶기

예:

- `except (ElementNotFoundError, TimeoutError):`

뜻:
- 둘 중 하나의 에러가 나도 같은 방식으로 처리하겠다는 말이다.

#### 문자열 포매팅

예:

- `f'{python_command} "{script_path}"'`

이건 f-string이다.
문자열 안에 변수 값을 쉽게 넣는 Python 문법이다.

### 이 파일이 실제로 하는 일

- 기존 창 연결 시도
- 없으면 앱 실행
- 최상위 창 확보
- 컨트롤 찾기
- 입력값 넣기
- 버튼 클릭
- 텍스트 검증
- 스크린샷 저장
- 창 닫기

### `_child()` 함수가 중요한 이유

이 함수는 시나리오의 `target` 이름을 실제 UI 컨트롤로 바꿔주는 역할을 한다.
즉, `key_input` 같은 이름이 실제 윈도우 객체로 연결된다.

## 4-9. `recognition/opencv_adapter.py`

### 이 파일의 역할

아직 실제 구현은 없지만, 나중에 이미지 매칭 자동화를 넣을 자리다.

### 중요한 문법

`NotImplementedError`가 있다는 것은:
- 구조는 미리 잡아뒀지만 기능은 아직 만들지 않았다는 뜻이다.

## 4-10. `recognition/ocr_adapter.py`

### 이 파일의 역할

향후 OCR 기반 텍스트 인식을 넣기 위한 자리다.

현재는 비어 있지만, 설계상 확장 포인트라는 의미가 있다.

## 4-11. `tools/check_environment.py`

### 이 파일의 역할

프로그램 실행 전에 필요한 라이브러리가 설치됐는지 확인한다.

### 중요한 문법

#### `importlib.import_module(...)`

문자열 이름으로 모듈을 가져와 보는 문법이다.

이걸 이용하면:
- `pywinauto`
- `yaml`
- `PIL`

같은 모듈이 실제로 설치돼 있는지 점검할 수 있다.

## 4-12. `tools/collect_templates.py`

### 이 파일의 역할

지금은 안내 메시지만 출력하는 간단한 파일이다.

하지만 구조상 나중에 템플릿 이미지 수집 기능을 넣기 위한 자리다.

## 4-13. `tools/generate_pdf_report.py`

### 이 파일의 역할

Markdown 보고서를 PDF로 바꾸는 유틸리티다.

### 중요한 문법

#### `argparse`

이 파일도 명령행 인자를 받을 수 있다.

#### 이미지 처리

`Pillow`를 이용해:
- 빈 페이지 생성
- 글자 쓰기
- 이미지 붙이기
- PDF 저장

를 한다.

즉, 이 파일은 "문서를 그림처럼 그려서 PDF로 만드는 도구"라고 생각하면 이해하기 쉽다.

## 4-14. `fcm_desktop.py`

### 이 파일의 역할

자동화 대상이 되는 샘플 GUI 프로그램이다.

### 중요한 문법

#### PyQt 클래스 사용

예:

- `QMainWindow`
- `QPushButton`
- `QLineEdit`
- `QTextEdit`

이런 클래스는 각각:
- 창
- 버튼
- 한 줄 입력창
- 여러 줄 텍스트창

을 의미한다.

#### 이벤트 연결

예:

- `save_button.clicked.connect(...)`

뜻:
- 버튼이 눌리면 어떤 함수를 실행하겠다는 연결이다.

#### `self`

GUI 코드에서는 `self.key_input`, `self.status_box`처럼 자주 보인다.
이건 "이 창이 가지고 있는 부품" 정도로 이해하면 된다.

### 핵심 포인트

이 파일은 자동화 엔진이 조작할 대상 앱이므로, 버튼 이름과 입력창 이름이 매우 중요하다.

## 5. 초보자가 이 프로젝트를 읽을 때 추천 순서

Python 문법이 익숙하지 않다면 아래 순서로 읽는 것이 가장 이해하기 쉽다.

1. `fcm_desktop.py`
2. `fcm_gui_automation/main.py`
3. `core/action_executor.py`
4. `recognition/pywinauto_adapter.py`
5. `core/fail_safe.py`
6. `core/logger.py`
7. `core/scenario_loader.py`
8. 나머지 tools

이 순서가 좋은 이유는 다음과 같다.

- 먼저 "대상 앱"이 무엇인지 이해
- 다음에 "전체 실행 흐름" 이해
- 그 다음 "시나리오 해석" 이해
- 마지막에 "세부 유틸" 이해

## 6. 이 프로젝트에서 꼭 이해해야 하는 핵심 개념 5개

초보자 기준으로 정말 중요한 것은 아래 다섯 가지다.

1. 함수 `def`
2. 클래스와 `self`
3. 조건문 `if / elif / else`
4. 예외 처리 `try / except`
5. 딕셔너리와 리스트

이 다섯 가지만 익숙해져도 현재 프로젝트 구조는 훨씬 쉽게 읽힌다.

## 7. 결론

이 프로젝트는 처음 보면 파일이 많아 보여도, 실제로는 역할이 꽤 분명하게 나뉘어 있다.

- `main.py`: 시작점
- `core/`: 흐름 관리
- `recognition/`: 실제 UI 조작
- `tools/`: 보조 기능
- `fcm_desktop.py`: 자동화 대상 샘플 앱

Python 문법을 잘 모르는 상태에서는 각 줄을 다 해석하려고 하기보다, 먼저 "이 파일이 맡은 역할"과 "여기서 자주 쓰는 문법 1~2개"만 잡는 방식으로 읽는 것이 가장 좋다.
