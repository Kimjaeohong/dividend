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
ARISTOCRATS_PATH = Path(__file__).resolve().parent.parent / "data" / "dividend_aristocrats_2026.json"

# 유니버스 베이스: 서학개미 관심 배당 종목/ETF. (영문명, 한글명) — 자유롭게 추가/삭제.
# 배당킹/배당귀족(S&P 500 Dividend Aristocrats) 69종목은 data/dividend_aristocrats_2026.json에서
# 자동 병합됨 — 그 목록 갱신은 연 1회 해당 JSON 파일만 고치면 됨.
BASE_UNIVERSE = {
    # 월배당 / 커버드콜 ETF
    "JEPI": {"name": "JPMorgan Equity Premium Income", "name_kr": "JP모건 에쿼티 프리미엄 인컴"},
    "JEPQ": {"name": "JPMorgan Nasdaq Equity Premium", "name_kr": "JP모건 나스닥 프리미엄 인컴"},
    "QYLD": {"name": "Global X Nasdaq 100 Covered Call", "name_kr": "글로벌X 나스닥100 커버드콜"},
    "XYLD": {"name": "Global X S&P 500 Covered Call", "name_kr": "글로벌X S&P500 커버드콜"},
    "RYLD": {"name": "Global X Russell 2000 Covered Call", "name_kr": "글로벌X 러셀2000 커버드콜"},
    "TLTW": {"name": "iShares 20+ Treasury BuyWrite", "name_kr": "아이셰어즈 미국채 20년+ 커버드콜"},
    "SPHD": {"name": "Invesco S&P 500 High Div Low Vol", "name_kr": "인베스코 고배당 저변동성"},
    "PFF":  {"name": "iShares Preferred & Income", "name_kr": "아이셰어즈 우선주"},
    "SDIV": {"name": "Global X SuperDividend", "name_kr": "글로벌X 슈퍼디비던드"},
    "DIVO": {"name": "Amplify CWP Enhanced Dividend", "name_kr": "앰플리파이 배당성장 커버드콜"},
    "DIA":  {"name": "SPDR Dow Jones Industrial Average", "name_kr": "SPDR 다우존스"},
    # 월배당 개별주 (리츠/BDC)
    "O":    {"name": "Realty Income", "name_kr": "리얼티인컴"},
    "MAIN": {"name": "Main Street Capital", "name_kr": "메인스트리트 캐피털"},
    "AGNC": {"name": "AGNC Investment", "name_kr": "AGNC 인베스트먼트"},
    "STAG": {"name": "STAG Industrial", "name_kr": "스태그 인더스트리얼"},
    "EPR":  {"name": "EPR Properties", "name_kr": "EPR 프로퍼티스"},
    # 분기배당 ETF
    "SCHD": {"name": "Schwab US Dividend Equity", "name_kr": "슈왑 미국 배당주"},
    "VYM":  {"name": "Vanguard High Dividend Yield", "name_kr": "뱅가드 고배당"},
    "VIG":  {"name": "Vanguard Dividend Appreciation", "name_kr": "뱅가드 배당성장"},
    "DGRO": {"name": "iShares Core Dividend Growth", "name_kr": "아이셰어즈 배당성장"},
    "HDV":  {"name": "iShares Core High Dividend", "name_kr": "아이셰어즈 고배당"},
    "SPYD": {"name": "SPDR S&P 500 High Dividend", "name_kr": "SPDR 고배당"},
    "DVY":  {"name": "iShares Select Dividend", "name_kr": "아이셰어즈 셀렉트 디비던드"},
    "NOBL": {"name": "ProShares S&P 500 Dividend Aristocrats", "name_kr": "프로셰어즈 배당귀족"},
    # 분기배당 개별주
    "KO":   {"name": "Coca-Cola", "name_kr": "코카콜라"},
    "PEP":  {"name": "PepsiCo", "name_kr": "펩시코"},
    "JNJ":  {"name": "Johnson & Johnson", "name_kr": "존슨앤드존슨"},
    "PG":   {"name": "Procter & Gamble", "name_kr": "프록터앤드갬블"},
    "MO":   {"name": "Altria", "name_kr": "알트리아"},
    "T":    {"name": "AT&T", "name_kr": "AT&T"},
    "VZ":   {"name": "Verizon", "name_kr": "버라이즌"},
    "ABBV": {"name": "AbbVie", "name_kr": "애브비"},
    "XOM":  {"name": "Exxon Mobil", "name_kr": "엑슨모빌"},
    "CVX":  {"name": "Chevron", "name_kr": "셰브론"},
    "MCD":  {"name": "McDonald's", "name_kr": "맥도날드"},
    "IBM":  {"name": "IBM", "name_kr": "IBM"},
    "MMM":  {"name": "3M", "name_kr": "쓰리엠"},
    "TGT":  {"name": "Target", "name_kr": "타깃"},
    "SBUX": {"name": "Starbucks", "name_kr": "스타벅스"},
    "HD":   {"name": "Home Depot", "name_kr": "홈디포"},
    "LMT":  {"name": "Lockheed Martin", "name_kr": "록히드마틴"},
    "AVGO": {"name": "Broadcom", "name_kr": "브로드컴"},
    "MSFT": {"name": "Microsoft", "name_kr": "마이크로소프트"},
    "AAPL": {"name": "Apple", "name_kr": "애플"},
}

FREQ_LABEL = {"monthly": "월배당", "quarterly": "분기배당",
              "semiannual": "반기배당", "annual": "연배당", "irregular": "비정기"}


def load_aristocrats() -> dict:
    data = json.loads(ARISTOCRATS_PATH.read_text(encoding="utf-8"))
    return {
        row["ticker"]: {"name": row["name_en"], "name_kr": row["name_ko"], "tier": row["tier"]}
        for row in data["tickers"]
    }


def build_universe() -> dict:
    universe = {sym: dict(info) for sym, info in BASE_UNIVERSE.items()}
    for sym, info in load_aristocrats().items():
        if sym in universe:
            universe[sym]["tier"] = info["tier"]  # 기존 종목: 한글명·설정 유지, tier만 추가
        else:
            universe[sym] = info  # 신규 배당킹/배당귀족 종목
    return universe


UNIVERSE = build_universe()


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


def fetch_one(symbol: str, name: str, name_kr: str, tier: str | None) -> dict | None:
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
        "tier": tier,
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
    for i, (sym, info) in enumerate(UNIVERSE.items()):
        for attempt in range(2):
            try:
                row = fetch_one(sym, info["name"], info["name_kr"], info.get("tier"))
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
