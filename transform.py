import numpy as np
import pandas as pd
from sqlalchemy import text
from db import get_engine

RAW_TABLE = "raw_data.supply_chain_disruption_recovery"

TEXT_COLS = ["disruption_id", "disruption_type", "industry", "supplier_region",
             "supplier_size", "response_type"]
NUM_COLS = ["supplier_tier", "disruption_severity", "production_impact_pct",
            "revenue_loss_usd", "response_time_days",
            "partial_recovery_days", "full_recovery_days"]
BOOL_COLS = ["has_backup_supplier", "permanent_supplier_change"]


# ---------- 3.1 CLEANING ----------
def clean(df):
    df = df.copy()
    before = len(df)

    # ตัดช่องว่างหัวท้ายของข้อความ
    for c in TEXT_COLS:
        df[c] = df[c].astype(str).str.strip()

    # ลบแถวซ้ำ (ดูจาก disruption_id)
    df = df.drop_duplicates(subset="disruption_id")

    # บังคับชนิดข้อมูลให้ถูกต้อง
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in BOOL_COLS:
        df[c] = df[c].astype(bool)

    # ตัดแถวที่ข้อมูลสำคัญหาย (ชุดนี้ไม่มี แต่ pipeline ควรรับมือได้)
    df = df.dropna(subset=NUM_COLS + TEXT_COLS)

    # ค่าต้องอยู่ในช่วงที่สมเหตุสมผล
    df["production_impact_pct"] = df["production_impact_pct"].clip(0, 100)
    df = df[df["revenue_loss_usd"] >= 0]

    # คอลัมน์ที่ควรเป็นจำนวนเต็ม
    for c in ["supplier_tier", "disruption_severity", "response_time_days",
              "partial_recovery_days", "full_recovery_days"]:
        df[c] = df[c].astype(int)

    # ตรวจความสอดคล้องของข้อมูล (แค่รายงาน ไม่ลบ)
    bad_order = (df["partial_recovery_days"] > df["full_recovery_days"]).sum()
    slow_start = (df["response_time_days"] > df["partial_recovery_days"]).sum()
    print(f"[clean] แถวก่อน/หลัง: {before:,} -> {len(df):,}")
    print(f"[clean] partial > full: {bad_order:,} แถว")
    print(f"[clean] response_time > partial: {slow_start:,} แถว (บันทึกไว้ ไม่ลบ)")
    return df


# ---------- 3.2 TRANSFORMATION ----------
def add_features(df):
    df = df.copy()
    df["supplier_tier_label"] = "Tier " + df["supplier_tier"].astype(str)
    df["backup_label"] = np.where(df["has_backup_supplier"], "With Backup", "No Backup")
    df["severity_group"] = df["disruption_severity"].map({
        1: "1-Low", 2: "2-Medium", 3: "2-Medium", 4: "3-High", 5: "4-Critical"})
    df["is_high_severity"] = df["disruption_severity"] >= 4
    df["revenue_loss_million"] = (df["revenue_loss_usd"] / 1e6).round(3)
    df["recovery_gap_days"] = df["full_recovery_days"] - df["partial_recovery_days"]
    df["permanent_change_flag"] = df["permanent_supplier_change"].astype(int)

    bins = [0, 1e5, 1e6, 1e7, np.inf]
    labels = ["1) < $100K", "2) $100K-1M", "3) $1M-10M", "4) > $10M"]
    df["loss_bucket"] = pd.cut(df["revenue_loss_usd"], bins=bins,
                               labels=labels, include_lowest=True).astype(str)
    return df


# ---------- 3.3 AGGREGATION ----------
def build_aggregates(df):
    out = {}

    # ข้อ 1: ประเภทเหตุการณ์ไหนสร้างความเสียหายมากสุด
    out["agg_by_type"] = (
        df.groupby("disruption_type")
          .agg(events=("disruption_id", "count"),
               total_revenue_loss_million=("revenue_loss_million", "sum"),
               avg_revenue_loss_million=("revenue_loss_million", "mean"),
               median_revenue_loss_million=("revenue_loss_million", "median"),
               avg_production_impact_pct=("production_impact_pct", "mean"))
          .round(2).reset_index()
          .sort_values("total_revenue_loss_million", ascending=False)
    )

    # ข้อ 2: มี Backup supplier ช่วยให้ฟื้นตัวเร็วขึ้นไหม
    out["agg_backup_supplier"] = (
        df.groupby(["industry", "backup_label"])
          .agg(events=("disruption_id", "count"),
               avg_partial_recovery_days=("partial_recovery_days", "mean"),
               avg_full_recovery_days=("full_recovery_days", "mean"),
               median_full_recovery_days=("full_recovery_days", "median"))
          .round(1).reset_index()
    )

    # ข้อ 3: กลยุทธ์ไหนฟื้นเร็วสุดเมื่อความรุนแรงสูง
    out["agg_response_severity"] = (
        df.groupby(["response_type", "severity_group"])
          .agg(events=("disruption_id", "count"),
               avg_response_time_days=("response_time_days", "mean"),
               avg_full_recovery_days=("full_recovery_days", "mean"),
               median_full_recovery_days=("full_recovery_days", "median"))
          .round(1).reset_index()
    )

    # ข้อ 4: Supplier Tier ไหนเกิดเหตุการณ์บ่อย / ฟื้นช้า
    tier = (
        df.groupby("supplier_tier_label")
          .agg(events=("disruption_id", "count"),
               avg_severity=("disruption_severity", "mean"),
               avg_revenue_loss_million=("revenue_loss_million", "mean"),
               avg_full_recovery_days=("full_recovery_days", "mean"))
          .round(2).reset_index()
    )
    tier["share_pct"] = (tier["events"] / tier["events"].sum() * 100).round(2)
    out["agg_supplier_tier"] = tier

    # ข้อ 5: ความรุนแรงและมูลค่าความเสียหายระดับไหนทำให้เปลี่ยน supplier ถาวร
    sev = (
        df.groupby(["disruption_severity", "loss_bucket"])
          .agg(events=("disruption_id", "count"),
               permanent_changes=("permanent_change_flag", "sum"))
          .reset_index()
    )
    sev["permanent_change_rate_pct"] = (
        sev["permanent_changes"] / sev["events"] * 100).round(2)
    out["agg_severity_loss"] = sev

    return out


def main():
    engine = get_engine()

    # อ่านข้อมูลดิบจาก raw_data เข้ามาเป็น DataFrame (ตามที่อาจารย์สั่ง)
    raw = pd.read_sql(f"SELECT * FROM {RAW_TABLE}", engine)
    print(f"[transform] อ่านจาก raw_data ได้ {len(raw):,} แถว")

    fact = add_features(clean(raw))
    tables = {"fact_disruptions": fact, **build_aggregates(fact)}

    # เขียนกลับเป็นตารางใหม่ใน schema production
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS production"))

    for name, df in tables.items():
        df.to_sql(name, engine, schema="production", if_exists="replace",
                  index=False, chunksize=5000, method="multi")
        print(f"[transform] เขียน production.{name}: {len(df):,} แถว x {df.shape[1]} คอลัมน์")


if __name__ == "__main__":
    main()