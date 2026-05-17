# FCM GUI Automation Action Reference Report

이 문서는 현재 `fcm_gui_automation`에서 지원하는 action이 무엇이고, 각 action이 코드에서 어떤 방식으로 실행되는지 정리한 보고서다.

## 1. 전체 실행 구조

현재 자동화는 YAML 시나리오 기반으로 동작한다.

실행 순서는 다음과 같다.

```text
scenario YAML
  -> main.py
  -> ScenarioRunner
  -> StepRunner
  -> ActionExecutor
  -> PyWinAutoAdapter / FailSafeManager / ColorAdapter
```

사용자는 `fcm_gui_automation/scenarios/*.yaml` 파일의 `steps`에 action을 작성한다.

예시:

```yaml
steps:
  - action: "launch_or_connect"
  - action: "set_text"
    target: "key_input"
    value: "sample-key"
  - action: "click"
    target: "save_button"
```

`main.py`는 시나리오 파일을 읽고, `ScenarioRunner`에 넘긴다. `ScenarioRunner`는 step을 순서대로 실행하고, 실패가 발생하면 fail-safe 정책을 적용한다. 각 step의 실제 action 실행은 `ActionExecutor.execute_step()`에서 이루어진다.

핵심 매핑은 `core/action_executor.py`의 `action_handlers`다.

```python
self.action_handlers: dict[str, Callable[[dict], None]] = {
    "launch_or_connect": self._launch_or_connect,
    "set_text": self._set_text,
    "click": self._click,
    "verify_text": self._verify_text,
    "verify_color": self._verify_color,
    "screenshot": self._screenshot,
    "safe_close": self._safe_close,
}
```

YAML의 `action` 이름이 이 딕셔너리에 없으면 `Unsupported action` 오류가 발생한다.

## 2. 현재 지원 action 목록

현재 지원되는 action은 다음 7개다.

| action | 목적 | 주요 입력값 |
| --- | --- | --- |
| `launch_or_connect` | 대상 GUI 앱 실행 또는 기존 창 연결 | 없음 |
| `set_text` | 입력 컨트롤에 텍스트 입력 | `target`, `value` |
| `click` | 버튼 등 GUI 컨트롤 클릭 | `target` |
| `verify_text` | 컨트롤의 현재 텍스트 검증 | `target`, `value` 또는 `expected` |
| `verify_color` | 지정 영역의 색상 비율 검증 | `target`, `expected_color`, `min_ratio` |
| `screenshot` | 현재 앱 창 스크린샷 저장 | `value` |
| `safe_close` | 앱 창 안전 종료 | 없음 |

## 3. `launch_or_connect`

### 목적

대상 GUI 프로그램을 실행하거나, 이미 떠 있는 창에 연결한다.

### YAML 예시

```yaml
- action: "launch_or_connect"
```

### 실행 코드

`ActionExecutor`는 `_launch_or_connect()`를 호출한다.

```python
def _launch_or_connect(self, step: dict) -> None:
    self.adapter.launch_or_connect()
```

실제 동작은 `recognition/pywinauto_adapter.py`의 `launch_or_connect()`에서 수행된다.

주요 흐름:

```text
config.yaml의 app 설정 읽기
  -> pywinauto Application 생성
  -> title_re가 있으면 기존 창 연결 시도
  -> 연결 실패 시 대상 앱 실행
  -> top_window 또는 title_re 창 확보
  -> 창이 visible/enabled/ready 상태가 될 때까지 대기
  -> 창에 focus 설정
```

관련 설정은 `fcm_gui_automation/config.yaml`에 있다.

```yaml
app:
  backend: "uia"
  title_re: "^PyQt Input Panel$"
  python_command: "python"
  script_path: "..\\fcm_desktop.py"
  focus_timeout: 10
```

`script_path`가 `.py` 파일이면 `python "script_path"` 형태로 실행하고, `.exe`이면 exe를 직접 실행한다.

## 4. `set_text`

### 목적

GUI 입력칸에 문자열을 입력한다.

### YAML 예시

```yaml
- action: "set_text"
  target: "key_input"
  value: "sample-key"
```

### 실행 코드

`ActionExecutor`는 YAML의 `target`, `value`를 adapter로 넘긴다.

```python
def _set_text(self, step: dict) -> None:
    self.adapter.set_text(step["target"], step["value"])
```

실제 입력은 `PyWinAutoAdapter.set_text()`에서 이루어진다.

```python
def set_text(self, target: str, value: str) -> None:
    control = self._child(target)
    control.set_focus()
    try:
        control.set_edit_text(value)
    except Exception:
        control.type_keys("^a{BACKSPACE}", set_foreground=True)
        control.type_keys(value, with_spaces=True, set_foreground=True)
```

### 동작 방식

먼저 `_child(target)`로 현재 창의 하위 컨트롤 중 `automation_id`가 target과 일치하는 컨트롤을 찾는다.

```python
if auto_id == target or auto_id.endswith(f".{target}"):
    return control
```

예를 들어 `target: "key_input"`이면 `automation_id`가 `key_input`인 입력칸을 찾는다.

컨트롤을 찾으면:

```text
control.set_focus()
  -> 입력칸에 포커스 부여
control.set_edit_text(value)
  -> pywinauto 직접 텍스트 설정 시도
실패 시
  -> Ctrl+A, Backspace로 기존 값 삭제
  -> type_keys로 실제 키보드 입력처럼 value 입력
```

이 fallback 덕분에 `set_edit_text()`가 동작하지 않는 일부 GUI 컨트롤에서도 입력을 시도할 수 있다.

## 5. `click`

### 목적

버튼이나 클릭 가능한 컨트롤을 누른다.

### YAML 예시

```yaml
- action: "click"
  target: "save_button"
```

### 실행 코드

```python
def _click(self, step: dict) -> None:
    self.adapter.click(step["target"])
```

실제 클릭은 `PyWinAutoAdapter.click()`에서 수행된다.

```python
def click(self, target: str) -> None:
    control = self._child(target)
    try:
        control.set_focus()
        control.click()
        time.sleep(0.2)
        return
    except Exception:
        pass

    try:
        control.set_focus()
        control.click_input()
        time.sleep(0.2)
        return
    except Exception:
        pass

    try:
        control.invoke()
        time.sleep(0.2)
        return
    except Exception:
        pass

    control.set_focus()
    control.type_keys("{SPACE}", set_foreground=True)
    time.sleep(0.2)
```

### 동작 방식

`click`은 한 가지 방식만 쓰지 않고 여러 방식으로 순차 시도한다.

```text
1. control.click()
2. 실패하면 control.click_input()
3. 실패하면 control.invoke()
4. 실패하면 Space 키 입력
```

이 구조는 컨트롤 타입이나 GUI 프레임워크에 따라 클릭 방식이 다르게 먹히는 문제를 줄이기 위한 것이다.

## 6. `verify_text`

### 목적

특정 GUI 컨트롤의 현재 텍스트에 기대 문자열이 포함되어 있는지 검증한다.

### YAML 예시

```yaml
- action: "verify_text"
  target: "status_box"
  value: "Key: sample-key"
```

또는 다음처럼 `expected`를 사용할 수도 있다.

```yaml
- action: "verify_text"
  target: "status_box"
  expected: "Key: sample-key"
```

### 실행 코드

```python
def _verify_text(self, step: dict) -> None:
    expected = step.get("value", step.get("expected"))
    if expected is None:
        raise ValueError("verify_text requires value or expected.")
    self.adapter.verify_text(step["target"], expected)
```

실제 검증은 `PyWinAutoAdapter.verify_text()`에서 수행된다.

```python
def verify_text(self, target: str, expected: str) -> None:
    control = self._child(target)
    current_text = control.window_text()
    if expected not in current_text:
        raise AssertionError(
            f"Expected text not found. expected={expected!r}, actual={current_text!r}"
        )
    self.logger.info("Verified text: %s", expected)
```

### 동작 방식

```text
target 컨트롤 찾기
  -> control.window_text()로 현재 텍스트 읽기
  -> expected가 current_text 안에 포함되어 있는지 확인
  -> 포함되어 있으면 성공
  -> 없으면 AssertionError 발생
```

중요한 점은 완전 일치가 아니라 포함 여부를 검사한다는 것이다.

예를 들어 실제 텍스트가 다음과 같다면:

```text
Selected action: Save
Key: sample-key
Value: sample-value
```

`expected`가 `"Key: sample-key"`이면 성공한다.

## 7. `verify_color`

### 목적

GUI 창의 특정 화면 영역에서 기대 색상이 일정 비율 이상인지 검증한다.

### YAML 예시

```yaml
elements:
  status_lamp:
    type: "indicator"
    region:
      x: 20
      y: 105
      width: 660
      height: 70

steps:
  - action: "verify_color"
    name: "status lamp blue check"
    target: "status_lamp"
    expected_color: "blue"
    min_ratio: 0.3
```

### 실행 코드

`verify_color`는 다른 action과 다르게 `target`을 바로 GUI 컨트롤로 찾지 않는다. 먼저 시나리오의 `elements`에서 target 이름에 해당하는 영역 정보를 찾는다.

```python
def _verify_color(self, step: dict) -> None:
    target = step["target"]
    element = self.elements.get(target)
    if element is None:
        raise ValueError(f"Color target is not defined in scenario elements: {target}")

    region = element.get("region")
    if region is None:
        raise ValueError(f"Color target has no region: {target}")

    self.adapter.verify_color(
        target=target,
        region=region,
        expected_color=step["expected_color"],
        min_ratio=float(step["min_ratio"]),
    )
```

실제 화면 캡처와 색상 분석은 `PyWinAutoAdapter.verify_color()`와 `ColorAdapter.verify_target_color()`가 나눠서 수행한다.

```python
screenshot = self.window.capture_as_image()
result = self.color_adapter.verify_target_color(
    screenshot=screenshot,
    target=target,
    region=region,
    expected_color=expected_color,
    min_ratio=min_ratio,
)
```

### 동작 방식

```text
target 이름으로 elements에서 region 찾기
  -> 현재 앱 창 screenshot 캡처
  -> region 영역만 crop
  -> 픽셀을 RGB에서 HSV로 변환
  -> 어둡거나 회색에 가까운 픽셀은 제외
  -> expected_color에 해당하는 hue 범위 픽셀 비율 계산
  -> detected_ratio >= min_ratio이면 성공
  -> 부족하면 AssertionError 발생
```

현재 지원 색상은 `red`, `green`, `blue` 세 가지다.

```python
SUPPORTED_COLORS = {"red", "green", "blue"}
```

색상 판정 기준은 HSV hue 범위다.

| expected_color | hue 기준 |
| --- | --- |
| `red` | `0..10` 또는 `170..180` |
| `green` | `35..85` |
| `blue` | `90..130` |

또한 saturation과 value가 낮은 픽셀은 제외한다.

```python
if saturation < 50 or value < 50:
    continue
```

따라서 테두리, 그림자, 검은 글자, 회색 배경이 색상 비율을 과도하게 흔들지 않도록 설계되어 있다.

## 8. `screenshot`

### 목적

현재 앱 창을 이미지 파일로 저장한다.

### YAML 예시

```yaml
- action: "screenshot"
  value: "basic_test_success"
```

### 실행 코드

```python
def _screenshot(self, step: dict) -> None:
    self.adapter.capture_window(step["value"])
```

실제 저장은 `PyWinAutoAdapter.capture_window()`에서 수행된다.

```python
def capture_window(self, name: str) -> None:
    if self.window is None:
        raise RuntimeError("Window is not connected.")
    screenshot_path = build_screenshot_path(self.base_dir, name)
    self.capture_window_to(screenshot_path)
```

### 동작 방식

```text
value를 스크린샷 이름으로 사용
  -> build_screenshot_path()로 저장 경로 생성
  -> 현재 window.capture_as_image() 호출
  -> 이미지 파일 저장
```

창이 연결되어 있지 않으면 `RuntimeError("Window is not connected.")`가 발생한다.

## 9. `safe_close`

### 목적

테스트가 끝난 뒤 대상 앱 창을 안전하게 닫는다.

### YAML 예시

```yaml
- action: "safe_close"
```

### 실행 코드

```python
def _safe_close(self, step: dict) -> None:
    self.fail_safe.safe_close()
```

`FailSafeManager.safe_close()`는 adapter의 `close()`를 호출한다.

```python
def safe_close(self) -> None:
    try:
        self.adapter.close()
    except Exception as close_error:
        self.logger.warning("Safe close skipped: %s", close_error)
```

실제 창 닫기는 `PyWinAutoAdapter.close()`가 처리한다.

```python
def close(self) -> None:
    if self.window is None:
        return
    try:
        self.window.close()
    except Exception:
        if self.process_started and self.app is not None:
            self.app.kill()
```

### 동작 방식

```text
window가 없으면 아무것도 하지 않음
  -> window.close() 시도
  -> 실패했고 자동화가 직접 실행한 프로세스라면 app.kill() 시도
```

`safe_close`는 실패해도 전체 프로그램이 바로 죽지 않도록 `FailSafeManager`에서 예외를 잡고 warning 로그만 남긴다.

## 10. 실패 처리와 재시도

각 action 실행 중 예외가 발생하면 `StepRunner`와 `ScenarioRunner`가 처리한다.

`StepRunner`는 step 또는 scenario의 `fail_safe.retry_count` 값을 보고 같은 step을 재시도할 수 있다.

```python
retry_count = max(0, int(fail_safe_options.get("retry_count", 0)))
max_attempts = retry_count + 1
```

재시도까지 실패하면 `ScenarioRunner`가 `FailSafeManager.handle_step_failure()`를 호출한다.

실패 유형은 대략 다음처럼 분류된다.

| 실패 상황 | 분류 |
| --- | --- |
| `AssertionError` | `assertion_failed` |
| 대상 컨트롤을 찾지 못함 | `target_not_found` |
| 창 연결 전 action 실행 | `window_not_connected` |
| 지원하지 않는 action | `unsupported_action` |
| 그 외 | `unknown` |

이후 fail-safe 정책에 따라 다음 step으로 넘어가거나, 같은 step을 다시 시도하거나, 시나리오를 중단한다.

## 11. 새 action 추가 방법

새 action을 추가하려면 보통 두 곳을 수정한다.

1. `core/action_executor.py`
2. `recognition/pywinauto_adapter.py`

예를 들어 `double_click` action을 추가한다면:

```python
# core/action_executor.py
self.action_handlers: dict[str, Callable[[dict], None]] = {
    ...
    "double_click": self._double_click,
}

def _double_click(self, step: dict) -> None:
    self.adapter.double_click(step["target"])
```

그리고 adapter에 실제 구현을 추가한다.

```python
# recognition/pywinauto_adapter.py
def double_click(self, target: str) -> None:
    control = self._child(target)
    control.set_focus()
    control.double_click_input()
```

그러면 YAML에서 다음처럼 사용할 수 있다.

```yaml
- action: "double_click"
  target: "save_button"
```

adapter 메서드가 추상 인터페이스에 포함되어야 하는 공통 기능이라면 `recognition/base.py`에도 메서드를 추가하는 것이 좋다.

## 12. 요약

현재 action 시스템은 YAML의 `action` 이름을 `ActionExecutor`가 Python 함수로 매핑하는 단순하고 확장 가능한 구조다.

사용자는 기존 action만 조합해도 기본적인 GUI 자동화를 수행할 수 있다.

```text
앱 실행
  -> 텍스트 입력
  -> 버튼 클릭
  -> 텍스트 검증
  -> 색상 검증
  -> 스크린샷 저장
  -> 앱 종료
```

새로운 GUI 동작이 필요해지면 `ActionExecutor`에 action 이름을 등록하고, adapter에 실제 pywinauto 동작을 구현하면 된다.
