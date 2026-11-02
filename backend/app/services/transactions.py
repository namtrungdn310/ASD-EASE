from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError


@contextmanager
def write_transaction(db):
    """Khoá ghi SQLite trước khi đọc, tránh hai Start cùng vượt kiểm tra."""
    try:
        db.execute(text("BEGIN IMMEDIATE"))
        yield
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "CONCURRENT_CONFLICT") from None
    except OperationalError:
        db.rollback()
        raise HTTPException(503, "STORAGE_UNAVAILABLE") from None
    except BaseException:
        db.rollback()
        raise
