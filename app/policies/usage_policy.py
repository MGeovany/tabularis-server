"""Policy: plan-based usage rules (Free vs Pro)."""

from abc import ABC, abstractmethod

from app.models.user import User


class UsagePolicy(ABC):
    """Policy for whether a user can convert and what message to show when limit exceeded."""

    @abstractmethod
    def can_convert(self, user: User) -> bool:
        """Return True if user has remaining conversions under this plan."""
        ...

    @abstractmethod
    def limit_exceeded_message(self) -> str:
        """Message to show when user hits the limit."""
        ...


class FreePlanPolicy(UsagePolicy):
    """FREE plan: fixed limit (e.g. 10 conversions)."""

    def can_convert(self, user: User) -> bool:
        return (user.conversions_used or 0) < (user.conversions_limit or 10)

    def limit_exceeded_message(self) -> str:
        return "Usage limit reached. Please upgrade to Pro to continue converting."


class ProPlanPolicy(UsagePolicy):
    """PRO plan: use user's conversions_limit (0 = unlimited)."""

    def can_convert(self, user: User) -> bool:
        limit = user.conversions_limit or 0
        if limit <= 0:
            return True  # unlimited
        return (user.conversions_used or 0) < limit

    def limit_exceeded_message(self) -> str:
        return "Usage limit reached for your plan."


def get_usage_policy(plan: str) -> UsagePolicy:
    """Return the policy for the given plan name."""
    if (plan or "").upper() == "PRO":
        return ProPlanPolicy()
    return FreePlanPolicy()
