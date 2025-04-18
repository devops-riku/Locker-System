from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

load_dotenv()

DRIVERNAME = os.getenv("DBDRIVERNAME")
USERNAME = os.getenv("DBUSERNAME")
PASSWORD = os.getenv("DBPASSWORD")
HOST = os.getenv("DBHOST")
PORT = os.getenv("DBPORT")
DBNAME = os.getenv("DBNAME")

DATABASE_URL = f"postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
# DATABASE_URL = URL.create(
#                 drivername=DRIVERNAME,
#                 username=USERNAME,
#                 password=PASSWORD,
#                 host=HOST,
#                 database=DBNAME,
#                 port=PORT)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
db_session = SessionLocal()


