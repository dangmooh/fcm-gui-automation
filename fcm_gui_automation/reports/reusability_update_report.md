# 재사용성 개선 변경 보고서

작성일: 2026-04-27
대상 프로젝트: `D:\app\fcm_gui_automation`

## 1. 목적

이번 변경의 목적은 자동화 프로그램을 특정 샘플 앱 하나에만 묶어두지 않고, 사용자가 실행할 앱과 시나리오 파일을 직접 선택해서 재사용할 수 있게 만드는 것이었다.

추가로, 이후 변경되는 코드에 대해서는 이해를 돕기 위해 설명용 주석을 함께 남기는 방향으로 작업했다.

## 2. 변경 요약

이번에 반영한 핵심 변경은 아래와 같다.

- 실행 대상 앱 경로를 파일 선택 창으로 고를 수 있게 변경
- 시나리오 YAML 파일도 파일 선택 창으로 고를 수 있게 변경
- 명령행 인자로 앱 경로와 시나리오 경로를 직접 넘길 수 있게 유지
- `.py` 파일과 `.exe` 파일을 모두 실행할 수 있게 처리
- 새로 시작한 앱은 창 제목에 덜 의존하도록 `top_window()` 기반으로 보완
- 이번에 수정한 코드에는 짧은 설명 주석 추가

## 3. 수정한 파일

- `fcm_gui_automation/main.py`
- `fcm_gui_automation/recognition/pywinauto_adapter.py`

## 4. main.py 변경 내용

### 4-1. 인자 처리

기존에는 시나리오 파일이 `basic_test.yaml`로 고정되어 있었다.
이번에는 아래 두 인자를 받을 수 있게 유지 및 확장했다.

- `--app-path`
- `--scenario`

둘 다 생략하면 파일 선택 창을 띄운다.

### 4-2. 앱 선택 함수

`choose_app_path()`를 통해 `.py` 또는 `.exe` 파일을 선택할 수 있게 만들었다.

이 함수의 역할은 다음과 같다.

- 파일 선택 창 표시
- 초기 디렉터리 설정
- 선택된 경로 반환

### 4-3. 시나리오 선택 함수

새로 `choose_scenario_path()`를 추가했다.

이 함수의 역할은 다음과 같다.

- YAML 파일 선택 창 표시
- `scenarios` 폴더를 기본 시작 위치로 사용
- `.yaml`, `.yml` 파일만 우선적으로 고르게 유도

### 4-4. 경로 해석 함수

`resolve_app_path()`와 `resolve_scenario_path()`를 사용해 최종 경로를 확정하도록 구성했다.

이 단계에서 처리하는 내용은 다음과 같다.

- CLI 인자가 있으면 그 값을 우선 사용
- 없으면 파일 선택 창 사용
- 그래도 없으면 기본값 사용
- 파일 존재 여부 검증

### 4-5. 로그 추가

실행 시 아래 정보가 로그에 남도록 했다.

- 선택한 앱 경로
- 선택한 시나리오 경로

이 변경으로 나중에 어떤 조합으로 테스트했는지 추적하기 쉬워졌다.

## 5. pywinauto_adapter.py 변경 내용

### 5-1. 실행 파일 형식 분기

기존에는 `script_path`를 사실상 Python 스크립트처럼 취급하고 있었다.

이번에는 `_build_command()`에서 확장자를 기준으로 분기했다.

- `.py`이면 `python "script.py"` 형태로 실행
- `.exe`이면 실행 파일 경로를 직접 실행

이 변경으로 Python 앱뿐 아니라 일반 Windows 실행 파일도 같은 구조로 자동화할 수 있게 되었다.

### 5-2. 창 연결 로직 보완

기존에는 `title_re`에 기대어 창을 찾는 비중이 컸다.
하지만 사용자가 다른 앱을 선택하면 창 제목이 다를 수 있으므로, 새로 시작한 프로세스에 대해서는 `self.app.top_window()`를 사용하도록 바꿨다.

현재 동작은 아래와 같다.

- `title_re`가 있으면 기존 창 연결을 시도
- 연결 실패 시 앱을 새로 실행
- 새로 실행한 경우 `top_window()`로 최상위 창 확보
- 이미 연결한 경우에는 `title_re`로 창 객체 확보

이 구조는 범용성을 높이는 데 의미가 있다.

## 6. 주석 추가 내용

사용자 요청에 따라 이번에 수정한 부분에는 짧은 설명 주석을 넣었다.

대표적으로 아래 함수들에 의도를 설명하는 주석이 추가되었다.

- `choose_app_path()`
- `choose_scenario_path()`
- `resolve_scenario_path()`

이 주석들은 "왜 이 함수가 존재하는지"를 빠르게 파악하게 돕는 목적이다.

## 7. 사용 방법

### 7-1. 파일 선택 창으로 실행

```powershell
python fcm_gui_automation\main.py
```

실행하면 아래 순서로 파일을 고를 수 있다.

1. 실행할 앱 선택
2. 실행할 시나리오 YAML 선택

### 7-2. 경로를 직접 지정해서 실행

```powershell
python fcm_gui_automation\main.py --app-path d:\app\fcm_desktop.py --scenario d:\app\fcm_gui_automation\scenarios\basic_test.yaml
```

이 방식은 반복 실행이나 배치 실행에 더 적합하다.

## 8. 검증 결과

이번 변경 후 아래 조합으로 실제 실행 검증을 수행했다.

- 앱 경로: `D:\app\fcm_desktop.py`
- 시나리오 경로: `D:\app\fcm_gui_automation\scenarios\basic_test.yaml`

로그 기준으로 아래 흐름이 성공했다.

- `Selected target app: D:\app\fcm_desktop.py`
- `Selected scenario: D:\app\fcm_gui_automation\scenarios\basic_test.yaml`
- `Step 1: launch_or_connect`
- `Step 2: set_text`
- `Step 3: set_text`
- `Step 4: set_text`
- `Step 5: click`
- `Step 6: verify_text`
- `Step 7: screenshot`
- `Step 8: safe_close`
- `Scenario completed successfully.`

검증 시 생성된 성공 스크린샷 예시는 다음과 같다.

- `20260427_232041_basic_test_success.png`
- `20260427_232131_basic_test_success.png`

## 9. 기대 효과

이번 변경으로 얻은 가장 큰 효과는 다음과 같다.

- 다른 앱에도 같은 자동화 엔진을 재사용하기 쉬워짐
- 시나리오를 여러 개 두고 골라 실행하기 쉬워짐
- 명령행 실행과 GUI 선택 실행을 둘 다 지원함
- 테스트 실행 이력을 로그로 남기기 쉬워짐

## 10. 다음 추천 작업

현재 상태에서 이어서 하면 좋은 작업은 아래와 같다.

1. 최근 사용한 앱/시나리오 경로 기억하기
2. `main.py`에서 시나리오 목록을 선택하는 간단한 메뉴 제공
3. 새로운 action 추가를 위한 템플릿 함수 만들기
4. 컨트롤 식별자 탐색 도구를 별도 유틸로 제공
5. YAML schema 검증 추가

## 11. 결론

이번 수정으로 자동화 프로그램은 "샘플 프로젝트 전용 스크립트"에서 "여러 앱과 여러 시나리오에 재사용 가능한 실행기"에 더 가까워졌다.

특히 `main.py`의 파일 선택 기능과 `pywinauto_adapter.py`의 `.py/.exe` 실행 분기는 앞으로 확장성을 높이는 핵심 변경이라고 볼 수 있다.
