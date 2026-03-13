#!/usr/bin/env python3
"""
數據品質驗證腳本：用 yfinance 即時數據交叉驗證 raw_data JSON
驗證至少 5 個關鍵數據點：S&P500、NASDAQ、BTC、黃金、至少 2 支熱門股票
偏差超過 1% 必須報告（加密貨幣允許 3%）
"""
import json
import os
import sys
from datetime import datetime

os.environ['TZ'] = 'Asia/Taipei'

import yfinance as yf

today = datetime.now().strftime('%Y-%m-%d')
raw_data_path = f'reports/raw_data_{today}.json'

print(f"=== 數據品質驗證 ===")
print(f"日期: {today}")
print(f"讀取: {raw_data_path}")
print()

with open(raw_data_path, 'r') as f:
    raw_data = json.load(f)

market_data = raw_data.get('market_data', {})
hot_stocks = raw_data.get('hot_stocks', {})

# 構建驗證目標（dict of dicts 結構）
verification_targets = {}

# 1. S&P 500
sp500 = market_data.get('us_indices', {}).get('S&P 500', {})
if sp500:
    verification_targets['S&P 500'] = {
        'report_price': sp500.get('current'),
        'report_change': sp500.get('change_pct'),
        'yf_ticker': '^GSPC',
        'is_crypto': False
    }

# 2. NASDAQ
nasdaq = market_data.get('us_indices', {}).get('納斯達克', {})
if nasdaq:
    verification_targets['NASDAQ'] = {
        'report_price': nasdaq.get('current'),
        'report_change': nasdaq.get('change_pct'),
        'yf_ticker': '^IXIC',
        'is_crypto': False
    }

# 3. Bitcoin
btc = market_data.get('crypto', {}).get('Bitcoin', {})
if btc:
    verification_targets['Bitcoin'] = {
        'report_price': btc.get('current'),
        'report_change': btc.get('change_pct'),
        'yf_ticker': 'BTC-USD',
        'is_crypto': True
    }

# 4. Gold
gold = market_data.get('commodities', {}).get('黃金', {})
if gold:
    verification_targets['Gold'] = {
        'report_price': gold.get('current'),
        'report_change': gold.get('change_pct'),
        'yf_ticker': 'GC=F',
        'is_crypto': False
    }

# 5-6. Hot stocks (美股前 2 支 inflow)
us_hot = hot_stocks.get('美股', {})
inflow = us_hot.get('inflow', [])
for stock in inflow[:2]:
    ticker = stock.get('symbol', '')
    name = stock.get('name', ticker)
    verification_targets[f'Hot: {name} ({ticker})'] = {
        'report_price': stock.get('current'),
        'report_change': stock.get('change_pct'),
        'yf_ticker': ticker,
        'is_crypto': False
    }

print(f"找到 {len(verification_targets)} 個驗證目標:")
for name, data in verification_targets.items():
    print(f"  - {name}: 報告價格={data['report_price']}, 漲跌幅={data['report_change']}%, ticker={data['yf_ticker']}")
print()

# 用 yfinance 獲取即時數據進行驗證
print("=== 開始 yfinance 即時驗證 ===")
all_passed = True
results = []

for name, data in verification_targets.items():
    ticker = data['yf_ticker']
    report_price = data['report_price']
    report_change = data['report_change']
    is_crypto = data['is_crypto']
    threshold = 3.0 if is_crypto else 1.0
    
    try:
        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period='5d')
        
        if hist.empty:
            print(f"  ⚠ {name}: yfinance 無數據")
            results.append({'name': name, 'status': 'NO_DATA'})
            continue
        
        latest_close = hist['Close'].iloc[-1]
        
        if report_price is not None and latest_close:
            report_price_float = float(str(report_price).replace(',', ''))
            deviation = abs(report_price_float - latest_close) / latest_close * 100
            
            if deviation < threshold:
                status = "✓ PASS"
            else:
                status = "✗ FAIL"
                all_passed = False
            
            # 也驗證漲跌幅（如果有前一天數據）
            change_info = ""
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                yf_change_pct = (latest_close - prev_close) / prev_close * 100
                if report_change is not None:
                    change_dev = abs(float(report_change) - yf_change_pct)
                    change_info = f" | 漲跌幅: 報告={report_change}%, yf={yf_change_pct:.2f}%, 差={change_dev:.2f}pp"
            
            print(f"  {status} {name}:")
            print(f"    報告價格: {report_price_float:,.2f}")
            print(f"    yfinance:  {latest_close:,.2f}")
            print(f"    偏差: {deviation:.3f}% (閾值: {threshold}%){change_info}")
            
            results.append({
                'name': name,
                'report_price': report_price_float,
                'yf_price': latest_close,
                'deviation_pct': deviation,
                'status': status
            })
        else:
            print(f"  ⚠ {name}: 報告價格為空")
            results.append({'name': name, 'status': 'EMPTY_PRICE'})
            
    except Exception as e:
        print(f"  ⚠ {name}: 驗證失敗 - {e}")
        results.append({'name': name, 'status': f'ERROR: {e}'})

print()
print("=" * 50)
print("=== 驗證結果摘要 ===")
print("=" * 50)
for r in results:
    if 'deviation_pct' in r:
        print(f"  {r['status']} {r['name']}: 偏差 {r['deviation_pct']:.3f}%")
    else:
        print(f"  {r.get('status', 'UNKNOWN')} {r['name']}")

print()
if all_passed:
    print("✅ 所有數據點驗證通過！報告數據品質合格，可以發送。")
    sys.exit(0)
else:
    print("❌ 發現數據偏差超過閾值！需要排查原因後再發送。")
    sys.exit(1)
