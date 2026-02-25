#!/bin/bash
# 每日宏觀資訊報告 - 執行腳本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

DATE=$(TZ='Asia/Taipei' date +%Y-%m-%d)
LOG_FILE="${LOG_DIR}/report_${DATE}.log"

echo "========================================" >> "${LOG_FILE}"
echo "開始生成報告: $(TZ='Asia/Taipei' date)" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

# 1. 生成報告（收集數據 + AI 分析 + Markdown）
python3 run_report.py daily >> "${LOG_FILE}" 2>&1

# 2. 生成 PDF
python3 generate_pdf.py "${DATE}" >> "${LOG_FILE}" 2>&1

# 3. 發送郵件
PDF_PATH="${SCRIPT_DIR}/reports/daily_report_${DATE}.pdf"
JSON_PATH="${SCRIPT_DIR}/reports/raw_data_${DATE}.json"

if [ -f "${PDF_PATH}" ]; then
    python3 -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.email_sender import send_report_email
send_report_email('${DATE}', '${PDF_PATH}', '${JSON_PATH}')
" >> "${LOG_FILE}" 2>&1
    echo "郵件發送完成" >> "${LOG_FILE}"
else
    echo "ERROR: PDF 不存在: ${PDF_PATH}" >> "${LOG_FILE}"
fi

echo "========================================" >> "${LOG_FILE}"
echo "報告流程結束: $(TZ='Asia/Taipei' date)" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"
