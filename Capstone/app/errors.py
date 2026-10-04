class ProviderError(Exception):
    """A vision/embedding provider call failed. `retriable` says whether retrying can help."""

    def __init__(self, message: str, retriable: bool = True):
        super().__init__(message)
        self.retriable = retriable


class InvalidModelOutput(Exception):
    """The model kept returning output that fails schema validation."""


class BudgetExceeded(Exception):
    """Cumulative (list-price-equivalent) spend reached BUDGET_USD."""


class NotEmbedded(Exception):
    """The post has no embedding yet (run the batch job first)."""
