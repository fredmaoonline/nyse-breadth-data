#!/usr/bin/env python3
"""
NYSE 市场广度数据采集器 — GitHub Actions 桥接
=============================================
在 GitHub Actions (US IP) 上运行，通过 yfinance 拉取:
  - ^NYA.A: NYSE 上涨家数
  - ^NYA.D: NYSE 下跌家数

输出: nyse_breadth.json (含40个交易日历史 + 麦克莱伦摆动值)
触发: 每个美股交易日 16:30 ET (GitHub Actions schedule)
"""

import json, os, sys
from datetime import datetime, timedelta

DATA_FILE = "nyse_breadth.json"

def fetch_breadth():
    """用 yfinance 拉取 NYSE 涨跌家数"""
    import yfinance as yf
    
    # 拉取最近60天数据 (足够计算 39日 EMA)
    advancing = yf.download('^NYA.A', period='3mo', interval='1d', progress=False)
    declining = yf.download('^NYA.D', period='3mo', interval='1d', progress=False)
    
    if advancing.empty or declining.empty:
        print("❌ yfinance 返回空数据")
        return None
    
    # 对齐日期
    adv_close = advancing['Close'].rename('advancing')
    dec_close = declining['Close'].rename('declining')
    merged = adv_close.to_frame().join(dec_close.to_frame(), how='inner').dropna()
    
    if len(merged) < 20:
        print(f"❌ 数据不足: {len(merged)} 天 (需要≥20天)")
        return None
    
    # 计算净上涨家数
    merged['net_advances'] = merged['advancing'] - merged['declining']
    
    # 计算麦克莱伦摆动值: 19日EMA - 39日EMA
    ema19 = merged['net_advances'].ewm(span=19, adjust=False).mean()
    ema39 = merged['net_advances'].ewm(span=39, adjust=False).mean()
    merged['mcclellan'] = ema19 - ema39
    
    # 序列化为 JSON
    records = []
    for idx, row in merged.iterrows():
        records.append({
            'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10],
            'advancing': round(float(row['advancing']), 0),
            'declining': round(float(row['declining']), 0),
            'net_advances': round(float(row['net_advances']), 0),
            'mcclellan': round(float(row['mcclellan']), 2) if not (pd.isna(row['mcclellan']) if 'pd' in dir() else False) else None
        })
    
    # 过滤掉 mcclellan 为 NaN 的早期记录
    import pandas as pd
    records = [r for r in records if r['mcclellan'] is not None]
    
    latest = records[-1]
    print(f"✅ {len(records)} 条记录")
    print(f"   最新: {latest['date']} 涨{latest['advancing']:.0f} 跌{latest['declining']:.0f}")
    print(f"   净上涨: {latest['net_advances']:.0f}")
    print(f"   麦克莱伦: {latest['mcclellan']:.2f}")
    
    return {
        'last_update': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'records': records,
        'latest': latest,
        'source': 'yfinance (^NYA.A / ^NYA.D) via GitHub Actions'
    }

# ── 主逻辑 ──
if __name__ == '__main__':
    import pandas as pd  # yfinance 依赖
    
    print(f"📡 NYSE 广度数据采集 — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    
    data = fetch_breadth()
    if data:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 已写入 {DATA_FILE} ({len(data['records'])} 条)")
        
        # 输出状态码给 GitHub Actions
        mcclellan = data['latest']['mcclellan']
        net = data['latest']['net_advances']
        print(f"📊 麦克莱伦={mcclellan:.0f} | 净上涨={net:.0f}")
        
        # 写 status badge 信息
        with open('STATUS.md', 'w') as f:
            icon = '🔴' if mcclellan < -200 else '🟡' if mcclellan < 0 else '🟢'
            f.write(f"# NYSE Breadth Status\n\n{icon} **McClellan: {mcclellan:.0f}** | Net Advances: {net:.0f}\n")
            f.write(f"\nLast update: {data['last_update']}\n")
    else:
        print("❌ 数据采集失败")
        sys.exit(1)
