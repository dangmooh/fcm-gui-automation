# Profile Generator Scenario Discovery Controller Unification Report

작성일: 2026-06-01

## 목적

시나리오 실행 중 새로 나타나는 창의 controller를 `hierarchical_profile.yaml`에만 추가하지 않고, 최초 main 화면에서 수집한 controller와 같은 방식으로 취급하도록 수정했다.

즉, 새 창에서 발견한 controller도 아래 산출물에 동일하게 반영된다.

- `controls_raw.yaml`
- `controls_dump.yaml`
- `elements.yaml`
- `hierarchical_profile.yaml`
- `discovery_summary.yaml`

## 주요 변경 사항

### 1. 전체 시나리오 discovery 흐름 추가

`app_profile_generator` CLI에 전체 시나리오 실행 옵션을 추가했다.

- `--discover-all-scenarios`
- `--discovery-scenario-dir`

이 옵션을 사용하면 main 화면 profile을 먼저 생성한 뒤, 지정된 scenario directory의 YAML 시나리오를 한 번씩 실행한다. 각 scenario step 이후 새 top-level window 또는 main window 내부 embedded window를 검사하고, 새 화면으로 판단되면 profile에 병합한다.

### 2. 새 창 controller를 기존 controller 목록으로 병합

기존에는 시나리오 discovery 결과가 `hierarchical_profile.yaml`의 `screens`에만 병합되는 구조였다. 이번 수정 후에는 discovery 중 발견한 controller를 `discovered_controls` 목록으로 수집하고, CLI에서 기존 `controls` 목록에 병합한다.

병합 이후 아래 파일을 다시 생성한다.

- `controls_raw.yaml`
- `controls_dump.yaml`
- `elements.yaml`
- `hierarchical_profile.yaml`
- `discovery_summary.yaml`

따라서 새 창 controller는 기존 controller와 동일한 후속 처리 경로를 탄다.

### 3. 화면 context metadata 추가

새 창에서 발견된 controller에는 화면 단위 context를 함께 저장한다.

- `screen_key`
- `screen_title`
- `screen_window_rect`
- `discovered_by`
- `rectangle_ratio`
- `rectangle_ratio_units: window_ratio`

이 metadata로 같은 `index`를 가진 controller가 서로 다른 화면에 있어도 구분할 수 있다.

### 4. `controls_dump.yaml` 화면별 grouping 분리

`controls_dump.yaml` 생성 시 전체 controller를 한 번에 grouping하면, 새 창 controller가 main 화면의 group에 잘못 들어갈 수 있었다.

이를 방지하기 위해 `screen_key` 기준으로 controller를 먼저 나누고, 각 화면별로 독립 grouping을 수행하도록 수정했다.

검증 결과 새로 발견된 `Setting Dialog` controller는 `Operation Group`이 아니라 `Setting Dialog` group으로 분류된다.

### 5. `elements.yaml`에 화면 정보 반영

`elements.yaml`의 각 element에도 `screen_key`, `screen_title`을 포함하도록 수정했다.

또한 region은 기존 절대 좌표 대신 `rectangle_ratio`를 우선 사용한다. 새 창 controller의 ratio는 해당 새 창의 `screen_window_rect` 기준이다.

### 6. review name sync 충돌 방지

`sync-profile-dir`에서 review name을 raw control에 반영할 때 기존에는 `index`만 기준으로 매칭했다.

새 창 controller가 추가되면 화면별로 같은 `index`가 존재할 수 있으므로, 이제 `(screen_key, index)` 조합으로 매칭한다.

## 검증 결과

실행 명령:

```powershell
python -m app_profile_generator.main --app-path d:\app\fcm_desktop.py --discover-all-scenarios --discovery-scenario-dir d:\app\fcm_gui_automation\scenarios --wait-timeout 10
```

최신 생성 결과:

```text
profiles/generated/fcm_desktop_2026-06-01_074018/
```

`discovery_summary.yaml` 결과:

- scenario count: 3
- failed scenarios: 0
- discovered screens: 1
- discovered controllers: 6
- discovered screen: `qt_complex_test_step_015_click_open_dialog_button_embedded_0`
- screen title: `Setting Dialog`

확인된 반영 위치:

- `controls_raw.yaml`: `Setting Dialog` controller 6개 포함
- `controls_dump.yaml`: `screen_key`, `screen_title`, `rectangle_ratio` 포함
- `elements.yaml`: `screen_key`, `screen_title` 포함
- `hierarchical_profile.yaml`: 새 screen으로 `Setting Dialog` 병합

추가 검증:

```powershell
python -m py_compile app_profile_generator\inspection\hierarchical_profile.py app_profile_generator\cli\main.py app_profile_generator\inspection\scenario_discovery.py app_profile_generator\inspection\control_dumper.py
```

결과: 통과

## 발견된 시나리오 이슈

`basic_test.yaml`는 실행 중 아래 target을 찾지 못했다.

- `parameter_group_3`
- `parameter_group_5`

이는 이번 discovery/controller 병합 기능의 실패가 아니라, 현재 application profile 또는 UI 이름과 scenario target 이름이 맞지 않는 기존 시나리오 데이터 문제로 보인다. 전체 discovery는 `continue_on_step_error` 방식으로 진행되므로 다른 scenario와 새 창 수집은 계속 수행된다.

## 결론

새 창에서 발견한 controller는 이제 `hierarchical_profile.yaml`에만 추가되는 것이 아니라 기존 controller와 동일한 데이터 흐름으로 처리된다.

특히 `Setting Dialog` embedded window에서 발견된 6개 controller가 `controls_raw.yaml`, `controls_dump.yaml`, `elements.yaml`, `hierarchical_profile.yaml`에 모두 반영되는 것을 실제 GUI 실행으로 확인했다.
