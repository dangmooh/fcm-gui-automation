from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailSafeDecision(str, Enum):
    RETRY_STEP = "retry_step"
    CONTINUE_NEXT_STEP = "continue_next_step"
    STOP_SCENARIO = "stop_scenario"
    RESTART_SCENARIO = "restart_scenario"
    RECOVER_AND_RETRY_STEP = "recover_and_retry_step"


class FailureType(str, Enum):
    ASSERTION_FAILED = "assertion_failed"
    TARGET_NOT_FOUND = "target_not_found"
    WINDOW_NOT_CONNECTED = "window_not_connected"
    UNSUPPORTED_ACTION = "unsupported_action"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StepFailure:
    scenario_name: str
    step_index: int
    step: dict
    error: Exception
    attempts: int


@dataclass(frozen=True)
class FailSafeResult:
    decision: FailSafeDecision
    failure_type: FailureType
    report_path: str | None = None
