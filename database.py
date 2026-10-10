from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from settings import settings

engine= create_engine(settings.DATABASE_URL)

SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit= False)

Base= declarative_base()


def get_db():
    db=SessionLocal()
    try: 
        yield db
    finally : 
        db.close()

       