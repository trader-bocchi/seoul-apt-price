# 서울/수도권 아파트 호가 리포트 시스템

관심 단지의 네이버 부동산 매물을 수집하여 면적·층·향별로 분석하고, 텔레그램으로 자동 리포트를 전송하는 시스템입니다.

## 주요 기능

- **자동 수집**: 네이버 부동산 API에서 지정 지역의 아파트 매물 수집
- **면적별 분석**: 전용면적 기준 호가 분포 (최저·최고·중앙값)
- **상세 분석**: 내 단지의 층별·향별·동별 호가 차이 분석
- **텔레그램 알림**: 분석 결과를 텔레그램 메시지로 자동 전송
- **GitHub Actions**: 월/목/토 오전 8시 30분(KST) 자동 실행

## 설치

```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## 환경 변수 설정 (`.env`)

```env
# 수집 지역 (쉼표로 여러 지역 지정 가능)
REGION_NAME=경기도 성남시 수정구 신흥동, 경기도 성남시 중원구 여수동

# 내 집 단지명 (상세 분석 대상)
MY_HOME_COMPLEX_NAME=산들마을
MY_HOME_COMPLEX_AREA=51        # 내 집 전용면적 (m²)

# 관심 단지 목록 (쉼표 구분)
TARGET_HOME_COMPLEX_NAME=산성역포레스티아, 산성역자이푸르지오1단지

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 가격 필터 (만원 단위, 선택사항)
FILTER_DPRC_MIN=70000   # 최소 7억
FILTER_DPRC_MAX=160000  # 최대 16억

# 면적 필터 (공급면적 m² 단위 = Naver API spc1 기준, 선택사항)
FILTER_SPC_MIN=65       # 최소 65m²
FILTER_SPC_MAX=115      # 최대 115m²
```

> **주의:** `FILTER_SPC_MIN/MAX`는 **공급면적 m²** 단위입니다 (Naver API의 `spc1` 기준, 평 단위가 아님).

## 실행 방법

### 인메모리 파이프라인 (GitHub Actions와 동일)

수집 → 분석 → 텔레그램 전송을 한 번에 실행합니다. 파일 저장 없음.

```bash
python scripts/run_pipeline.py
```

### 로컬 2단계 실행 (데이터 저장 후 분석)

```bash
# 1단계: 매물 수집 및 CSV 저장
python scripts/collect_by_region.py

# 2단계: 저장된 데이터로 텔레그램 리포트 전송
python scripts/send_telegram_report.py
```

## GitHub Actions 자동화

### 자동 실행 일정

| 요일 | KST | UTC (cron) |
|------|-----|------------|
| 월요일 | 08:30 | 일 23:30 |
| 목요일 | 08:30 | 수 23:30 |
| 토요일 | 08:30 | 금 23:30 |

### 수동 트리거 방법

**방법 1 — GitHub 웹:**
1. 저장소 → **Actions** 탭 → **Weekly Apartment Price Report**
2. 우측 **"Run workflow"** 버튼 클릭 → **Run workflow** 확인

**방법 2 — GitHub CLI:**
```bash
gh workflow run weekly_report.yml --ref master
```

**방법 3 — GitHub API:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/trader-bocchi/seoul-apt-price/actions/workflows/weekly_report.yml/dispatches \
  -d '{"ref":"master"}'
```

### GitHub Actions 설정 (Secrets & Variables)

저장소 **Settings → Secrets and variables → Actions** 에서 설정:

**Secrets (민감 정보):**
| 키 | 설명 |
|----|------|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID |

**Variables (설정값):**
| 키 | 예시 | 설명 |
|----|------|------|
| `REGION_NAME` | `경기도 성남시 수정구 신흥동, ...` | 수집 지역 |
| `MY_HOME_COMPLEX_NAME` | `산들마을` | 내 집 단지명 |
| `MY_HOME_COMPLEX_AREA` | `51` | 내 집 전용면적 (m²) |
| `TARGET_HOME_COMPLEX_NAME` | `산성역포레스티아, ...` | 관심 단지 목록 |
| `FILTER_DPRC_MIN` | `70000` | 최소 가격 (만원) |
| `FILTER_DPRC_MAX` | `160000` | 최대 가격 (만원) |
| `FILTER_SPC_MIN` | `65` | 최소 공급면적 (m²) |
| `FILTER_SPC_MAX` | `115` | 최대 공급면적 (m²) |

## 데이터 저장 위치 (로컬 실행 시)

```
data/
├── raw/{지역명}/offers_YYYYMMDD.csv   # 수집된 매물
├── ref/국토교통부_행정구역법정동코드_*.CSV  # 지역코드 참조
└── telegram_logs/                     # 전송 로그
```

## 텔레그램 리포트 예시

```
📊 호가 리포트
2026-03-31 (화) 08:30
────────────────────────

🏠 산들마을  17건
 51㎡  8.5~11.5억  중앙 9.1억  17건

🎯 산성역포레스티아  190건
 59㎡  9.0~14.0억  중앙 11.5억  120건
 84㎡  12.0~16.0억  중앙 14.0억   70건
```
