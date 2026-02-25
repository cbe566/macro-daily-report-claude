#!/bin/bash
# ============================================================
# 每日宏觀資訊報告 - 自動排程設定
# 
# 執行時間：北京時間（UTC+8）每週一至週五 08:30
# 對應 UTC 時間：00:30
# 
# 用法：
#   chmod +x setup_cron.sh && ./setup_cron.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_SCRIPT="${SCRIPT_DIR}/run_daily.sh"

# 建立每日執行腳本
cat > "${RUN_SCRIPT}" << 'DAILY_SCRIPT'
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
DAILY_SCRIPT

chmod +x "${RUN_SCRIPT}"
echo "已建立執行腳本: ${RUN_SCRIPT}"

# 設定 cron job
# 北京時間 08:30 = UTC 00:30，週一到週五
CRON_ENTRY="30 0 * * 1-5 ${RUN_SCRIPT}"

# 移除舊的相關 cron（如有）
crontab -l 2>/dev/null | grep -v "run_daily.sh" | grep -v "daily-macro-report" > /tmp/crontab_clean 2>/dev/null || true

# 加入新的 cron
echo "${CRON_ENTRY}" >> /tmp/crontab_clean
crontab /tmp/crontab_clean
rm /tmp/crontab_clean

echo ""
echo "Cron 排程已設定："
echo "  時間：北京時間 週一至週五 08:30（UTC 00:30）"
echo "  腳本：${RUN_SCRIPT}"
echo ""
echo "當前 crontab："
crontab -l
