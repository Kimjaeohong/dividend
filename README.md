# dividend-data

dividend.hongspot.com 배당 허브의 데이터 저장소.
GitHub Actions가 매일 07:10 KST에 yfinance로 미국 배당 데이터를 갱신합니다.

## 구조
- `scripts/fetch_dividends.py` — 미국 배당 배치 (유니버스는 파일 상단 UNIVERSE에서 편집)
- `data/us_dividends.json` — 자동 생성 (미국 캘린더·월배당 ETF 페이지가 읽음)
- `data/kr_quarterly.json` — 수동 관리 (국내 분기배당주 페이지가 읽음)
- `.github/workflows/update-dividends.yml` — 일일 스케줄

## 최초 설정
1. GitHub에 public 저장소 `dividend-data` 생성 후 이 폴더 전체 push
2. Actions 탭 → "Update US dividend data" → Run workflow (수동 1회 실행해 JSON 생성)
3. 블로그 페이지 3개의 DATA_URL에서 `YOUR_GITHUB_ID`를 본인 아이디로 교체

## 데이터 URL (jsDelivr CDN)
https://cdn.jsdelivr.net/gh/YOUR_GITHUB_ID/dividend-data@main/data/us_dividends.json

jsDelivr는 최대 12시간 캐시하므로 갱신 직후 반영이 늦으면 정상입니다.
즉시 확인은 raw URL: https://raw.githubusercontent.com/YOUR_GITHUB_ID/dividend-data/main/data/us_dividends.json
