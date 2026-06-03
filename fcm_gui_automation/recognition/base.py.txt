class RecognitionAdapter:
    def launch_or_connect(self) -> None:
        raise NotImplementedError

    def set_text(self, target: str, value: str) -> None:
        raise NotImplementedError

    def click(self, target: str) -> None:
        raise NotImplementedError

    def verify_text(self, target: str, expected: str) -> None:
        raise NotImplementedError

    def verify_color(
        self,
        target: str,
        region: dict,
        expected_color: str,
        min_ratio: float,
    ) -> None:
        raise NotImplementedError

    def capture_window(self, name: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
