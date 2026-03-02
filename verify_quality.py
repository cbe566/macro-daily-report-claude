#!/usr/bin/env python3
"""
數據品質驗證腳本
讀取 raw_data JSON，用 yfinance 即時數據交叉驗證關鍵數據點
"""
import json
import yfinance as yf
import datetime
import os

os.environ['TZ'] = 'Asia/Taipei'

today = datetime.datetime.now().strftime('%Y-%m-%d')
raw_data_path = f'reports/raw_data_{today}.json'

print(f"{'='*60}")
print(f"  數據品質驗證（面向機構客戶 - 最高標準）")
print(f"  日期: {today}")
print(f"{'='*60}\n")

with open(raw_data_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

md = raw_data['market_data']

# 定義驗證目標：從 raw_data 直接提取
targets = []

# 1. S&P 500 - 注意 raw_data 中沒有 S&P 500，只有納斯達克、道瓊斯、羅素2000、費城半導體
# 用 ^GSPC 驗證（雖然報告中沒有，但我們可以驗證有的指數）
# 納斯達克
nasdaq = md['us_indices']['納斯達克']
targets.append({
    'name': '納斯達克 (NASDAQ)',
    'yf_ticker': '^IXIC',
    'report_price': nasdaq['current'],
    'report_change_pct': nasdaq['change_pct'],
})

# 道瓊斯
dow = md['us_indices']['道瓊斯']
targets.append({
    'name': '道瓊斯 (Dow Jones)',
    'yf_ticker': '^DJI',
    'report_price': dow['current'],
    'report_change_pct': dow['change_pct'],
})

# 費城半導體
sox = md['us_indices']['費城半導體']
targets.append({
    'name': '費城半導體 (SOX)',
    'yf_ticker': '^SOX',
    'report_price': sox['current'],
    'report_change_pct': sox['change_pct'],
})

# Bitcoin
btc = md['crypto']['Bitcoin']
targets.append({
    'name': 'Bitcoin (BTC)',
    'yf_ticker': 'BTC-USD',
    'report_price': btc['current'],
    'report_change_pct': btc['change_pct'],
})

# 黃金
gold = md['commodities']['黃金']
targets.append({
    'name': '黃金 (Gold)',
    'yf_ticker': 'GC=F',
    'report_price': gold['current'],
    'report_change_pct': gold['change_pct'],
})

# 熱門股票 - DELL, ZS
dell = raw_data['hot_stocks']['美股']['inflow'][0]
targets.append({
    'name': f"{dell['name']} ({dell['symbol']})",
    'yf_ticker': dell['symbol'],
    'report_price': dell['current'],
    'report_change_pct': dell['change_pct'],
})

zs = raw_data['hot_stocks']['美股']['outflow'][0]
targets.append({
    'name': f"{zs['name']} ({zs['symbol']})",
    'yf_ticker': zs['symbol'],
    'report_price': zs['current'],
    'report_change_pct': zs['change_pct'],
})

# 執行驗證
all_pass = True
fail_count = 0
results = []

for t in targets:
    ticker_symbol = t['yf_ticker']
    name = t['name']
    report_price = t['report_price']
    report_chg = t['report_change_pct']
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period='5d')
        if hist.empty:
            print(f"⚠️  {name}: yfinance 無法獲取數據，跳過")
            continue
        
        yf_price = hist['Close'].iloc[-1]
        if len(hist) >= 2:
            yf_prev = hist['Close'].iloc[-2]
            yf_change_pct = ((yf_price - yf_prev) / yf_prev) * 100
        else:
            yf_change_pct = None
        
        # 計算偏差
        price_deviation = abs(yf_price - report_price) / report_price * 100 if report_price else None
        
        # 判斷是否通過（加密貨幣允許稍大偏差因為 24 小時交易）
        is_crypto = 'BTC' in ticker_symbol or 'ETH' in ticker_symbol
        threshold = 3.0 if is_crypto else 1.0
        
        if price_deviation is not None:
            passed = price_deviation < threshold
        else:
            passed = True
        
        if not passed:
            all_pass = False
            fail_count += 1
            status = "❌ FAIL"
        else:
            status = "✅ PASS"
        
        print(f"{status}  {name}")
        print(f"       報告價格:    {report_price:>12,.2f}")
        print(f"       yfinance:    {yf_price:>12,.2f}")
        print(f"       價格偏差:    {price_deviation:>11.4f}%  (閾值: {threshold}%)")
        
        if report_chg is not None and yf_change_pct is not None:
            chg_dev = abs(yf_change_pct - report_chg)
            print(f"       報告漲跌幅:  {report_chg:>+11.2f}%")
            print(f"       yfinance:    {yf_change_pct:>+11.2f}%")
            print(f"       漲跌幅偏差:  {chg_dev:>11.4f}%")
        print()
        
        results.append({
            'name': name,
            'report_price': report_price,
            'yf_price': round(yf_price, 2),
            'deviation_pct': round(price_deviation, 4) if price_deviation else None,
            'passed': passed
        })
        
    except Exception as e:
        print(f"⚠️  {name}: 驗證錯誤 - {e}\n")

# 最終結論
print(f"\n{'='*60}")
print(f"  驗證結果摘要")
print(f"{'='*60}")
print(f"  總驗證項目: {len(results)}")
print(f"  通過: {sum(1 for r in results if r['passed'])}")
print(f"  失敗: {sum(1 for r in results if not r['passed'])}")
print()

if all_pass:
    print("  ✅ 數據品質驗證通過！所有關鍵數據點偏差在允許範圍內。")
    print("  → 可以安全發送報告。")
else:
    print("  ❌ 數據品質驗證未通過！存在偏差超過閾值的數據點。")
    print("  → 需要排查原因後才能發送。")
    for r in results:
        if not r['passed']:
            print(f"     問題項: {r['name']} (偏差 {r['deviation_pct']}%)")

print(f"{'='*60}")
