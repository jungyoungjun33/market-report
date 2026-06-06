# 📊 Market Report 자동화 시스템

매일 오전 5시(KST) 한국 시장 주요 지표를 자동 수집해 대시보드 업데이트, Notion 기록, 텔레그램 알림을 전송하는 시스템.

---

## 🔄 시스템 동작 흐름

```
GitHub Actions (매일 UTC 20:00 = KST 05:00)
    ↓
scripts/market_report.py
    ├── yfinance + Naver API → 시장 데이터 수집
    ├── index.html 업데이트 (비교표 + 차트)
    ├── Notion DB에 오늘 기록 추가
    └── 텔레그램 알림 전송 (대시보드 링크 + Notion 링크)
    ↓
git push → Netlify 자동 배포
```

---

## 🔗 연결된 서비스

| 서비스 | URL / 정보 |
|--------|-----------|
| **대시보드** | https://splendorous-empanada-694d4e.netlify.app/ |
| **Notion DB** | 시장 주요 지표 일지 (비밀 워크스페이스) |
| **텔레그램 봇** | @daily0600bot |
| **GitHub 레포** | https://github.com/jungyoungjun33/market-report |

---

## 📁 파일 구조

```
market-report/
├── index.html                        # 대시보드 (Netlify 배포)
├── scripts/
│   └── market_report.py              # 메인 실행 스크립트
└── .github/
    └── workflows/
        └── market-report.yml         # GitHub Actions 워크플로우
```

---

## ⚙️ GitHub Secrets 설정 목록

| Secret 이름 | 용도 |
|------------|------|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID |
| `NOTION_TOKEN` | Notion 인테그레이션 토큰 (비밀 워크스페이스) |

---

## 📈 수집 지표 목록

| 분류 | 지표 |
|------|------|
| 국내 | 코스피, 코스닥, 코스피 거래대금, 코스닥 거래대금, 원달러 |
| 미국 | S&P 500, 나스닥, 미국 10년물 금리, 미국 30년물 금리 |
| 해외 | 상하이, DAX |
| 원자재 | WTI, 골드, 비트코인 |
| 기타 | VIX, 달러인덱스 |
