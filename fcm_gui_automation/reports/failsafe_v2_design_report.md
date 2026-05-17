# Fail-Safe V2 설계 상세 보고서

작성일: 2026-05-15
대상 프로젝트: `D:\app\fcm_gui_automation`
대상 설계: `experiments/failsafe_v2`

## 1. 보고서 목적

이 보고서는 새로 설계한 Fail-Safe V2 구조를 파일 구성부터 세부 데이터 모델까지 설명하기 위해 작성되었다.

이번 설계의 핵심은 기존처럼 실패가 발생한 뒤에만 후처리하는 방식이 아니라, 각 action의 전후로 시스템 상태를 검증하는 fail-safe 계층을 두는 것이다.

Fail-Safe V2는 다음 세 가지 실패 등급을 기준으로 동작한다.

- 긴급: 임베디드 장비의 이상 가능성이 있는 상태
- 보통: GUI 프로그램 종료, 윈도우 사라짐, 프로세스 중단 같은 실행 환경 이상
- 단순: action 후 원하는 결과가 나오지 않은 일반 검증 실패

오류 우선순위는 항상 다음과 같다.

```text
긴급 > 보통 > 단순
```

즉, 단순 실패처럼 보여도 동시에 긴급 조건이 감지되면 retry를 하지 않고 즉시 시나리오를 중단하는 방향으로 판단한다.

## 2. 현재 파일 구성

Fail-Safe V2는 기존 실행 경로를 건드리지 않기 위해 실험 폴더에 분리했다.

```text
fcm_gui_automation/
  experiments/
    failsafe_v2/
      README.md
      __init__.py
      design.md
      models.py
  reports/
    failsafe_v2_design_report.md
    failsafe_v2_design_report.pdf
```

각 파일의 역할은 다음과 같다.

| 파일 | 역할 |
| --- | --- |
| `README.md` | 실험 폴더의 목적과 운영 규칙 설명 |
| `__init__.py` | Python 패키지 인식용 파일 |
| `design.md` | Fail-Safe V2 전체 설계 문서 |
| `models.py` | 설계를 코드로 옮길 때 기준이 되는 데이터 모델 |
| `failsafe_v2_design_report.md` | 현재 보고서 원문 |
| `failsafe_v2_design_report.pdf` | 현재 보고서 PDF 출력물 |

현재 `experiments/failsafe_v2`는 기존 `main.py`에서 import하지 않는다. 따라서 현재 자동화 실행 흐름에는 영향을 주지 않는다.

## 3. 설계의 큰 흐름

Fail-Safe V2는 step 실행을 다음 흐름으로 본다.

```text
pre-check
  -> action 실행
post-check
  -> decision
```

기존 구조가 대체로 "action 실행 중 예외 발생 후 처리"에 가까웠다면, V2는 action 실행 전에도 안전 여부를 판단한다.

## 4. pre-check 동작

pre-check는 action을 실행해도 되는 상태인지 판단한다.

검증 대상은 다음과 같다.

- 대상 프로그램이 살아 있는가
- 대상 윈도우가 존재하는가
- step에 작성된 target이 현재 잡히는가
- 긴급 조건이 이미 발생해 있지 않은가
- 보통 조건이 이미 발생해 있지 않은가

예를 들어 다음 step이 있다고 가정한다.

```yaml
- name: Connect click
  action: click
  target: connect_button
```

이 경우 pre-check는 action 실행 전에 `connect_button` target을 찾을 수 있는지 확인해야 한다. target이 잡히지 않으면 click을 실행하지 않고 보통 또는 단순 실패로 분류할 수 있다. 또한 같은 시점에 긴급 감시 값도 확인한다.

## 5. post-check 동작

post-check는 action 실행 이후 결과가 원하는 대로 되었는지 판단한다.

검증 대상은 다음과 같다.

- 긴급 조건이 새로 발생했는가
- 프로그램이 action 이후 종료되었는가
- 윈도우가 사라졌는가
- action 결과가 기대 상태가 되었는가
- step에 정의된 post condition이 통과했는가

예를 들어 connect 버튼 클릭 후 상태 텍스트가 `CONNECTED`가 되어야 한다면 다음과 같이 표현한다.

```yaml
fail_safe:
  post_checks:
    - type: target_text_contains
      target: status_text
      expected: CONNECTED
```

post-check에서 기대 결과가 나오지 않으면 단순 실패로 보고 action retry를 수행한다. 단, 동시에 긴급 값이 제한을 넘으면 단순 retry가 아니라 긴급 중단을 선택한다.

## 6. 긴급 감시의 목표

긴급 감시는 임베디드 장비가 정상 범위를 벗어났는지 확인하기 위한 기능이다.

긴급 감시 대상은 많고, 값과 flag가 섞여 있다. 따라서 Python 코드에 감시 항목을 하드코딩하지 않고 YAML로 관리한다.

감시 대상은 크게 두 종류다.

| 종류 | 의미 | 감지 방식 |
| --- | --- | --- |
| `value` | 숫자 값 | OCR로 읽고 min/max 비교 |
| `flag` | 램프, 상태 표시, 색상 flag | 색상 감지 또는 OpenCV 계층으로 판정 |

## 7. target 기반 감시

초기 설계에서는 화면 `region`을 직접 YAML에 쓰는 방안도 고려했지만, 최종 방향은 target 기반이다.

YAML 작성자는 좌표를 직접 쓰지 않는다. 대신 감시 대상 target 이름을 쓴다.

```yaml
emergency_targets:
  voltage_value:
    kind: value
    source: ocr
    target: voltage_value
    parser: float
    min: 0.0
    max: 5.0
```

이 구조의 장점은 다음과 같다.

- 화면 위치가 바뀌어도 YAML을 덜 수정한다.
- profile generator가 만든 target 정보를 재사용할 수 있다.
- UI Automation으로 찾을 수 있는 target은 직접 control image를 얻을 수 있다.
- OCR/OpenCV 판정 로직과 target 탐색 로직을 분리할 수 있다.

target 해석은 다음 순서를 목표로 한다.

```text
target name
  -> UI Automation control lookup
  -> generated profile / controls map lookup
  -> captured image for OCR or color detection
```

## 8. 긴급 value target

value target은 GUI에 표시된 숫자를 OCR로 읽고 제한값과 비교한다.

YAML 예시는 다음과 같다.

```yaml
emergency_targets:
  temperature_value:
    kind: value
    source: ocr
    target: temperature_value
    parser: float
    max: 80.0
```

동작 순서는 다음과 같다.

1. `temperature_value` target을 찾는다.
2. target 영역 또는 control image를 캡처한다.
3. 기존 `OCRAdapter.read_text()`로 텍스트를 읽는다.
4. `parser: float` 규칙에 따라 숫자로 변환한다.
5. 값이 `max: 80.0`을 초과하면 긴급 실패로 분류한다.

기존 OCR 코드는 다음 형태로 재사용할 수 있다.

```python
adapter = OCRAdapter()
text = adapter.read_text(target_image)
value = float(text)
```

OCR value target은 단위가 제거된 숫자 값을 대상으로 한다. 단위 문자열은 parser가 제거하지 않는다. 화면에 단위가 함께 보이는 경우에는 profile map에서 숫자 부분만 별도 target으로 잡거나, 해당 GUI가 숫자 값만 노출하는 target을 제공해야 한다.

## 9. 긴급 flag target

flag target은 램프나 상태 표시처럼 색상으로 상태를 알려주는 대상을 감시한다.

YAML 예시는 다음과 같다.

```yaml
emergency_targets:
  fault_flag:
    kind: flag
    source: color
    target: fault_flag
    forbidden_colors: [red]
    allowed_colors: [green, blue]
    min_ratio: 0.3
```

동작 순서는 다음과 같다.

1. `fault_flag` target을 찾는다.
2. target 영역 또는 control image를 캡처한다.
3. 색상 감지 계층으로 dominant color 또는 expected color ratio를 계산한다.
4. 감지된 색상이 `forbidden_colors`에 포함되면 긴급 실패로 분류한다.

현재 프로젝트에는 `OpenCVAdapter`가 아직 placeholder로 남아 있다. 대신 실제 색상 판정은 `ColorAdapter`에 구현되어 있다.

관련 코드 구조는 다음과 같다.

```python
class ColorAdapter:
    SUPPORTED_COLORS = {"red", "green", "blue"}

    def calculate_color_ratio(
        self,
        screenshot: Image.Image,
        region: dict,
        expected_color: str,
    ) -> tuple[float, int, int]:
        ...
```

V2 설계에서는 외부 이름은 OpenCV/color detection으로 두고, MVP 구현은 현재 동작하는 `ColorAdapter`를 재사용하는 방식이 적절하다.

## 10. YAML 구성 제안

전체 fail-safe YAML은 scenario-level 정책과 step-level 정책으로 나눈다.

```yaml
scenario:
  name: operation_test
  fail_safe:
    enabled: true
    simple_retry_count: 3
    simple_retry_interval: 1.0
    on_emergency: stop_scenario
    on_normal: recover_and_restart_scenario
    on_simple_final_failure: stop_scenario
    max_scenario_restarts: 3

    emergency_targets:
      voltage_value:
        kind: value
        source: ocr
        target: voltage_value
        parser: float
        min: 0.0
        max: 5.0

      fault_flag:
        kind: flag
        source: color
        target: fault_flag
        forbidden_colors: [red]
        min_ratio: 0.3

steps:
  - name: Connect click
    action: click
    target: connect_button
    fail_safe:
      pre_checks:
        target_exists: true
      post_checks:
        - type: target_text_contains
          target: status_text
          expected: CONNECTED
```

감시 항목이 많아지면 별도 YAML 파일로 분리한다.

```yaml
scenario:
  name: operation_test
  fail_safe:
    emergency_targets_file: monitors/operation_emergency_targets.yaml
```

분리된 monitor 파일은 다음 형태를 가진다.

```yaml
emergency_targets:
  dc_link_voltage:
    kind: value
    source: ocr
    target: dc_link_voltage_value
    parser: float
    min: 10.0
    max: 15.0

  inverter_fault_flag:
    kind: flag
    source: color
    target: inverter_fault_lamp
    forbidden_colors: [red]
    min_ratio: 0.3
```

## 11. 데이터 모델 코드

현재 `models.py`는 설계에서 사용할 기본 타입을 정의한다.

```python
class Checkpoint(str, Enum):
    PRE_CHECK = "pre_check"
    POST_CHECK = "post_check"
    ACTION_EXCEPTION = "action_exception"
```

`Checkpoint`는 fail-safe 검사가 어느 시점에서 발생했는지 나타낸다.

```python
class FailureLevel(str, Enum):
    NONE = "none"
    SIMPLE = "simple"
    NORMAL = "normal"
    EMERGENCY = "emergency"
```

`FailureLevel`은 실패 등급을 나타낸다. 판단 우선순위는 `EMERGENCY`가 가장 높다.

```python
class Decision(str, Enum):
    CONTINUE_NEXT_STEP = "continue_next_step"
    RETRY_ACTION = "retry_action"
    STOP_SCENARIO = "stop_scenario"
    RESTART_SCENARIO = "restart_scenario"
    RECOVER_AND_RESTART_SCENARIO = "recover_and_restart_scenario"
```

`Decision`은 fail-safe 판단 이후 runner가 수행할 행동이다.

```python
class MonitorKind(str, Enum):
    VALUE = "value"
    FLAG = "flag"


class MonitorSource(str, Enum):
    OCR = "ocr"
    COLOR = "color"
```

`MonitorKind`는 감시 대상이 숫자 값인지 flag인지 구분한다. `MonitorSource`는 OCR 또는 color detection 중 어떤 방식으로 읽을지 나타낸다.

```python
@dataclass(frozen=True)
class EmergencyTarget:
    name: str
    kind: MonitorKind
    source: MonitorSource
    target: str
    parser: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    allowed_colors: list[str] = field(default_factory=list)
    forbidden_colors: list[str] = field(default_factory=list)
    min_ratio: float | None = None
```

`EmergencyTarget`은 YAML의 `emergency_targets` 한 항목을 코드에서 표현하기 위한 모델이다.

중요한 점은 `region`이 아니라 `target`을 가진다는 것이다. 좌표는 YAML 작성자가 직접 관리하지 않고, target resolver가 profile 또는 UI Automation 정보에서 찾아야 한다.

시나리오 재시작 제한은 별도 정책 모델로 표현한다.

```python
@dataclass(frozen=True)
class ScenarioRestartPolicy:
    max_restarts: int = 3
    current_restarts: int = 0

    def can_restart(self) -> bool:
        return self.current_restarts < self.max_restarts
```

`max_restarts` 기본값은 3이다. 보통 실패로 인해 시나리오 재시작이 필요하더라도 `current_restarts`가 3 이상이면 더 이상 재시작하지 않고 종료 decision으로 전환한다.

## 12. CheckResult 구조

단일 검사 결과는 `SingleCheckResult`로 표현한다.

```python
@dataclass(frozen=True)
class SingleCheckResult:
    name: str
    level: FailureLevel
    passed: bool
    message: str = ""
    observed: Any | None = None
    expected: Any | None = None
```

예를 들어 `temperature_value`가 87.5로 읽혔고 최대값이 80.0이라면 다음과 같은 결과가 만들어진다.

```python
SingleCheckResult(
    name="temperature_value",
    level=FailureLevel.EMERGENCY,
    passed=False,
    message="value exceeded max limit",
    observed=87.5,
    expected={"max": 80.0},
)
```

여러 검사 결과를 합친 것이 `CheckResult`다.

```python
@dataclass(frozen=True)
class CheckResult:
    checkpoint: Checkpoint
    level: FailureLevel
    passed: bool
    checks: list[SingleCheckResult] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
```

`CheckResult.level`은 포함된 검사 중 가장 높은 실패 등급이 된다.

## 13. 실패 우선순위 계산

실패 우선순위는 다음 dict로 표현한다.

```python
FAILURE_PRIORITY = {
    FailureLevel.NONE: 0,
    FailureLevel.SIMPLE: 1,
    FailureLevel.NORMAL: 2,
    FailureLevel.EMERGENCY: 3,
}
```

그리고 여러 검사 중 가장 높은 실패 등급은 다음 함수로 계산한다.

```python
def highest_failure_level(results: list[SingleCheckResult]) -> FailureLevel:
    highest = FailureLevel.NONE
    for result in results:
        if not result.passed and FAILURE_PRIORITY[result.level] > FAILURE_PRIORITY[highest]:
            highest = result.level
    return highest
```

이 함수 덕분에 단순 실패와 긴급 실패가 동시에 발생했을 때 긴급 실패가 최종 판단으로 선택된다.

## 14. 책임 분리

V2에서 필요한 주요 구성 요소는 다음과 같다.

| 구성 요소 | 책임 |
| --- | --- |
| `ScenarioRunnerV2` | 전체 step 순서 관리, scenario stop/restart 결정 반영 |
| `StepRunnerV2` | 한 step의 pre-check, action, post-check, retry 관리 |
| `FailSafeEngine` | YAML 기반 검사를 실행하고 `CheckResult` 생성 |
| `TargetResolver` | target 이름을 실제 control/image 영역으로 변환 |
| `EmergencyMonitor` | value/flag 긴급 감시 수행 |
| `DecisionEngine` | 실패 등급과 정책을 decision으로 변환 |
| `EvidenceCollectorV2` | screenshot, controls dump, OCR 결과, 색상 감지 결과 저장 |
| `RecoveryEngine` | 보통 실패 발생 시 프로그램 재실행과 복구 action 수행 |

가장 중요한 추가 구성은 `TargetResolver`다. target 기반 YAML을 사용하려면 감시 target을 실제 이미지로 바꾸는 계층이 필요하다.

## 15. TargetResolver의 필요성

Fail-safe YAML은 다음처럼 target 이름만 가진다.

```yaml
target: voltage_value
```

하지만 OCR과 색상 감지는 실제 이미지가 필요하다. 따라서 실행 시에는 다음 변환이 필요하다.

```text
voltage_value
  -> profile map lookup
  -> target rectangle or metadata
  -> window screenshot crop
  -> OCRAdapter.read_text(cropped_image)
```

profile map에서 target을 찾지 못한 경우에는 보조 경로로 UI Automation을 사용할 수 있다.

```text
voltage_value
  -> UI Automation control lookup
  -> control.capture_as_image()
  -> OCRAdapter.read_text(image)
```

즉, `TargetResolver`는 target 이름과 image detector 사이의 연결부다. 이번 설계에서는 profile map을 1순위로 사용한다.

## 16. Evidence 저장 내용

긴급 또는 최종 실패가 발생하면 다음 자료를 저장해야 한다.

- 전체 스크린샷
- controls dump
- 실패 시점의 checkpoint
- 실패 step index
- 실패 action
- 감시 target 이름
- OCR 원문
- parsing 결과
- 색상 판정 결과
- 최종 failure level
- 최종 decision

예상 report YAML은 다음 형태다.

```yaml
scenario: operation_test
step_index: 7
checkpoint: post_check
level: emergency
decision: stop_scenario
restart_count: 0
max_scenario_restarts: 3
failed_checks:
  - name: temperature_value
    kind: value
    source: ocr
    target: temperature_value
    observed: 87.5
    expected:
      max: 80.0
    raw_text: "87.5"
evidence:
  screenshot: screenshot.png
  controls_dump: controls_dump.yaml
```

## 17. MVP 구현 순서 제안

V2 구현은 다음 순서로 진행하는 것이 좋다.

1. YAML parser 작성
2. `EmergencyTarget` 로딩
3. `TargetResolver` 인터페이스 정의
4. fake resolver로 단위 테스트 작성
5. OCR value check 구현
6. color flag check 구현
7. `FailSafeEngine.pre_check()` 구현
8. `FailSafeEngine.post_check()` 구현
9. `DecisionEngine` 구현
10. `StepRunnerV2`에 simple retry 연결
11. scenario restart count 관리
12. evidence report 저장
13. 실제 `PyWinAutoAdapter` target resolver 연결

## 18. 확정된 설계 결정

이번 논의에서 확정된 내용은 다음과 같다.

- target resolver는 profile map을 먼저 본다.
- OCR value target은 단위가 제외된 숫자 값만 대상으로 한다.
- parser는 단위 제거를 하지 않고, 이미 범위 판단 가능한 value를 입력으로 받는다.
- flag 색상은 MVP 기준 red, green, blue면 충분하다.
- scenario restart에는 최대 횟수를 둔다.
- 현재 기본값은 `max_scenario_restarts: 3`이다.
- scenario restart가 3회를 초과하면 더 이상 재시작하지 않고 시나리오를 종료한다.

재시작 판단 흐름은 다음과 같다.

```text
normal failure detected
  -> recovery rule exists
  -> restart_count < max_scenario_restarts
  -> restart app
  -> run recovery actions
  -> restart scenario
```

재시작 횟수를 초과하면 다음 흐름이 된다.

```text
normal failure detected
  -> restart_count >= max_scenario_restarts
  -> save evidence
  -> stop_scenario
```

## 19. 이번 설계에서 아직 남은 질문

아직 구현 전에 결정해야 할 항목은 다음과 같다.

- 보통 실패 후 시나리오 재시작은 step 1부터 할 것인가, checkpoint부터 할 것인가
- 긴급 실패 시 GUI를 닫을 것인가, 증거 확인을 위해 유지할 것인가

## 20. 결론

Fail-Safe V2의 핵심 방향은 target 기반, YAML 기반, pre/post-check 기반이다.

긴급 감시 값은 많고 종류도 다양하므로 Python 코드에 직접 작성하지 않는다. 대신 YAML에서 target과 감시 조건을 선언하고, 실행 계층은 target을 이미지로 변환한 뒤 OCR 또는 색상 감지를 수행한다.

이 설계는 기존 OCRAdapter와 ColorAdapter를 재사용할 수 있다. OpenCVAdapter가 나중에 완성되면 flag 감지 내부 구현만 교체하면 된다.

다음 단계는 `TargetResolver`, `EmergencyMonitor`, `FailSafeEngine`의 MVP 코드를 실험 폴더 안에 구현하고 fake adapter로 먼저 검증하는 것이다.
