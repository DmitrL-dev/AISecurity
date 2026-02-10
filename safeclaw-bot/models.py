"""SafeClaw Bot — Database Models."""

import secrets
import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    Session,
    sessionmaker,
)


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class User(Base):
    """Registered SafeClaw user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    plan = Column(String(50), default="free", nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    tokens_used = Column(Integer, default=0)
    tokens_limit = Column(Integer, default=50_000)
    agents_used = Column(Integer, default=0)
    agents_limit = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    payments = relationship("Payment", back_populates="user")

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"sc_{secrets.token_hex(24)}"

    @property
    def usage_percent(self) -> float:
        """Token usage as percentage."""
        if self.tokens_limit <= 0:
            return 0.0
        return (self.tokens_used / self.tokens_limit) * 100

    @property
    def plan_emoji(self) -> str:
        """Emoji for current plan."""
        return {
            "free": "🆓",
            "pro": "⭐",
            "team": "🏢",
            "enterprise": "🏛️",
        }.get(self.plan, "❓")


class Payment(Base):
    """ЮKassa payment record."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    yookassa_id = Column(String(255), unique=True, nullable=True)
    amount_kopecks = Column(Integer, nullable=False)
    plan = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="payments")


# --- Database setup ---


def init_db(
    db_url: str = "sqlite:///safeclaw.db",
) -> sessionmaker:
    """Initialize database and return session factory."""
    engine = create_engine(db_url, echo=False)

    # Enable WAL mode for SQLite
    if "sqlite" in db_url:

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _rec):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def get_or_create_user(
    session: Session,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> tuple["User", bool]:
    """Get existing user or create new one.

    Returns (user, created) tuple.
    """
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        # Update username if changed
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        session.commit()
        return user, False

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        api_key=User.generate_api_key(),
        plan="free",
        tokens_limit=50_000,
        agents_limit=1,
    )
    session.add(user)
    session.commit()
    return user, True


def regenerate_api_key(session: Session, user: User) -> str:
    """Regenerate API key for user."""
    new_key = User.generate_api_key()
    user.api_key = new_key
    session.commit()
    return new_key
