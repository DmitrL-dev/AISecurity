"""SafeClaw Bot — Configuration & Plans."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanConfig:
    """Subscription plan configuration."""

    name: str
    display_name: str
    price_rub: int  # 0 = free
    max_agents: int
    tokens_limit: int  # per month
    shield_level: str
    features: list[str] = field(default_factory=list)


# -- Tier definitions (from business plan) --
PLANS: dict[str, PlanConfig] = {
    "free": PlanConfig(
        name="free",
        display_name="🆓 Free",
        price_rub=0,
        max_agents=1,
        tokens_limit=50_000,
        shield_level="basic",
        features=["Shield basic", "1 агент", "50K токенов/мес"],
    ),
    "pro": PlanConfig(
        name="pro",
        display_name="⭐ Pro",
        price_rub=1490,
        max_agents=5,
        tokens_limit=500_000,
        shield_level="full",
        features=[
            "Shield полный",
            "5 агентов",
            "500K токенов/мес",
            "RLM Memory",
        ],
    ),
    "team": PlanConfig(
        name="team",
        display_name="🏢 Team",
        price_rub=4990,
        max_agents=20,
        tokens_limit=2_000_000,
        shield_level="full+shared",
        features=[
            "Shield полный",
            "20 агентов",
            "2M токенов/мес",
            "Shared Memory",
            "Audit Logs",
            "+990₽/user",
        ],
    ),
    "enterprise": PlanConfig(
        name="enterprise",
        display_name="🏛️ Enterprise",
        price_rub=49_900,
        max_agents=999_999,
        tokens_limit=999_999_999,
        shield_level="on-prem",
        features=[
            "Unlimited",
            "On-prem",
            "SLA 99.9%",
            "Dedicated support",
        ],
    ),
}


@dataclass
class BotConfig:
    """Bot configuration from environment."""

    bot_token: str = ""
    yookassa_shop_id: str = ""
    yookassa_secret: str = ""
    database_url: str = "sqlite+aiosqlite:///safeclaw.db"
    webhook_host: str = ""
    webhook_port: int = 8443
    admin_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables."""
        admin_str = os.getenv("SAFECLAW_ADMIN_IDS", "")
        admin_ids = [
            int(x.strip()) for x in admin_str.split(",") if x.strip().isdigit()
        ]
        return cls(
            bot_token=os.getenv("SAFECLAW_BOT_TOKEN", ""),
            yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
            yookassa_secret=os.getenv("YOOKASSA_SECRET", ""),
            database_url=os.getenv(
                "SAFECLAW_DB_URL",
                "sqlite+aiosqlite:///safeclaw.db",
            ),
            webhook_host=os.getenv("SAFECLAW_WEBHOOK_HOST", ""),
            webhook_port=int(os.getenv("SAFECLAW_WEBHOOK_PORT", "8443")),
            admin_ids=admin_ids,
        )
