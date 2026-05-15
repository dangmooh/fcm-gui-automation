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

    emergency_checks:
      - name: voltage_limit
        source: target_text
        target: voltage_value
        parser: float
        min: 0.0
        max: 5.0

      - name: temperature_limit
        source: target_text
        target: temperature_value
        parser: float
        max: 80.0

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
          actions:
            - action: click
              target: reconnect_button
          restart_scenario: true
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
- Emergency check interface and one target-text numeric limit check.
- Evidence report.

Defer:

- Real embedded communication.
- Full recovery action engine.
- Automatic popup handling.
- Complex scenario resume points.
- Parallel monitoring thread.

## Open Questions

1. Emergency values: are they read from GUI targets, logs, files, or device APIs?
2. Program stopped detection: should it use process id, window existence, or both?
3. Scenario restart: should it restart from step 1 or from a named checkpoint?
4. Recovery actions: should they use the same action schema as normal steps?
5. Should emergency close the GUI program, kill the process, or leave it open for inspection?
