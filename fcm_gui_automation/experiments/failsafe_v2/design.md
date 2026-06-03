# Fail-Safe V2 Design

## Goal

Fail-safe v2 is a validation layer that runs before and after every action.
It does not only react to an exception. It continuously decides whether the
system is safe enough to run the next action, whether the target application is
still alive, and whether the last action produced the expected result.

The first implementation should stay isolated in this experiment folder. After
the behavior is confirmed, selected parts can move into `core/`.

## Failure Levels

Failure priority is always:

```text
emergency > normal > simple
```

If multiple failures are found at the same checkpoint, the highest priority
failure wins.

### Emergency

Emergency means the embedded system may be in an unsafe or broken state.

Examples:

- A test parameter exceeds a configured limit.
- A monitored value reaches a forbidden range.
- A safety status target reports a critical state.
- A monitored flag target shows a forbidden color/state.

Expected behavior:

- Save evidence.
- Stop the scenario immediately.
- Close or stop the target program if configured.
- Do not retry the action.
- Do not restart the scenario.

### Normal

Normal means the GUI program or automation environment is not in the expected
runtime state.

Examples:

- The target program has stopped.
- The target window disappeared.
- The program crashed during a specific step.

Expected behavior:

- Save evidence.
- Record the step where the program stopped.
- If a recovery rule exists for that step/action, restart the program and run
  recovery actions.
- Re-run the scenario from the configured point.
- If no recovery rule exists, stop the scenario.

### Simple

Simple means the action was attempted, but the expected action result was not
observed.

Examples:

- A click did not change the expected status.
- A text verification failed.
- A color verification failed.
- A value did not update after input.

Expected behavior:

- Retry the same action a configured number of times.
- If retries are exhausted, save evidence.
- Then apply the configured final decision.

## Checkpoints

Every action has two fail-safe checkpoints.

```text
pre-check
  -> action
post-check
```

### Pre-Check

Pre-check decides whether an action is allowed to run.

It should verify:

- The target application is running.
- The target window is available.
- The step target exists if the step requires a target.
- No emergency condition is currently active.
- No normal condition is currently active.

Pre-check should not verify the final action result, because the action has not
run yet.

### Post-Check

Post-check decides whether the action succeeded and whether the system remains
safe afterward.

It should verify:

- No emergency condition became active.
- The target application is still running.
- The target window is still available.
- The expected result of the action is visible.
- Step-level post conditions passed.

## Emergency Monitoring Model

Emergency checks are expected to be numerous. They should not be hard-coded in
Python. They should be declared in YAML as monitored targets.

There are two primary emergency target kinds:

```text
value
flag
```

### Value Target

A value target is a numeric value read from the GUI.

Detection method:

- Resolve the configured target name to a screen/control image.
- Read text with OCR.
- Parse the OCR text into a numeric value.
- Compare it against configured `min` and `max` limits.

This should reuse the existing OCR layer:

- `recognition/ocr_adapter.py`
- `OCRAdapter.read_text()`

### Flag Target

A flag target is a visual status indicator.

Detection method:

- Resolve the configured target name to a screen/control image.
- Detect the target color/state using OpenCV-style image processing.
- Compare the detected color/state with allowed or forbidden states.

The design should expose this as OpenCV/color detection. The current codebase
already has `recognition/color_adapter.py`, which can be used for the MVP while
`OpenCVAdapter` is still reserved for a later phase.

### Target Registry

Emergency targets should be reusable. A scenario should define target metadata
once, and emergency checks should reference those targets by name.

Target metadata can include:

- `kind`: `value` or `flag`
- `source`: how to read it, for example `ocr` or `color`
- `target`: named GUI/control/profile target to inspect
- `parser`: how to parse OCR output, for example `float` or `int`
- `min` / `max`: numeric limits for values
- `allowed_colors`: valid flag colors
- `forbidden_colors`: emergency flag colors
- `min_ratio`: minimum color match ratio for flag detection

This keeps emergency definitions data-driven and makes it possible to monitor
many values and flags without changing code.

### Target Resolution

Fail-safe YAML should use target names, not raw regions.

The runtime should resolve a target name through the existing recognition/profile
layers. The target resolver must use the generated profile map as the primary
source of target geometry and metadata.

```text
target name
  -> generated profile or controls map lookup
  -> UI Automation control lookup, if profile lookup is unavailable
  -> captured image for OCR or color detection
```

This keeps scenario YAML stable even if the window moves or the screen scale
changes. Raw coordinates can still exist inside generated profile data, but they
should not be the primary authoring format for fail-safe rules.

OCR value targets must represent already-normalized numeric values. Unit text is
not stripped by fail-safe parsing. If the screen shows a unit, the selected
target should point only to the numeric portion, or the profile map should define
a numeric-only target. This keeps limit comparisons deterministic.

For MVP flag detection, the supported colors are:

```text
red
green
blue
```

Custom HSV ranges are deferred until a real scenario needs colors outside this
set.

## Proposed Runtime Flow

```text
ScenarioRunnerV2
  for each step:
    StepRunnerV2.run_step(step)

StepRunnerV2
  attempt = 1
  loop:
    pre_result = FailSafeEngine.pre_check(context, step)
    if pre_result blocks action:
      decision = DecisionEngine.decide(pre_result)
      return decision

    action_result = ActionExecutor.execute_step(step)

    post_result = FailSafeEngine.post_check(context, step, action_result)
    if post_result passed:
      return continue_next_step

    decision = DecisionEngine.decide(post_result)
    if decision == retry_action and attempt has retries left:
      attempt += 1
      continue

    return decision
```

## Responsibilities

### ScenarioRunnerV2

- Owns scenario order.
- Applies scenario-level decisions.
- Stops the scenario on emergency.
- Restarts the scenario only when a normal failure recovery policy allows it.
- Records the current step index.

### StepRunnerV2

- Owns one step lifecycle.
- Runs pre-check, action, and post-check.
- Owns simple action retry.
- Does not decide scenario restart by itself.

### FailSafeEngine

- Runs all configured checks.
- Produces a structured check result.
- Does not execute recovery actions.
- Does not directly stop or restart scenarios.

### FailureClassifier

- Converts raw check results and exceptions into one of:
  - emergency
  - normal
  - simple
  - none

### DecisionEngine

- Converts classified failure into an execution decision.
- Applies priority rules.
- Applies YAML policies.

### EvidenceCollectorV2

- Saves screenshot.
- Saves controls dump.
- Saves monitored values.
- Saves failure report.
- Includes checkpoint information:
  - `pre_check`
  - `post_check`
  - `action_exception`

### RecoveryEngine

- Handles normal failures only.
- Can restart the target program.
- Can run configured recovery actions.
- Can request scenario restart.
- MVP can define this interface without fully implementing recovery.

## Proposed Decisions

```text
continue_next_step
retry_action
stop_scenario
restart_scenario
recover_and_restart_scenario
```

Notes:

- `retry_action` is for simple failures.
- `restart_scenario` is for normal failures after app restart.
- `recover_and_restart_scenario` means restart app, run recovery actions, then
  restart scenario.
- Emergency failures should resolve to `stop_scenario`.

## Proposed YAML Shape

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

      temperature_value:
        kind: value
        source: ocr
        target: temperature_value
        parser: float
        max: 80.0

      fault_flag:
        kind: flag
        source: color
        target: fault_flag
        forbidden_colors: [red]
        allowed_colors: [green, blue]
        min_ratio: 0.3

    emergency_checks:
      - target: voltage_value
      - target: temperature_value
      - target: fault_flag

    normal_checks:
      app_alive:
        enabled: true
      window_alive:
        enabled: true

    evidence:
      screenshot: true
      controls_dump: true
      monitored_values: true

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
      simple_retry_count: 3
      on_simple_final_failure: stop_scenario

  - name: Start operation
    action: click
    target: start_button
    fail_safe:
      post_checks:
        - type: target_text_contains
          target: operation_state
          expected: RUNNING
      on_normal:
        recovery:
          restart_app: true
          max_scenario_restarts: 3
          actions:
            - action: click
              target: reconnect_button
          restart_scenario: true
```

Emergency target definitions can also be moved into a separate YAML file when
the list becomes large:

```yaml
scenario:
  name: operation_test
  fail_safe:
    emergency_targets_file: monitors/operation_emergency_targets.yaml
```

Example external monitor file:

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

## Structured Results

### CheckResult

```text
checkpoint: pre_check | post_check | action_exception
level: none | simple | normal | emergency
passed: bool
checks: list[SingleCheckResult]
error: optional error
```

### SingleCheckResult

```text
name: string
level: none | simple | normal | emergency
passed: bool
message: string
observed: any
expected: any
```

### DecisionResult

```text
decision: continue_next_step | retry_action | stop_scenario | restart_scenario | recover_and_restart_scenario
level: none | simple | normal | emergency
reason: string
evidence_path: optional path
```

## MVP Scope

Implement first:

- Data models.
- Failure priority.
- Pre-check target existence.
- Pre-check app/window alive check.
- Post-check app/window alive check.
- Post-check expected text check.
- Simple retry.
- Emergency check interface.
- YAML-driven emergency value target with OCR numeric limit check.
- YAML-driven emergency flag target with color detection.
- Profile-map-first target resolver.
- Scenario restart limit with default maximum of 3 restarts.
- Evidence report.

Defer:

- Real embedded communication.
- Full recovery action engine.
- Automatic popup handling.
- Complex scenario resume points.
- Parallel monitoring thread.
- Unit-stripping OCR parsers. Emergency value targets should expose numeric
  text only.
- Full OpenCV adapter replacement if `ColorAdapter` is enough for MVP.

## Resolved Design Decisions

1. Target resolver must consult the generated profile map first.
2. OCR value parsing does not remove units. Emergency value targets should be
   numeric-only targets.
3. MVP flag colors are limited to `red`, `green`, and `blue`.
4. Scenario restart has a maximum count. The current planned default is 3.
5. If scenario restart count exceeds the maximum, fail-safe stops the scenario
   instead of restarting again.

## Open Questions

1. Program stopped detection: should it use process id, window existence, or both?
2. Scenario restart: should it restart from step 1 or from a named checkpoint?
3. Recovery actions: should they use the same action schema as normal steps?
4. Should emergency close the GUI program, kill the process, or leave it open for inspection?
