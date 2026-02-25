#!/usr/bin/env python3
"""
熱門股票偵測模組
結合新聞提及頻率 + 成交量異常 + 漲跌幅異常來偵測市場熱點股票

篩選邏輯：
  1. 資金追捧（買入放量）：量比 ≥ 1.5x + 上漲 → 市場正在搶進的標的
  2. 資金出清（賣出放量）：量比 ≥ 2.5x + 下跌 → 市場正在拋售的標的
  3. 熱度分數權重：成交量異常（最高）> 漲跌幅 > 新聞提及（最低）
"""
import sys
sys.path.append('/opt/.manus/.sandbox-runtime')

import json
from data_api import ApiClient
from datetime import datetime

client = ApiClient()

# ==================== 量比門檻設定 ====================
# 買入放量門檻（資金追捧）：輕度放量即可關注
MIN_VOLUME_RATIO_BUY = 1.5   # 量比 ≥ 1.5x + 上漲
# 賣出放量門檻（資金出清）：需顯著放量才算恐慌性拋售
MIN_VOLUME_RATIO_SELL = 2.5   # 量比 ≥ 2.5x + 下跌

# ==================== 熱度分數權重 ====================
# 權重排序：成交量異常（最高）> 漲跌幅 > 新聞提及（最低）
WEIGHT_VOLUME = 0.50    # 成交量異常權重（最高優先）
WEIGHT_PRICE = 0.35     # 漲跌幅權重
WEIGHT_NEWS = 0.15      # 新聞提及權重（最低優先）

# ==================== 資金流向分類 ====================
FLOW_BUY = 'inflow'     # 資金追捧（買入放量上漲）
FLOW_SELL = 'outflow'   # 資金出清（賣出放量下跌）


# 各市場的主要股票池（用於成交量異常偵測）
US_STOCK_POOL = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'AMD',
    'NFLX', 'CRM', 'ADBE', 'INTC', 'QCOM', 'MU', 'MRVL', 'AMAT', 'LRCX', 'KLAC',
    'JPM', 'V', 'MA', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'SCHW',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'BMY', 'AMGN',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG',
    'KO', 'PEP', 'PG', 'WMT', 'COST', 'HD', 'MCD', 'DIS', 'NKE',
    'BA', 'CAT', 'GE', 'HON', 'UPS', 'RTX', 'LMT',
    'F', 'GM', 'RIVN', 'LCID',
    'COIN', 'MSTR', 'RIOT', 'MARA',
    'CLF', 'KR', 'MNDY',
]

JP_STOCK_POOL = [
    '9984.T',   # SoftBank
    '6758.T',   # Sony
    '7203.T',   # Toyota
    '8306.T',   # Mitsubishi UFJ
    '6861.T',   # Keyence
    '9432.T',   # NTT
    '6501.T',   # Hitachi
    '8035.T',   # Tokyo Electron
    '6902.T',   # Denso
    '7741.T',   # HOYA
]

TW_STOCK_POOL = [
    '2330.TW',  # TSMC
    '2454.TW',  # MediaTek
    '2317.TW',  # Hon Hai
    '3034.TW',  # Novatek
    '2308.TW',  # Delta
    '2382.TW',  # Quanta
    '2303.TW',  # UMC
    '3711.TW',  # ASE
    '2881.TW',  # Fubon FHC
    '2891.TW',  # CTBC FHC
]

HK_STOCK_POOL = [
    '0700.HK',  # Tencent
    '9988.HK',  # Alibaba
    '9618.HK',  # JD.com
    '3690.HK',  # Meituan
    '1810.HK',  # Xiaomi
    '0941.HK',  # China Mobile
    '1398.HK',  # ICBC
    '2318.HK',  # Ping An
]


def calculate_heat_score(volume_ratio, abs_change_pct, news_mentions=0):
    """
    計算綜合熱度分數

    權重：成交量異常（50%）> 漲跌幅（35%）> 新聞提及（15%）
    """
    vol_score = max(0, volume_ratio - 1.0)
    price_score = abs_change_pct
    news_score = min(news_mentions, 10)

    heat = (WEIGHT_VOLUME * vol_score * 10 +
            WEIGHT_PRICE * price_score +
            WEIGHT_NEWS * news_score)

    return round(heat, 2)


def classify_flow(change_pct, volume_ratio):
    """
    根據漲跌幅方向和量比大小，判斷資金流向分類

    Returns:
        'inflow'  - 資金追捧（量比 ≥ 1.5x + 上漲）
        'outflow' - 資金出清（量比 ≥ 2.5x + 下跌）
        None      - 不符合任何分類（被過濾掉）
    """
    if change_pct > 0 and volume_ratio >= MIN_VOLUME_RATIO_BUY:
        return FLOW_BUY
    elif change_pct < 0 and volume_ratio >= MIN_VOLUME_RATIO_SELL:
        return FLOW_SELL
    else:
        return None


def detect_hot_stocks(stock_pool, market_name, top_n=5):
    """
    偵測熱門股票：區分買入放量與賣出放量

    篩選條件：
    - 買入放量：量比 ≥ 1.5x + 上漲
    - 賣出放量：量比 ≥ 2.5x + 下跌
    - 其餘不列入（正常交易量 or 縮量下跌等）
    """
    results = []
    skipped_count = 0

    for symbol in stock_pool:
        try:
            response = client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': symbol,
                'region': 'US',
                'interval': '1d',
                'range': '1mo'
            })

            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                meta = result['meta']
                quotes = result['indicators']['quote'][0]
                timestamps = result.get('timestamp', [])

                if len(timestamps) < 5:
                    continue

                curr_close = quotes['close'][-1]
                prev_close = quotes['close'][-2]
                curr_volume = quotes['volume'][-1]

                if curr_close is None or prev_close is None or curr_volume is None:
                    continue

                change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close else 0

                # 計算過去20天的平均成交量（排除最近一天）
                valid_volumes = [v for v in quotes['volume'][:-1] if v is not None and v > 0]
                avg_volume = sum(valid_volumes) / len(valid_volumes) if valid_volumes else curr_volume
                volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1

                # ★ 資金流向分類
                flow = classify_flow(change_pct, volume_ratio)
                if flow is None:
                    skipped_count += 1
                    continue

                heat_score = calculate_heat_score(volume_ratio, abs(change_pct), 0)

                results.append({
                    'symbol': symbol,
                    'name': meta.get('longName', symbol),
                    'current': round(curr_close, 2),
                    'previous': round(prev_close, 2),
                    'change': round(curr_close - prev_close, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': curr_volume,
                    'avg_volume': round(avg_volume),
                    'volume_ratio': round(volume_ratio, 2),
                    'heat_score': heat_score,
                    'market': market_name,
                    'flow': flow,  # 'inflow' or 'outflow'
                })

        except Exception as e:
            continue

    if skipped_count > 0:
        print(f"  [{market_name}] 跳過 {skipped_count} 支未達放量門檻的股票")

    # 按熱度分數排序
    results.sort(key=lambda x: x['heat_score'], reverse=True)
    return results[:top_n]


def merge_with_news_tickers(hot_stocks, news_trending_tickers):
    """
    將新聞熱門 tickers 與成交量/漲跌幅熱門股票合併
    合併後重新計算含新聞權重的熱度分數
    """
    news_tickers = {t['ticker']: t for t in news_trending_tickers}

    for stock in hot_stocks:
        symbol_base = stock['symbol'].split('.')[0]
        if symbol_base in news_tickers:
            stock['news_mentions'] = news_tickers[symbol_base]['mention_count']
            stock['news_sentiment'] = news_tickers[symbol_base].get('sentiment', {})
        else:
            stock['news_mentions'] = 0
            stock['news_sentiment'] = {}

        stock['heat_score'] = calculate_heat_score(
            stock['volume_ratio'],
            abs(stock['change_pct']),
            stock['news_mentions']
        )

    hot_stocks.sort(key=lambda x: x['heat_score'], reverse=True)
    return hot_stocks


def split_by_flow(stocks):
    """
    將股票列表按資金流向分成兩組

    Returns:
        (inflow_list, outflow_list)
    """
    inflow = [s for s in stocks if s.get('flow') == FLOW_BUY]
    outflow = [s for s in stocks if s.get('flow') == FLOW_SELL]
    return inflow, outflow


def get_all_hot_stocks(news_trending_tickers=None):
    """獲取所有市場的熱門股票"""
    results = {
        '美股': detect_hot_stocks(US_STOCK_POOL, '美股', top_n=8),
        '日股': detect_hot_stocks(JP_STOCK_POOL, '日股', top_n=5),
        '台股': detect_hot_stocks(TW_STOCK_POOL, '台股', top_n=5),
        '港股': detect_hot_stocks(HK_STOCK_POOL, '港股', top_n=5),
    }

    if news_trending_tickers:
        for market, stocks in results.items():
            results[market] = merge_with_news_tickers(stocks, news_trending_tickers)

    return results


if __name__ == '__main__':
    print(f"買入放量門檻：{MIN_VOLUME_RATIO_BUY}x（量比 + 上漲）")
    print(f"賣出放量門檻：{MIN_VOLUME_RATIO_SELL}x（量比 + 下跌）")
    print(f"熱度權重：成交量 {WEIGHT_VOLUME*100:.0f}% > 漲跌幅 {WEIGHT_PRICE*100:.0f}% > 新聞 {WEIGHT_NEWS*100:.0f}%")
    print()
    print("偵測美股熱門股票...")
    us_hot = detect_hot_stocks(US_STOCK_POOL[:15], '美股', top_n=10)
    inflow, outflow = split_by_flow(us_hot)
    print(f"\n🔥 資金追捧（買入放量 ≥ {MIN_VOLUME_RATIO_BUY}x + 上漲）：")
    for s in inflow:
        print(f"  {s['symbol']:6s} {s['change_pct']:+6.2f}% | Vol {s['volume_ratio']:.1f}x | Heat {s['heat_score']:.1f}")
    if not inflow:
        print("  （無）")
    print(f"\n⚠️ 資金出清（賣出放量 ≥ {MIN_VOLUME_RATIO_SELL}x + 下跌）：")
    for s in outflow:
        print(f"  {s['symbol']:6s} {s['change_pct']:+6.2f}% | Vol {s['volume_ratio']:.1f}x | Heat {s['heat_score']:.1f}")
    if not outflow:
        print("  （無）")
