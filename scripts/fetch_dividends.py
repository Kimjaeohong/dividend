#!/usr/bin/env python3
"""
미국 배당 데이터 일일 배치
- yfinance로 유니버스 순회 → data/us_dividends.json 생성
- 배당 주기는 최근 365일 지급 횟수로 추론 (하드코딩 없음)
- 실패 종목은 건너뛰고, 전체 실패 시 기존 JSON 유지 (사이트 안 깨짐)
"""
import json
import time
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

OUT = Path(__file__).resolve().parent.parent / "data" / "us_dividends.json"

# 유니버스: 서학개미 관심 배당 종목/ETF. (영문명, 한글명) — 자유롭게 추가/삭제.
UNIVERSE = {
    # 월배당 / 커버드콜 ETF
    "JEPI": ("JPMorgan Equity Premium Income", "JP모건 에쿼티 프리미엄 인컴"),
    "JEPQ": ("JPMorgan Nasdaq Equity Premium", "JP모건 나스닥 프리미엄 인컴"),
    "QYLD": ("Global X Nasdaq 100 Covered Call", "글로벌X 나스닥100 커버드콜"),
    "XYLD": ("Global X S&P 500 Covered Call", "글로벌X S&P500 커버드콜"),
    "RYLD": ("Global X Russell 2000 Covered Call", "글로벌X 러셀2000 커버드콜"),
    "TLTW": ("iShares 20+ Treasury BuyWrite", "아이셰어즈 미국채 20년+ 커버드콜"),
    "SPHD": ("Invesco S&P 500 High Div Low Vol", "인베스코 고배당 저변동성"),
    "PFF":  ("iShares Preferred & Income", "아이셰어즈 우선주"),
    "SDIV": ("Global X SuperDividend", "글로벌X 슈퍼디비던드"),
    "DIVO": ("Amplify CWP Enhanced Dividend", "앰플리파이 배당성장 커버드콜"),
    "DIA":  ("SPDR Dow Jones Industrial Average", "SPDR 다우존스"),
    # 월배당 개별주 (리츠/BDC)
    "O":    ("Realty Income", "리얼티인컴"),
    "MAIN": ("Main Street Capital", "메인스트리트 캐피털"),
    "AGNC": ("AGNC Investment", "AGNC 인베스트먼트"),
    "STAG": ("STAG Industrial", "스태그 인더스트리얼"),
    "EPR":  ("EPR Properties", "EPR 프로퍼티스"),
    # 분기배당 ETF
    "SCHD": ("Schwab US Dividend Equity", "슈왑 미국 배당주"),
    "VYM":  ("Vanguard High Dividend Yield", "뱅가드 고배당"),
    "VIG":  ("Vanguard Dividend Appreciation", "뱅가드 배당성장"),
    "DGRO": ("iShares Core Dividend Growth", "아이셰어즈 배당성장"),
    "HDV":  ("iShares Core High Dividend", "아이셰어즈 고배당"),
    "SPYD": ("SPDR S&P 500 High Dividend", "SPDR 고배당"),
    "DVY":  ("iShares Select Dividend", "아이셰어즈 셀렉트 디비던드"),
    "NOBL": ("ProShares S&P 500 Dividend Aristocrats", "프로셰어즈 배당귀족"),
    # 분기배당 개별주
    "KO":   ("Coca-Cola", "코카콜라"),
    "PEP":  ("PepsiCo", "펩시코"),
    "JNJ":  ("Johnson & Johnson", "존슨앤드존슨"),
    "PG":   ("Procter & Gamble", "프록터앤드갬블"),
    "MO":   ("Altria", "알트리아"),
    "T":    ("AT&T", "AT&T"),
    "VZ":   ("Verizon", "버라이즌"),
    "ABBV": ("AbbVie", "애브비"),
    "XOM":  ("Exxon Mobil", "엑슨모빌"),
    "CVX":  ("Chevron", "셰브론"),
    "MCD":  ("McDonald's", "맥도날드"),
    "IBM":  ("IBM", "IBM"),
    "MMM":  ("3M", "쓰리엠"),
    "TGT":  ("Target", "타깃"),
    "SBUX": ("Starbucks", "스타벅스"),
    "HD":   ("Home Depot", "홈디포"),
    "LMT":  ("Lockheed Martin", "록히드마틴"),
    "AVGO": ("Broadcom", "브로드컴"),
    "MSFT": ("Microsoft", "마이크로소프트"),
    "AAPL": ("Apple", "애플"),
}

FREQ_LABEL = {"monthly": "월배당", "quarterly": "분기배당",
              "semiannual": "반기배당", "annual": "연배당", "irregular": "비정기"}


def infer_frequency(n_last_365d: int) -> str:
    if n_last_365d >= 10:
        return "monthly"
    if n_last_365d >= 3:
        return "quarterly"
    if n_last_365d == 2:
        return "semiannual"
    if n_last_365d == 1:
        return "annual"
    return "irregular"


def fetch_one(symbol: str, name: str, name_kr: str) -> dict | None:
    t = yf.Ticker(symbol)
    now = datetime.now(timezone.utc)

    divs = t.dividends  # tz-aware DatetimeIndex → amount
    if divs is None or len(divs) == 0:
        return None

    cutoff = now - timedelta(days=365)
    recent = divs[divs.index >= cutoff]
    freq = infer_frequency(len(recent))

    # 최근 12개월 지급 이력 (배당락일 기준)
    history = [
        {"ex_date": d.strftime("%Y-%m-%d"), "amount": round(float(a), 4)}
        for d, a in recent.items()
    ]

    # 다음 배당락일 (선언된 경우만 존재)
    next_ex = None
    try:
        cal = t.calendar
        if isinstance(cal, dict):
            ex = cal.get("Ex-Dividend Date")
            if ex:
                next_ex = ex.strftime("%Y-%m-%d") if hasattr(ex, "strftime") else str(ex)
    except Exception:
        pass

    # 가격 → TTM 배당수익률
    price = None
    try:
        price = float(t.fast_info["lastPrice"])
    except Exception:
        try:
            h = t.history(period="5d")
            if len(h):
                price = float(h["Close"].iloc[-1])
        except Exception:
            pass

    ttm = float(recent.sum())
    ttm_yield = round(ttm / price * 100, 2) if price and ttm > 0 else None

    last = history[-1] if history else None

    return {
        "symbol": symbol,
        "name": name,
        "name_kr": name_kr,
        "frequency": freq,
        "frequency_kr": FREQ_LABEL[freq],
        "price": round(price, 2) if price else None,
        "ttm_dividend": round(ttm, 4),
        "ttm_yield": ttm_yield,
        "last_ex_date": last["ex_date"] if last else None,
        "last_amount": last["amount"] if last else None,
        "next_ex_date": next_ex,
        "history": history,
    }


def main() -> int:
    results, failed = [], []
    for i, (sym, names) in enumerate(UNIVERSE.items()):
        name, name_kr = names
        for attempt in range(2):
            try:
                row = fetch_one(sym, name, name_kr)
                if row:
                    results.append(row)
                break
            except Exception as e:
                if attempt == 1:
                    failed.append(sym)
                    print(f"[skip] {sym}: {e}", file=sys.stderr)
                else:
                    time.sleep(3)
        time.sleep(0.6)  # 레이트리밋 예방

    # 전멸 시 기존 파일 보존 → 사이트는 이전 데이터로 계속 동작
    if len(results) < max(5, len(UNIVERSE) // 4):
        print(f"[abort] too few results ({len(results)}), keeping previous JSON",
              file=sys.stderr)
        return 1

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(results),
        "failed": failed,
        "tickers": sorted(results, key=lambda r: (r["ttm_yield"] or 0), reverse=True),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] {len(results)} tickers → {OUT} (failed: {failed or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
