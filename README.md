# Supply Chain Disruption & Recovery — Data Pipeline

โปรเจกต์ Mini Project: สร้างไปป์ไลน์ข้อมูลอัตโนมัติ จาก Kaggle Dataset ไปจนถึง Dashboard

**สมาชิก:** สิริวิมล สัมฤทธิ์, ภูธดา พงษ์สุขกุล

**Dashboard:**  https://datastudio.google.com/reporting/59dd670d-bc0f-48e6-95bf-791ce315e2b3

## ภาพรวม

ชุดข้อมูล [Supply Chain Disruption and Recovery Dataset](https://www.kaggle.com/datasets/likithagedipudi/supply-chain-disruption-and-recovery-dataset) (ข้อมูลจำลอง 100,000 เหตุการณ์, 15 คอลัมน์)
ใช้วิเคราะห์ความเสียหาย กลยุทธ์รับมือ และระยะเวลาฟื้นตัวของห่วงโซ่อุปทาน

## สถาปัตยกรรม

```
Kaggle CSV -> ingest.py -> PostgreSQL (raw_data)
           -> transform.py -> PostgreSQL (production)
           -> publish.py -> Google Sheets -> Data Studio Dashboard
```

ทั้งหมดรันต่อเนื่องด้วยคำสั่งเดียว: `python3 run_pipeline.py`

## เครื่องมือ

Python (pandas, SQLAlchemy, gspread), PostgreSQL 16 บน Docker, Google Sheets, Data Studio

## คำถามทางธุรกิจ

1  ประเภทของภัยพิบัติหรืออุบัติเหตุใด (Disruption Type) ที่ส่งผลกระทบต่อความเสียหายทางมูลค่ารายได้ (Revenue Loss)และทำให้กำลังการผลิตลดลง (Production Impact) มากที่สุดในภาพรวม?
2. การมีซัพพลายเออร์สำรอง (Has Backup Supplier) ช่วยร่นระยะเวลาในการฟื้นฟูกำลังการผลิตให้กลับคืนสู่ภาวะปกติ (Full Recovery Days) ได้จริงหรือไม่ และต่างกันมากแค่ไหน?
3. กลยุทธ์การรับมือประเภทใด (Response Type เช่น Alternative Supplier, Inventory Buffer หรือ Production Reroute) ที่ช่วยให้องค์กรสามารถฟื้นฟูกำลังการผลิตได้เร็วที่สุดเมื่อเผชิญกับความรุนแรงระดับสูง?
4.  ตำแหน่งชั้นของซัพพลายเออร์ (Supplier Tier 1 ถึง 4) มีความสัมพันธ์กับระยะเวลาหรืออัตราการเกิดความผิดปกติในห่วงโซ่อุปทานอย่างไร (ปัญหามักเกิดจากต้นน้ำหรือปลายน้ำมากกว่ากัน)?
5.  เหตุการณ์ความรุนแรงระดับใด (Disruption Severity) และสร้างความเสียหายต่อรายได้เท่าไหร่ ที่ส่งผลให้บริษัทตัดสินใจเปลี่ยนตัวซัพพลายเออร์แบบถาวร (Permanent Supplier Change) มากที่สุด?

## โครงสร้างไฟล์

|                  ไฟล์                  |                           หน้าที่                          |
|---------------------------------------|---------------------------------------------------------|
| `docker-compose.yml`                  |  เปิดฐานข้อมูล PostgreSQL                                  |
| `db.py`                               |  ตัวช่วยเชื่อมต่อฐานข้อมูล                                     |
| `ingest.py`                           |  โหลด CSV เข้า schema `raw_data`                         |
| `transform.py`                        |  ล้างข้อมูล สร้างฟีเจอร์ สรุปยอด แล้วเขียนลง schema `production` |
| `publish.py`                          |  ส่งตารางใน `production` ขึ้น Google Sheets                |
| `run_pipeline.py`                     |  รันทุกขั้นตอนต่อเนื่อง                                        |

## วิธีรัน

**สิ่งที่ต้องมี:** Python 3.9 ขึ้นไป, Docker Desktop, Git, บัญชี Google

1. โคลนโปรเจกต์
   ```bash
   git clone https://github.com/siriwimol-ss/supply-chain-pipeline
   cd supply-chain-pipeline
   ```
2. ดาวน์โหลด `supply_chain_disruption_recovery.csv` จาก Kaggle (ลิงก์ด้านบน) แล้ววางในโฟลเดอร์ `data/`
3. สร้าง virtual environment และติดตั้งไลบรารี
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. ตั้งค่าไฟล์ `.env`: คัดลอก `.env.example` เป็น `.env` แล้วใส่ค่าให้ครบ
   ```bash
   cp .env.example .env
   ```
5. ตั้งค่า Google API
   - สร้างโปรเจกต์ใน Google Cloud Console แล้วเปิดใช้ Google Sheets API และ Google Drive API
   - สร้าง Service Account และดาวน์โหลดกุญแจ JSON ตั้งชื่อ `credentials.json` วางในโฟลเดอร์โปรเจกต์
   - สร้าง Google Sheet ใหม่ แชร์ให้อีเมลของ Service Account (`client_email` ในไฟล์กุญแจ) กำหนดสิทธิ์ Editor
   - คัดลอก Sheet ID จาก URL ใส่ใน `GOOGLE_SHEET_ID` ของไฟล์ `.env`
6. เปิดฐานข้อมูล
   ```bash
   docker compose up -d
   ```
7. รัน pipeline ทั้งหมดด้วยคำสั่งเดียว
   ```bash
   python3 run_pipeline.py
   ```

## ข้อควรระวัง

- **ห้าม commit** `credentials.json` และ `.env` (อยู่ใน `.gitignore` แล้ว)
- Google Sheets จำกัด 10 ล้านเซลล์ต่อไฟล์ โปรเจกต์นี้ใช้ประมาณ 2.3 ล้านเซลล์ และส่งข้อมูลทีละ 2,000 แถว
- ข้อมูลเป็นข้อมูลจำลอง (synthetic) ผลวิเคราะห์เป็นความสัมพันธ์ ไม่ใช่การพิสูจน์เหตุและผล