# dividend

dividend.hongspot.com 배당 허브의 데이터 저장소.
GitHub Actions가 매일 아침 07:10(한국 시간)쯤 yfinance로 미국 배당 데이터를 갱신합니다.

## 구조
- `scripts/fetch_dividends.py` — 미국 배당 배치 (종목 목록은 파일 상단 `BASE_UNIVERSE`에서 편집)
- `data/dividend_aristocrats_2026.json` — 배당킹·배당귀족 목록 (연 1회 수동 갱신, 배치에 자동 병합)
- `data/us_dividends.json` — 자동 생성 (미국 배당 캘린더·월배당 ETF 페이지가 읽음)
- `data/kr_quarterly.json` — 수동 관리 (국내 분기배당주 페이지가 읽음)
- `.github/workflows/update-dividends.yml` — 일일 스케줄 + CDN 캐시 비우기

## 데이터 주소
블로그 페이지는 jsDelivr CDN 주소를 먼저 읽고, 막히면 GitHub 원본 주소로 다시 시도합니다.

- https://cdn.jsdelivr.net/gh/Kimjaeohong/dividend@main/data/us_dividends.json
- https://cdn.jsdelivr.net/gh/Kimjaeohong/dividend@main/data/kr_quarterly.json
- (원본) https://raw.githubusercontent.com/Kimjaeohong/dividend/main/data/us_dividends.json

jsDelivr는 원래 최대 12시간 캐시하지만, 워크플로가 갱신 직후 캐시를 비우므로 보통 바로 반영됩니다.
`kr_quarterly.json`을 GitHub에서 직접 고쳐 저장해도 캐시 비우기가 자동으로 실행됩니다.

## 수동 갱신
Actions 탭 → "Update US dividend data" → Run workflow
