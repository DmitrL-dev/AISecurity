"""
SafeClaw Billing — Test Factories.

Factory Boy factories for generating test data.
"""

import factory
from factory.django import DjangoModelFactory

from billing.models import (
    BillingEvent,
    Subscription,
    UsageLog,
    User,
)
from billing.plans import (
    BillingEventType,
    PlanType,
    SubscriptionStatus,
    PLANS,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@safeclaw.ru")
    telegram_id = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Generate API key hash automatically."""
        if "api_key_hash" not in kwargs:
            _, key_hash = User.generate_api_key()
            kwargs["api_key_hash"] = key_hash
        return super()._create(model_class, *args, **kwargs)


class TelegramUserFactory(UserFactory):
    email = None
    telegram_id = factory.Sequence(lambda n: 100000 + n)


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    plan = PlanType.FREE
    status = SubscriptionStatus.FREE
    tokens_limit = factory.LazyAttribute(lambda o: PLANS[o.plan].tokens_monthly)


class ProSubscriptionFactory(SubscriptionFactory):
    plan = PlanType.PRO
    status = SubscriptionStatus.ACTIVE
    tokens_limit = factory.LazyAttribute(lambda o: PLANS[PlanType.PRO].tokens_monthly)


class BillingEventFactory(DjangoModelFactory):
    class Meta:
        model = BillingEvent

    subscription = factory.SubFactory(SubscriptionFactory)
    event_type = BillingEventType.CREATED
    idempotency_key = factory.Sequence(lambda n: f"idem-{n}")


class UsageLogFactory(DjangoModelFactory):
    class Meta:
        model = UsageLog

    subscription = factory.SubFactory(SubscriptionFactory)
    tokens_input = 100
    tokens_output = 50
    model_used = "gigachat-lite"
    cost_kopecks = 15
