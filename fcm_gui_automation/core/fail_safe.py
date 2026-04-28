from __future__ import annotations


class FailSafeManager:
    def __init__(self, adapter, base_dir, logger) -> None:
        self.adapter = adapter
        self.base_dir = base_dir
        self.logger = logger

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
