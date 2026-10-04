from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import BudgetExceeded
from ..models import CostEntry
from ..providers.base import Usage

# Approximate list prices, USD per 1M tokens (input, output). Verify on the provider's pricing page.
# On free tiers nothing is billed; we still record the list-price equivalent so cost stays visible.
PRICES = {"gemini-2.5-flash": (0.30, 2.50), "gemini-embedding": (0.15, 0.0)}


def price(model: str, usage: Usage) -> float:
    for prefix, (pin, pout) in PRICES.items():
        if model.startswith(prefix):
            return (usage.input_tokens * pin + usage.output_tokens * pout) / 1_000_000
    return 0.0  # local / mock models


class CostRecorder:
    def __init__(self, session: Session, settings, provider, job_id: int | None = None):
        self.s, self.settings, self.provider, self.job_id = session, settings, provider, job_id

    def total(self) -> float:
        return float(self.s.scalar(select(func.coalesce(func.sum(CostEntry.cost_usd), 0.0))))

    def check(self) -> None:
        """Budget guard: call before every provider call."""
        if self.total() >= self.settings.budget_usd:
            raise BudgetExceeded(f"budget of ${self.settings.budget_usd:.4f} reached")

    def record(self, kind: str, usage: Usage, ok: bool = True, image_id: int | None = None, post_id: int | None = None) -> None:
        model = self.provider.vision_model if kind == "vision" else self.provider.embed_model
        self.s.add(CostEntry(job_id=self.job_id, kind=kind, provider=self.provider.name, model=model, image_id=image_id,
                             post_id=post_id, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                             cost_usd=price(model, usage), ok=ok))
        self.s.commit()  # persist immediately so a crash never loses the spend record
