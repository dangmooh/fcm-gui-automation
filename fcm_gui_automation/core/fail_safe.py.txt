from __future__ import annotations

from pathlib import Path

from core.evidence_collector import EvidenceCollector
from core.fail_safe_types import FailSafeDecision, FailSafeResult, FailureType, StepFailure
from core.state_analyzer import StateAnalyzer


class FailSafeManager:
    def __init__(self, adapter, base_dir: Path, logger) -> None:
        self.adapter = adapter
        self.base_dir = base_dir
        self.logger = logger
        self.evidence_collector = EvidenceCollector(adapter=adapter, base_dir=base_dir, logger=logger)
        self.state_analyzer = StateAnalyzer(adapter=adapter, logger=logger)

    def handle_step_failure(
        self,
        failure: StepFailure,
        scenario_fail_safe: dict | None = None,
    ) -> FailSafeResult:
        scenario_options = scenario_fail_safe or {}
        step_options = failure.step.get("fail_safe", {}) or {}
        options = {**scenario_options, **step_options}

        failure_type = self._classify_failure(failure.error)
        decision = self._resolve_decision(options)
        state = self.state_analyzer.collect_state()

        report_path = self.evidence_collector.collect(
            scenario_name=failure.scenario_name,
            step_index=failure.step_index,
            step=failure.step,
            error=failure.error,
            attempts=failure.attempts,
            failure_type=failure_type.value,
            decision=decision.value,
            state=state,
            options=options,
        )

        self.logger.error(
            "Step failed after retries: scenario=%s step=%s failure_type=%s decision=%s",
            failure.scenario_name,
            failure.step_index,
            failure_type.value,
            decision.value,
        )
        return FailSafeResult(
            decision=decision,
            failure_type=failure_type,
            report_path=str(report_path),
        )

    def handle_failure(self, error: Exception) -> None:
        self.logger.error("Handling failure: %s", error)
        try:
            self.adapter.capture_window("failure")
        except Exception as screenshot_error:
            self.logger.warning("Failure screenshot skipped: %s", screenshot_error)
        finally:
            self.safe_close()

    def safe_close(self) -> None:
        try:
            self.adapter.close()
        except Exception as close_error:
            self.logger.warning("Safe close skipped: %s", close_error)

    def _classify_failure(self, error: Exception) -> FailureType:
        error_name = error.__class__.__name__
        error_message = str(error).lower()

        if isinstance(error, AssertionError):
            return FailureType.ASSERTION_FAILED
        if "elementnotfound" in error_name.lower() or "not found" in error_message:
            return FailureType.TARGET_NOT_FOUND
        if "window is not connected" in error_message:
            return FailureType.WINDOW_NOT_CONNECTED
        if isinstance(error, ValueError) and "unsupported action" in error_message:
            return FailureType.UNSUPPORTED_ACTION
        return FailureType.UNKNOWN

    def _resolve_decision(self, options: dict) -> FailSafeDecision:
        raw_decision = (
            options.get("on_final_failure")
            or options.get("default_on_final_failure")
            or FailSafeDecision.STOP_SCENARIO.value
        )
        try:
            return FailSafeDecision(raw_decision)
        except ValueError:
            self.logger.warning(
                "Unsupported fail-safe decision %r. Falling back to stop_scenario.",
                raw_decision,
            )
            return FailSafeDecision.STOP_SCENARIO
