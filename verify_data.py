"""
完整數據交叉驗證腳本
用 yfinance 驗證 PDF 報告中的每一個數據點
"""
import yfinance as yf
import json
import os

os.environ['TZ'] = 'Asia/Taipei'

# ========== 1. 指數驗證 ==========
print("=" * 60)
print("1. 指數驗證")
print("=" * 60)

indices = {
    # 亞洲
    "韓國KOSPI": ("^KS11", 6198.88, 3.84),
    "日經225": ("^N225", 58922.92, 2.79),
    "台灣加權": ("^TWII", 35413.07, 2.05),
    "澳洲ASX200": ("^AXJO", 9178.80, 1.73),
    "深證成指": ("399001.SZ", 14475.87, 1.29),
    "上證綜指": ("000001.SS", 4147.23, 0.72),
    "香港恆生": ("^HSI", 26765.72, 0.66),
    # 歐洲
    "英國FTSE100": ("^FTSE", 10806.41, 1.18),
    "歐洲STOXX50": ("^STOXX50E", 6173.32, 0.93),
    "德國DAX": ("^GDAXI", 25175.94, 0.76),
    "法國CAC40": ("^FCHI", 8559.07, 0.47),
    "瑞士SMI": ("^SSMI", 13977.10, -0.14),
    # 美國
    "費城半導體": ("^SOX", 8467.43, 1.62),
    "納斯達克": ("^IXIC", 23152.08, 1.26),
    "S&P500": ("^GSPC", 6946.13, 0.81),
    "道瓊斯": ("^DJI", 49482.15, 0.63),
    "羅素2000": ("^RUT", 2663.33, 0.41),
}

errors = []
warnings = []

for name, (symbol, pdf_close, pdf_pct) in indices.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            warnings.append(f"  ⚠️ {name} ({symbol}): 數據不足")
            continue
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff = abs(yf_close - pdf_close)
        close_pct_diff = (close_diff / pdf_close) * 100 if pdf_close else 0
        pct_diff = abs(yf_pct - pdf_pct)
        
        status = "✅" if close_pct_diff < 0.5 and pct_diff < 0.3 else "❌"
        if status == "❌":
            errors.append(f"  {name}: PDF={pdf_close} ({pdf_pct:+.2f}%) vs YF={yf_close:.2f} ({yf_pct:+.2f}%)")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: PDF={pdf_close} ({pdf_pct:+.2f}%) | YF={yf_close:.2f} ({yf_pct:+.2f}%) | Date={date_str} | Δclose={close_pct_diff:.3f}%")
    except Exception as e:
        warnings.append(f"  ⚠️ {name} ({symbol}): {e}")

# ========== 2. 商品驗證 ==========
print("\n" + "=" * 60)
print("2. 商品驗證")
print("=" * 60)

commodities = {
    "黃金": ("GC=F", 5204.20, 0.94),
    "白銀": ("SI=F", 90.00, 2.91),
    "原油WTI": ("CL=F", 65.75, 0.18),
    "布蘭特": ("BZ=F", 71.01, 0.34),
    "銅": ("HG=F", 6.05, 2.09),
    "天然氣": ("NG=F", 2.89, -0.96),
}

for name, (symbol, pdf_price, pdf_pct) in commodities.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            warnings.append(f"  ⚠️ {name} ({symbol}): 數據不足")
            continue
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff_pct = abs(yf_close - pdf_price) / pdf_price * 100 if pdf_price else 0
        pct_diff = abs(yf_pct - pdf_pct)
        
        status = "✅" if close_diff_pct < 1.0 and pct_diff < 0.5 else "❌"
        if status == "❌":
            errors.append(f"  {name}: PDF=${pdf_price} ({pdf_pct:+.2f}%) vs YF=${yf_close:.2f} ({yf_pct:+.2f}%)")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: PDF=${pdf_price} ({pdf_pct:+.2f}%) | YF=${yf_close:.2f} ({yf_pct:+.2f}%) | Date={date_str} | Δ={close_diff_pct:.3f}%")
    except Exception as e:
        warnings.append(f"  ⚠️ {name} ({symbol}): {e}")

# ========== 3. 外匯驗證 ==========
print("\n" + "=" * 60)
print("3. 外匯驗證")
print("=" * 60)

forex = {
    "美元指數": ("DX-Y.NYB", 97.5800, -0.31),
    "EUR/USD": ("EURUSD=X", 1.1822, 0.39),
    "USD/JPY": ("JPY=X", 155.9690, 0.06),
    "GBP/USD": ("GBPUSD=X", 1.3566, 0.51),
    "USD/CNY": ("CNY=X", 6.8687, -0.57),
    "USD/TWD": ("TWD=X", 31.2680, -0.35),
}

for name, (symbol, pdf_rate, pdf_pct) in forex.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            warnings.append(f"  ⚠️ {name} ({symbol}): 數據不足")
            continue
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff_pct = abs(yf_close - pdf_rate) / pdf_rate * 100 if pdf_rate else 0
        pct_diff = abs(yf_pct - pdf_pct)
        
        status = "✅" if close_diff_pct < 0.5 and pct_diff < 0.5 else "❌"
        if status == "❌":
            errors.append(f"  {name}: PDF={pdf_rate} ({pdf_pct:+.2f}%) vs YF={yf_close:.4f} ({yf_pct:+.2f}%)")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: PDF={pdf_rate} ({pdf_pct:+.2f}%) | YF={yf_close:.4f} ({yf_pct:+.2f}%) | Date={date_str} | Δ={close_diff_pct:.3f}%")
    except Exception as e:
        warnings.append(f"  ⚠️ {name} ({symbol}): {e}")

# ========== 4. 加密貨幣驗證 ==========
print("\n" + "=" * 60)
print("4. 加密貨幣驗證")
print("=" * 60)

crypto = {
    "Bitcoin": ("BTC-USD", 68465.83, 6.84),
    "Ethereum": ("ETH-USD", 2061.49, 11.25),
    "Solana": ("SOL-USD", 88.78, 12.33),
    "Cardano": ("ADA-USD", 0.30, 14.51),
    "XRP": ("XRP-USD", 1.44, 6.68),
    "BNB": ("BNB-USD", 630.15, 7.88),
    "Dogecoin": ("DOGE-USD", 0.10, 10.13),
}

for name, (symbol, pdf_price, pdf_pct) in crypto.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            warnings.append(f"  ⚠️ {name} ({symbol}): 數據不足")
            continue
        # 加密貨幣24/7，找最近的完整日
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff_pct = abs(yf_close - pdf_price) / pdf_price * 100 if pdf_price else 0
        pct_diff = abs(yf_pct - pdf_pct)
        
        # 加密貨幣波動大，容許稍大偏差
        status = "✅" if close_diff_pct < 2.0 and pct_diff < 2.0 else "❌"
        if status == "❌":
            errors.append(f"  {name}: PDF=${pdf_price} ({pdf_pct:+.2f}%) vs YF=${yf_close:.2f} ({yf_pct:+.2f}%)")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: PDF=${pdf_price} ({pdf_pct:+.2f}%) | YF=${yf_close:.2f} ({yf_pct:+.2f}%) | Date={date_str} | Δ={close_diff_pct:.3f}%")
    except Exception as e:
        warnings.append(f"  ⚠️ {name} ({symbol}): {e}")

# ========== 5. 熱門股票驗證 ==========
print("\n" + "=" * 60)
print("5. 熱門股票驗證（抽樣關鍵標的）")
print("=" * 60)

hot_stocks = {
    # 美股
    "AXON": ("AXON", 520.18, 17.55),
    "COIN": ("COIN", 183.94, 13.52),
    "TRI": ("TRI", 99.38, 10.31),
    "NFLX": ("NFLX", 82.70, 5.97),
    "ALB": ("ALB", 195.87, 4.84),
    "GDDY": ("GDDY", 79.12, -14.28),
    "FSLR": ("FSLR", 210.12, -13.61),
    "MELI": ("MELI", 1767.71, -8.05),
    # 港股
    "HSBC": ("0005.HK", 142.70, 5.47),
    "Tingyi": ("0322.HK", 13.53, 3.76),
    "Anta": ("2020.HK", 86.65, 2.48),
    # 台股
    "台化": ("1326.TW", 49.20, 9.94),
    "南電": ("8046.TW", 553.00, 9.94),
    "台塑": ("1301.TW", 53.40, 9.88),
    "華城": ("1519.TW", 1050.00, 9.83),
    "台玻": ("1802.TW", 61.30, 7.92),
    "正新": ("2105.TW", 30.45, -1.14),
}

for name, (symbol, pdf_close, pdf_pct) in hot_stocks.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            warnings.append(f"  ⚠️ {name} ({symbol}): 數據不足")
            continue
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff_pct = abs(yf_close - pdf_close) / pdf_close * 100 if pdf_close else 0
        pct_diff = abs(yf_pct - pdf_pct)
        
        status = "✅" if close_diff_pct < 1.0 and pct_diff < 0.5 else "❌"
        if status == "❌":
            errors.append(f"  {name} ({symbol}): PDF={pdf_close} ({pdf_pct:+.2f}%) vs YF={yf_close:.2f} ({yf_pct:+.2f}%)")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: PDF={pdf_close} ({pdf_pct:+.2f}%) | YF={yf_close:.2f} ({yf_pct:+.2f}%) | Date={date_str} | Δ={close_diff_pct:.3f}%")
    except Exception as e:
        warnings.append(f"  ⚠️ {name} ({symbol}): {e}")

# ========== 總結 ==========
print("\n" + "=" * 60)
print("驗證總結")
print("=" * 60)

if errors:
    print(f"\n❌ 發現 {len(errors)} 個數據偏差：")
    for e in errors:
        print(e)
else:
    print("\n✅ 所有數據點驗證通過，無偏差")

if warnings:
    print(f"\n⚠️ {len(warnings)} 個警告：")
    for w in warnings:
        print(w)
