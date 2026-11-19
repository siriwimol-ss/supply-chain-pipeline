import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()  # เพื่อใช้อ่านค่ารหัสผ่านจากไฟล์ .env --> อ่านชื่อผู้ใช้ รหัสผ่าน ฯลฯ จากไฟล์ .env


def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:"
        f"{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    return create_engine(url)