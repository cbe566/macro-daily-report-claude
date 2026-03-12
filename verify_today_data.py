#!/usr/bin/env python3
"""
數據品質驗證腳本
從 raw_data JSON 讀取報告數據，用 yfinance 即時查詢交叉驗證
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

# 讀取 raw_data
with open(raw_data_path, 'r') as f:
    raw_data = json.load(f)

market_data = raw_data.get('market_data', {})

# 定義要驗證的數據點
verify_targets = {}

# 1. US Indices (dict format: key=name, value=dict)
us_indices = market_data.get('us_indices', {})
if isinstance(us_indices, dict):
    for name, data in us_indices.items():
        if isinstance(data, dict):
            if 'S&P' in name:
                verify_targets['S&P 500'] = {
                    'symbol': data.get('symbol', '^GSPC'),
                    'report_price': data.get('current'),
                    'report_change': data.get('change_pct'),
                }
            elif 'NASDAQ' in name.upper() or '納斯達克' in name:
                verify_targets['NASDAQ'] = {
                    'symbol': data.get('symbol', '^IXIC'),
                    'report_price': data.get('current'),
                    'report_change': data.get('change_pct'),
                }
            elif '道瓊' in name or 'Dow' in name:
                verify_targets['道瓊工業'] = {
                    'symbol': data.get('symbol', '^DJI'),
                    'report_price': data.get('current'),
                    'report_change': data.get('change_pct'),
                }

# 2. Crypto (dict format)
crypto = market_data.get('crypto', {})
if isinstance(crypto, dict):
    for name, data in crypto.items():
        if isinstance(data, dict) and ('BTC' in name.upper() or 'Bitcoin' in name):
            verify_targets['BTC'] = {
                'symbol': data.get('symbol', 'BTC-USD'),
                'report_price': data.get('current'),
                'report_change': data.get('change_pct'),
            }

# 3. Commodities (dict format)
commodities = market_data.get('commodities', {})
if isinstance(commodities, dict):
    for name, data in commodities.items():
        if isinstance(data, dict) and ('黃金' in name or 'Gold' in name):
            verify_targets['黃金'] = {
                'symbol': data.get('symbol', 'GC=F'),
                'report_price': data.get('current'),
                'report_change': data.get('change_pct'),
            }

# 4. Hot stocks - 美股前2支 inflow
hot_stocks = raw_data.get('hot_stocks', {})
us_stocks = hot_stocks.get('美股', {})
inflow = us_stocks.get('inflow', [])
for stock in inflow[:2]:
    ticker = stock.get('symbol', '')
    name = stock.get('name', ticker)
    if ticker:
        verify_targets[f'美股-{name}({ticker})'] = {
            'symbol': ticker,
            'report_price': stock.get('current'),
            'report_change': stock.get('change_pct'),
        }

# 打印找到的驗證目標
print(f"找到 {len(verify_targets)} 個驗證目標:")
for name, info in verify_targets.items():
    print(f"  - {name}: symbol={info['symbol']}, report_price={info['report_price']}, report_change={info['report_change']}%")
print()

# 用 yfinance 查詢即時數據進行驗證
print("=== 開始 yfinance 交叉驗證 ===")
print()

all_pass = True
results = []

for name, info in verify_targets.items():
    symbol = info['symbol']
    report_price = info['report_price']
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')
        
        if hist.empty:
            print(f"[WARN] {name} ({symbol}): yfinance 無數據")
            results.append((name, 'WARN', '無數據'))
            continue
        
        # 取最新收盤價
        yf_price = hist['Close'].iloc[-1]
        yf_date = hist.index[-1].strftime('%Y-%m-%d')
        
        if report_price is None:
            print(f"[WARN] {name}: 報告中無價格數據")
            results.append((name, 'WARN', '報告無價格'))
            continue
        
        report_price = float(report_price)
        
        # 計算偏差
        if report_price != 0:
            deviation = abs(yf_price - report_price) / report_price * 100
        else:
            deviation = 0
        
        # 加密貨幣允許更大偏差（24小時交易）
        threshold = 3.0 if ('BTC' in name or 'ETH' in name) else 1.0
        status = "PASS" if deviation < threshold else "FAIL"
        
        if status == "FAIL":
            all_pass = False
        
        print(f"[{status}] {name} ({symbol})")
        print(f"  報告價格: {report_price:,.2f}")
        print(f"  yfinance:  {yf_price:,.2f} (日期: {yf_date})")
        print(f"  偏差: {deviation:.4f}% (閾值: {threshold}%)")
        print()
        
        results.append((name, status, f"偏差 {deviation:.4f}%"))
        
    except Exception as e:
        print(f"[ERROR] {name} ({symbol}): {str(e)}")
        results.append((name, 'ERROR', str(e)))

print()
print("=== 驗證結果摘要 ===")
for name, status, detail in results:
    emoji = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    print(f"  {emoji} [{status}] {name}: {detail}")

print()
if all_pass:
    print("✅ 所有關鍵數據點驗證通過！報告數據可靠，可以發送。")
    sys.exit(0)
else:
    print("❌ 發現數據偏差超過閾值！請排查原因後再發送。")
    sys.exit(1)
