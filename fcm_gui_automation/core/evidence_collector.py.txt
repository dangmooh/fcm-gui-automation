from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml


class EvidenceCollector:
    def __init__(self, adapter, base_dir: Path, logger) -> None:
        self.adapter = adapter
        self.base_dir = base_dir
        self.logger = logger

    def collect(
        self,
        *,
        scenario_name: str,
        step_index: int,
        step: dict,
        error: Exception,
        attempts: int,
        failure_type: str,
        decision: str,
        state: dict,
        options: dict,
    ) -> Path:
        evidence_dir = self._build_evidence_dir(scenario_name, step_index)
        screenshot_path = None
        controls_path = None

        if options.get("save_screenshot_on_failure", True):
            candidate_path = evidence_dir / "screenshot.png"
            if self._save_screenshot(candidate_path):
                screenshot_path = candidate_path

        if options.get("save_controls_on_failure", True):
            candidate_path = evidence_dir / "controls_dump.yaml"
            if self._save_controls_dump(candidate_path):
                controls_path = candidate_path

        report_path = evidence_dir / "failure_report.yaml"
        report = {
            "scenario": scenario_name,
            "step_index": step_index,
            "step_name": step.get("name"),
            "action": step.get("action"),
            "target": step.get("target"),
            "attempts": attempts,
            "failure_type": failure_type,
            "decision": decision,
            "error": {
                "type": error.__class__.__name__,
                "message": str(error),
            },
            "state": state,
            "evidence": {
                "screenshot": str(screenshot_path) if screenshot_path else None,
                "controls_dump": str(controls_path) if controls_path else None,
            },
        }
        with report_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(report, file, allow_unicode=True, sort_keys=False)
        self.logger.info("Saved failure report: %s", report_path)
        return report_path

    def _build_evidence_dir(self, scenario_name: str, step_index: int) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in scenario_name
        )
        evidence_dir = (
            self.base_dir
            / "reports"
            / "failures"
            / f"{timestamp}_{safe_name}_step_{step_index}"
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        return evidence_dir

    def _save_screenshot(self, path: Path) -> bool:
        try:
            if hasattr(self.adapter, "capture_window_to"):
                self.adapter.capture_window_to(path)
            else:
                self.adapter.capture_window(path.stem)
            self.logger.info("Saved failure screenshot: %s", path)
            return True
        except Exception as error:
            self.logger.warning("Failure screenshot skipped: %s", error)
            return False

    def _save_controls_dump(self, path: Path) -> bool:
        try:
            if hasattr(self.adapter, "dump_controls_to"):
                self.adapter.dump_controls_to(path)
            else:
                with path.open("w", encoding="utf-8") as file:
                    yaml.safe_dump({"error": "adapter does not support controls dump"}, file)
            self.logger.info("Saved controls dump: %s", path)
            return True
        except Exception as error:
            self.logger.warning("Controls dump skipped: %s", error)
            return False
