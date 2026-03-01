"""
等待至 8:00 (GMT+8) 後發送 Email - 2026-03-01
"""
import os
import sys
import time
import datetime

os.environ['TZ'] = 'Asia/Taipei'
time.tzset()

sys.path.insert(0, os.path.dirname(__file__))
from modules.email_sender import send_report_email

report_date = '2026-03-01'
pdf_path = os.path.join(os.path.dirname(__file__), 'reports', f'daily_report_{report_date}.pdf')
json_path = os.path.join(os.path.dirname(__file__), 'reports', f'raw_data_{report_date}.json')

# Verify files exist
for path in [pdf_path, json_path]:
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    print(f"OK: {path}")

# Wait until 8:00
now = datetime.datetime.now()
target = now.replace(hour=8, minute=0, second=0, microsecond=0)
if now < target:
    diff = (target - now).total_seconds()
    print(f"\n[{now.strftime('%H:%M:%S')}] 等待 {diff:.0f} 秒 ({diff/60:.1f} 分鐘) 至 08:00:00...")
    time.sleep(diff)
elif now > target:
    print(f"\n[{now.strftime('%H:%M:%S')}] 已過 8:00，立即發送...")

# Send at 8:00
now = datetime.datetime.now()
print(f"\n[{now.strftime('%H:%M:%S')}] 開始發送 Email...")
result = send_report_email(report_date, pdf_path, json_path)
print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 發送結果: {'成功' if result else '失敗'}")
