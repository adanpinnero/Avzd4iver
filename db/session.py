from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from db import models  # noqa: F401 - register tables

DB_PATH = Path(__file__).resolve().parent.parent / "fleet.db"
ENGINE = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(ENGINE)
    _maybe_seed()


def get_session() -> Session:
    return Session(ENGINE)


def _maybe_seed() -> None:
    from db.seed import seed_all

    with Session(ENGINE) as s:
        has_users = s.exec(select(models.User).limit(1)).first() is not None
    if not has_users:
        seed_all()
