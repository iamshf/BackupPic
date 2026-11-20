from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

def get_engine(db_url: str):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        echo=False
    )
    return engine

def get_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)

class DbSessionCtx:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self):
        self.session = self.session_factory()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
            self.session.close()
