# 다중 시나리오 실행 리팩터링 보고서

작성일: 2026-04-28
대상 프로젝트: `D:\app\fcm_gui_automation`

## 1. 변경 목적

이번 변경의 목적은 기존 자동화 프로그램이 하나의 시나리오 YAML만 실행하던 구조를, 사용자가 선택한 여러 시나리오를 순서대로 실행할 수 있는 구조로 확장하는 것이었다.

기존 구조에서는 `main.py`가 한 개의 시나리오 파일만 읽고 `executor.run(scenario)`를 한 번 호출했다.
이 방식은 단순하지만, 실제 자동화 운영에서는 여러 테스트 케이스를 연속으로 실행하기 어렵다.

따라서 이번 리팩터링에서는 아래 목표를 반영했다.

- `--scenario` 옵션을 여러 번 받을 수 있게 변경
- 파일 선택 창에서 여러 YAML 파일을 한 번에 선택할 수 있게 변경
- 선택된 시나리오들을 순서대로 실행
- 각 시나리오의 진행 상황을 로그에 남김
- 전체 배치 실행 성공/실패를 명확히 구분

## 2. 수정된 파일

이번에 직접 수정한 파일은 아래 두 개다.

- `fcm_gui_automation/main.py`
- `fcm_gui_automation/core/action_executor.py`

## 3. main.py 주요 변경 내용

### 3-1. `--scenario` 옵션 변경

기존에는 `--scenario`가 하나의 문자열만 받았다.
이번에는 `argparse`의 `action="append"`를 사용해 같은 옵션을 여러 번 받을 수 있게 바꿨다.

예:

```powershell
python fcm_gui_automation\main.py --app-path d:\app\fcm_desktop.py --scenario scenario1.yaml --scenario scenario2.yaml
```

이렇게 실행하면 `args.scenario`에는 시나리오 경로 목록이 들어간다.

### 3-2. 시나리오 파일 선택 함수 변경

기존 함수:

- `choose_scenario_path()`

변경 후 함수:

- `choose_scenario_paths()`

기존 함수는 `filedialog.askopenfilename()`을 사용해 파일 하나만 선택했다.
변경 후에는 `filedialog.askopenfilenames()`를 사용해 여러 YAML 파일을 선택할 수 있게 했다.

이 함수는 선택된 파일 경로들을 `list[str]` 형태로 반환한다.

### 3-3. 시나리오 경로 해석 함수 변경

기존 함수:

- `resolve_scenario_path() -> Path`

변경 후 함수:

- `resolve_scenario_paths() -> list[Path]`

변경된 함수는 CLI로 전달된 시나리오 목록 또는 파일 선택 창에서 선택한 목록을 받아, 모두 절대 경로로 변환한다.

또한 각 시나리오 파일이 실제로 존재하는지 검사한다.
존재하지 않는 파일이 있으면 `FileNotFoundError`를 발생시킨다.

### 3-4. main 실행 흐름 변경

기존 실행 흐름:

```text
시나리오 1개 로드
executor.run(scenario) 1회 실행
성공 로그 출력
```

변경 후 실행 흐름:

```text
시나리오 경로 목록 로드
각 시나리오를 순서대로 반복
각 시나리오를 load_scenario()로 로드
executor.run(scenario) 실행
모든 시나리오가 끝나면 전체 성공 로그 출력
```

변경된 핵심 구조는 아래와 같다.

```python
for index, scenario_path in enumerate(scenario_paths, start=1):
    scenario = load_scenario(scenario_path)
    scenario_name = scenario.get("name", scenario_path.stem)
    logger.info(
        "Running scenario %s/%s: %s (%s)",
        index,
        len(scenario_paths),
        scenario_name,
        scenario_path,
    )
    executor.run(scenario)
```

이 구조 덕분에 각 시나리오가 몇 번째로 실행되는지 로그에서 확인할 수 있다.

## 4. action_executor.py 변경 내용

이번 작업의 중심은 다중 시나리오 실행이지만, `action_executor.py`도 함께 정리했다.

기존에 깨져 보이던 주석을 ASCII 주석으로 바꿨고, 현재 구조가 딕셔너리 디스패치 방식임을 명확히 남겼다.

현재 핵심 주석:

```python
# Map action names to handlers so new actions do not lengthen run().
```

의미:

- 새 action이 생겨도 `run()` 함수 안에 긴 `if/elif`를 계속 추가하지 않기 위한 구조다.
- action 이름과 실행 함수를 `self.action_handlers` 딕셔너리에 등록한다.

## 5. 변경 후 실행 방법

### 5-1. CLI에서 여러 시나리오 지정

아래처럼 `--scenario` 옵션을 여러 번 사용할 수 있다.

```powershell
python fcm_gui_automation\main.py --app-path d:\app\fcm_desktop.py --scenario d:\app\fcm_gui_automation\scenarios\basic_test.yaml --scenario d:\app\fcm_gui_automation\scenarios\basic_test.yaml
```

전달된 순서대로 시나리오가 실행된다.

### 5-2. 파일 선택 창에서 여러 시나리오 선택

아래처럼 실행하면 앱 선택 창과 시나리오 선택 창이 열린다.

```powershell
python fcm_gui_automation\main.py
```

시나리오 선택 창에서는 여러 YAML 파일을 선택할 수 있다.
선택된 목록이 실행 대상 시나리오 목록이 된다.

## 6. 로그 변화

기존에는 선택된 시나리오 하나만 로그에 남았다.

이제는 아래처럼 여러 시나리오 목록과 각 실행 순서가 로그에 남는다.

```text
Selected scenarios: scenario1.yaml, scenario2.yaml
Running scenario 1/2: basic_pywinauto_poc (...)
Running scenario 2/2: basic_pywinauto_poc (...)
All scenarios completed successfully.
```

이 로그 구조는 여러 테스트를 실행했을 때 어떤 시나리오에서 실패했는지 추적하기 좋다.

## 7. 검증 내용

검증은 기존 `basic_test.yaml`을 두 번 연속 지정해서 수행했다.

실행 명령:

```powershell
python fcm_gui_automation\main.py --app-path d:\app\fcm_desktop.py --scenario d:\app\fcm_gui_automation\scenarios\basic_test.yaml --scenario d:\app\fcm_gui_automation\scenarios\basic_test.yaml
```

검증 결과:

- 문법 검사 성공
- 첫 번째 시나리오 실행 성공
- 두 번째 시나리오 실행 성공
- 각 시나리오별 스크린샷 저장 성공
- 최종 로그에 `All scenarios completed successfully.` 출력

생성된 성공 스크린샷:

- `20260428_214123_basic_test_success.png`
- `20260428_214127_basic_test_success.png`

## 8. 실패 처리 방식

현재 구조에서는 여러 시나리오 중 하나라도 실패하면 `except` 블록으로 이동한다.

그 후 처리 흐름:

- 실패 로그 기록
- `fail_safe.handle_failure(error)` 호출
- 실패 스크린샷 저장 시도
- 안전 종료 시도
- 프로그램 종료 코드 `1` 반환

즉, 현재 배치 실행 방식은 "중간 실패 시 즉시 중단" 방식이다.

이 방식은 초기 자동화에서는 안전하다.
다만 나중에 운영 정책에 따라 실패해도 다음 시나리오를 계속 실행하는 방식으로 바꿀 수 있다.

## 9. 현재 구조의 장점

이번 변경으로 얻은 장점은 아래와 같다.

- 여러 테스트 케이스를 한 번에 실행 가능
- CLI 자동 실행과 파일 선택 실행을 모두 지원
- 시나리오별 진행 상황이 로그에 남음
- 기존 `ActionExecutor` 구조를 그대로 재사용
- 기존 YAML 시나리오 형식을 바꾸지 않아도 됨

## 10. 앞으로 개선할 수 있는 부분

다음 단계에서 고려할 수 있는 개선은 아래와 같다.

- 시나리오별 성공/실패 요약 리포트 생성
- 실패해도 다음 시나리오 계속 실행하는 옵션 추가
- 시나리오 실행 전 앱 재시작 여부를 YAML에서 선택 가능하게 만들기
- 시나리오 목록 파일 추가
- 실행 순서를 사용자가 UI에서 조정할 수 있는 런처 추가

## 11. 결론

이번 리팩터링으로 자동화 프로그램은 단일 시나리오 실행 도구에서 여러 시나리오를 순차 실행할 수 있는 배치 실행 도구로 확장되었다.

핵심 변화는 `main.py`의 시나리오 선택 및 반복 실행 구조이며, 기존 `ActionExecutor`와 YAML 시나리오 형식은 그대로 유지되었다.

따라서 기존 시나리오 파일과 실행 흐름을 깨지 않으면서, 실제 자동화 운영에 더 가까운 형태로 발전한 변경이라고 볼 수 있다.
