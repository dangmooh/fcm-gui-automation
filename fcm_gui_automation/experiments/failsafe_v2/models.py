from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Checkpoint(str, Enum):
    PRE_CHECK = "pre_check"
    POST_CHECK = "post_check"
    ACTION_EXCEPTION = "action_exception"


class FailureLevel(str, Enum):
    NONE = "none"
    SIMPLE = "simple"
    NORMAL = "normal"
    EMERGENCY = "emergency"


class Decision(str, Enum):
    CONTINUE_NEXT_STEP = "continue_next_step"
    RETRY_ACTION = "retry_action"
    STOP_SCENARIO = "stop_scenario"
    RESTART_SCENARIO = "restart_scenario"
    RECOVER_AND_RESTART_SCENARIO = "recover_and_restart_scenario"


FAILURE_PRIORITY = {
    FailureLevel.NONE: 0,
    FailureLevel.SIMPLE: 1,
    FailureLevel.NORMAL: 2,
    FailureLevel.EMERGENCY: 3,
}


@dataclass(frozen=True)
class SingleCheckResult:
    name: str
    level: FailureLevel
    passed: bool
    message: str = ""
    observed: Any | None = None
    expected: Any | None = None


@dataclass(frozen=True)
class CheckResult:
    checkpoint: Checkpoint
    level: FailureLevel
    passed: bool
    checks: list[SingleCheckResult] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    level: FailureLevel
    reason: str
    evidence_path: str | None = None


def highest_failure_level(results: list[SingleCheckResult]) -> FailureLevel:
    highest = FailureLevel.NONE
    for result in results:
        if not result.passed and FAILURE_PRIORITY[result.level] > FAILURE_PRIORITY[highest]:
            highest = result.level
    return highest
