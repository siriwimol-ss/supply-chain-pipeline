import os
import json
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from db import get_engine

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

TABLES = ["fact_disruptions", "agg_by_type", "agg_backup_supplier",
          "agg_response_severity", "agg_supplier_tier", "agg_severity_loss"]

CHUNK = 2000   # ส่งทีละ 2,000 แถว


def upload(sh, name, df):
    # แปลงตารางเป็นลิสต์ที่ส่งขึ้น Google ได้ (ค่าว่างกลายเป็น null)
    values = [df.columns.tolist()] + json.loads(df.to_json(orient="values"))

    # หาแท็บชื่อนี้ ถ้ามีให้ล้างของเก่า ถ้าไม่มีให้สร้างใหม่
    try:
        ws = sh.worksheet(name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1, cols=1)

    # ขยายแท็บให้พอดีกับข้อมูล
    ws.resize(rows=len(values), cols=len(values[0]))

    # ส่งทีละก้อน
    for start in range(0, len(values), CHUNK):
        chunk = values[start:start + CHUNK]
        ws.update(range_name=f"A{start + 1}", values=chunk)
        done = min(start + CHUNK, len(values))
        print(f"   - {name}: ส่งแล้ว {done:,}/{len(values):,} แถว")
        time.sleep(1.5)   # เว้นจังหวะ กัน Google จำกัดจำนวนคำสั่ง


def main():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_FILE"), scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(os.getenv("GOOGLE_SHEET_ID"))
    engine = get_engine()

    # อ่านตารางสุดท้ายจาก schema production แล้วส่งขึ้น Google Sheets
    for t in TABLES:
        df = pd.read_sql(f"SELECT * FROM production.{t}", engine)
        print(f"[publish] {t}: {len(df):,} แถว x {df.shape[1]} คอลัมน์")
        upload(sh, t, df)

    print("[publish] เสร็จสิ้น")


if __name__ == "__main__":
    main()