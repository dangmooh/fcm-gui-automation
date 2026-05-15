from __future__ import annotations

from core.fail_safe_types import FailSafeDecision, StepFailure


class ScenarioRunner:
    def __init__(self, step_runner, fail_safe, logger) -> None:
        self.step_runner = step_runner
        self.fail_safe = fail_safe
        self.logger = logger

    def run(self, scenario: dict) -> bool:
        normalized = self._normalize_scenario(scenario)
        steps = normalized.get("steps", [])
        if not steps:
            raise ValueError("Scenario has no steps.")

        scenario_name = normalized.get("name", "unnamed_scenario")
        scenario_fail_safe = normalized.get("fail_safe", {}) or {}
        fail_safe_enabled = bool(scenario_fail_safe.get("enabled", True))

        self.step_runner.executor.set_context(normalized)
        index = 0
        decision_retry_counts: dict[int, int] = {}

        while index < len(steps):
            step = steps[index]
            step_number = index + 1
            self.logger.info(
                "Step %s/%s: %s",
                step_number,
                len(steps),
                step.get("name") or step.get("action"),
            )

            try:
                self.step_runner.run_step(step, scenario_fail_safe)
                index += 1
                continue
            except Exception as error:
                if not fail_safe_enabled:
                    raise

                attempts = self._attempt_count(step, scenario_fail_safe)
                result = self.fail_safe.handle_step_failure(
                    StepFailure(
                        scenario_name=scenario_name,
                        step_index=step_number,
                        step=step,
                        error=error,
                        attempts=attempts,
                    ),
                    scenario_fail_safe=scenario_fail_safe,
                )

                if result.decision == FailSafeDecision.CONTINUE_NEXT_STEP:
                    index += 1
                    continue

                if result.decision == FailSafeDecision.RETRY_STEP:
                    decision_retry_counts[index] = decision_retry_counts.get(index, 0) + 1
                    max_decision_retries = int(
                        (step.get("fail_safe", {}) or {}).get(
                            "decision_retry_count",
                            scenario_fail_safe.get("decision_retry_count", 1),
                        )
                    )
                    if decision_retry_counts[index] <= max_decision_retries:
                        self.logger.info(
                            "Fail-safe decision requested retry_step: step=%s retry=%s/%s",
                            step_number,
                            decision_retry_counts[index],
                            max_decision_retries,
                        )
                        continue
                    self.logger.error(
                        "retry_step decision limit reached. Stopping scenario: step=%s",
                        step_number,
                    )
                    return False

                if result.decision == FailSafeDecision.RESTART_SCENARIO:
                    self.logger.warning("restart_scenario is reserved for a later MVP.")
                    return False

                if result.decision == FailSafeDecision.RECOVER_AND_RETRY_STEP:
                    self.logger.warning("recover_and_retry_step is reserved for a later MVP.")
                    return False

                return False

        return True

    def _normalize_scenario(self, scenario: dict) -> dict:
        if "scenario" not in scenario:
            return scenario

        scenario_meta = scenario.get("scenario") or {}
        if not isinstance(scenario_meta, dict):
            raise ValueError("scenario must be a mapping.")

        normalized = {**scenario_meta}
        for key, value in scenario.items():
            if key != "scenario":
                normalized[key] = value
        return normalized

    def _attempt_count(self, step: dict, scenario_fail_safe: dict) -> int:
        fail_safe_options = {**scenario_fail_safe, **(step.get("fail_safe", {}) or {})}
        return max(0, int(fail_safe_options.get("retry_count", 0))) + 1
