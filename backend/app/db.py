import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

DB_URL = os.environ.get('ROBOLN_DATABASE_URL', 'sqlite:///./roboln_dev.db')
kwargs = {'connect_args': {'check_same_thread': False}} if DB_URL.startswith('sqlite') else {}
engine = create_engine(DB_URL, pool_pre_ping=True, **kwargs)
if DB_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def enable_fk(conn, _record):
        conn.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
