import subprocess
import sys
import time

# ลำดับงานของ pipeline
STEPS = ["ingest.py", "transform.py", "publish.py"]


def main():
    t0 = time.time()

    for step in STEPS:
        print(f"\n===== รัน {step} =====")
        t_step = time.time()
        try:
            # ใช้ Python ตัวเดียวกับที่กำลังรันอยู่ (ตัวใน venv)
            subprocess.run([sys.executable, step], check=True)
        except subprocess.CalledProcessError:
            print(f"\n[ERROR] {step} ล้มเหลว หยุด pipeline")
            sys.exit(1)
        print(f"[OK] {step} เสร็จใน {time.time() - t_step:.1f} วินาที")

    print(f"\n[DONE] Pipeline ทั้งหมดเสร็จใน {time.time() - t0:.1f} วินาที")


if __name__ == "__main__":
    main()