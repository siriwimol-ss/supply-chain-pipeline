from pathlib import Path
import pandas as pd
from sqlalchemy import text
from db import get_engine

CSV_PATH = Path("data/supply_chain_disruption_recovery.csv")
TABLE = "supply_chain_disruption_recovery"   # ตั้งชื่อตารางตามชื่อไฟล์ Kaggle


def main():
    engine = get_engine()

    # 1) อ่าน CSV เข้ามาเป็น DataFrame (ตารางในหน่วยความจำ)
    df = pd.read_csv(CSV_PATH)
    print(f"[ingest] อ่าน CSV ได้ {len(df):,} แถว, {df.shape[1]} คอลัมน์")

    # 2) สร้าง schema ชื่อ raw_data ถ้ายังไม่มี
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw_data"))

    # 3) เขียน DataFrame ลงฐานข้อมูลเป็นตาราง
    df.to_sql(
        TABLE, engine, schema="raw_data",
        if_exists="replace", index=False,
        chunksize=5000, method="multi",
    )

    # 4) ตรวจว่าเข้ามาในฐานข้อมูลครบไหมโดยนับแถวกลับมาจากฐานข้อมูล
    with engine.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM raw_data.{TABLE}")).scalar()
    print(f"[ingest] โหลดเข้า raw_data.{TABLE} สำเร็จ {n:,} แถว")


if __name__ == "__main__":
    main()