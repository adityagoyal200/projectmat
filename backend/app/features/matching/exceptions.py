class LlmEvaluationError(Exception):
    """Raised when LLM evaluation is required but unavailable
    or returns invalid output.
    """

    def __init__(self, message: str, *, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class MatchingUnavailableError(Exception):
    """Raised when matching cannot run because LLM is disabled or not configured."""

    def __init__(self, message: str):
        super().__init__(message)
