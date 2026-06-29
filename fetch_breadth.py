#!/usr/bin/env python3
"""
NYSE 市场广度数据采集器 — GitHub Actions 桥接 v2
=============================================
修复: ^NYA.A/^NYA.D 符号格式问题，增加多重回退策略
"""

import json, sys
from datetime import datetime, timedelta

DATA_FILE = "nyse_breadth.json"

def fetch_breadth():
    """用 yfinance 拉取 NYSE 涨跌家数 — 多策略回退"""
    import yfinance as yf
    import pandas as pd
    
    # 策略: 先试标准 ticker，再试替代格式
    symbols_to_try = [
        ('^NYA.A', '^NYA.D'),
        ('NYA.A', 'NYA.D'),
        ('^ADV.N', '^DEC.N'),
    ]
    
    for adv_sym, dec_sym in symbols_to_try:
        print(f"  尝试: {adv_sym} / {dec_sym}")
        try:
            adv = yf.download(adv_sym, period='3mo', interval='1d', progress=False)
            dec = yf.download(dec_sym, period='3mo', interval='1d', progress=False)
            
            if adv.empty or dec.empty:
                print(f"    → 空数据，换下一个")
                continue
            
            adv_close = adv['Close'].rename('advancing')
            dec_close = dec['Close'].rename('declining')
            merged = adv_close.to_frame().join(dec_close.to_frame(), how='inner').dropna()
            
            if len(merged) < 20:
                print(f"    → 数据不足 ({len(merged)}天)")
                continue
            
            merged['net_advances'] = merged['advancing'] - merged['declining']
            ema19 = merged['net_advances'].ewm(span=19, adjust=False).mean()
            ema39 = merged['net_advances'].ewm(span=39, adjust=False).mean()
            merged['mcclellan'] = ema19 - ema39
            
            records = []
            for idx, row in merged.iterrows():
                date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
                m = row['mcclellan']
                records.append({
                    'date': date_str,
                    'advancing': round(float(row['advancing']), 0),
                    'declining': round(float(row['declining']), 0),
                    'net_advances': round(float(row['net_advances']), 0),
                    'mcclellan': round(float(m), 2) if not pd.isna(m) else None
                })
            
            records = [r for r in records if r['mcclellan'] is not None]
            latest = records[-1]
            
            print(f"✅ 成功! {len(records)}条记录, 麦克莱伦={latest['mcclellan']:.1f}")
            
            return {
                'last_update': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'records': records[-40:],
                'latest': latest,
                'source': f'yfinance ({adv_sym}/{dec_sym}) via GitHub Actions'
            }
            
        except Exception as e:
            print(f"    → 异常: {e}")
            continue
    
    # 全部策略失败 — 尝试直接从 Yahoo 网页抓取
    print("  尝试直接网页抓取...")
    try:
        html = pd.read_html('https://finance.yahoo.com/markets/stocks/most-active/')
        print(f"   网页抓取结果: {len(html)} tables")
    except Exception as e:
        print(f"   网页抓取失败: {e}")
    
    return None


if __name__ == '__main__':
    print(f"📡 NYSE 广度数据采集 v2 — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    
    data = fetch_breadth()
    if data:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 已写入 {DATA_FILE}")
        m = data['latest']['mcclellan']
        print(f"📊 麦克莱伦={m:.0f} | 净上涨={data['latest']['net_advances']:.0f}")
        
        icon = '🔴' if m < -200 else '🟡' if m < 0 else '🟢'
        with open('STATUS.md', 'w') as f:
            f.write(f"# NYSE Breadth Status\n\n{icon} **McClellan: {m:.0f}** | Net Advances: {data['latest']['net_advances']:.0f}\n")
            f.write(f"\nLast update: {data['last_update']}\n")
    else:
        print("❌ 所有策略均失败")
        sys.exit(1)
