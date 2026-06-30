# 서울/수도권 아파트 호가 리포트 시스템

관심 단지의 네이버 부동산 매물을 수집하여 면적·층·향별로 분석하고, 텔레그램으로 자동 리포트를 전송하는 시스템입니다.

## 주요 기능

- **자동 수집**: 네이버 부동산에서 지정 지역의 아파트 매물 수집
- **면적별 분석**: 공급면적 기준 호가 분포 (최저·최고·중앙값)
- **상세 분석**: 내 단지의 층별·향별·동별 호가 차이 분석
- **텔레그램 알림**: 분석 결과를 텔레그램 메시지로 자동 전송

## 설치

```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

> Python 3.11+ 권장. `curl_cffi` 패키지가 포함됩니다.

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

# 면적 필터 (공급면적 m² 단위, 선택사항)
FILTER_SPC_MIN=65       # 최소 65m²
FILTER_SPC_MAX=115      # 최대 115m²

# 단지 수집 동시성 (선택사항, 기본 4; 429 잦으면 낮추거나 1=순차)
COLLECT_MAX_WORKERS=4
```

> **주의:** `FILTER_SPC_MIN/MAX`는 **공급면적 m²** 단위입니다 (평 단위가 아님).

## 실행 방법

### 파이프라인 실행 (수집 → 분석 → 전송)

```bash
python scripts/run_pipeline.py
```

지역별 raw 데이터를 `data/raw/{지역명}/` 에 즉시 저장하며, 전체 완료 후 텔레그램으로 리포트를 전송합니다.

## 데이터 저장 위치

```
data/
├── raw/
│   ├── {지역명}/
│   │   └── properties_YYYYMMDD_HHMMSS.csv   # 지역별 수집 매물
│   └── properties_YYYYMMDD_HHMMSS_ALL.csv   # 전체 합산 (중복 제거)
├── ref/
│   └── 국토교통부_행정구역법정동코드_*.CSV       # 지역코드 참조
└── telegram_logs/                             # 전송 로그
```

## 텔레그램 리포트 예시

```
📊 호가 리포트
2026-04-04 (금) 08:30
────────────────────────

🏠 산들마을  30건
 51㎡  8.4~11.5억  중앙 9.2억  30건

🎯 산성역포레스티아  183건
 59㎡  9.0~14.0억  중앙 11.5억  109건
 84㎡  12.0~16.0억  중앙 14.0억   74건
```

## 의존성

주요 패키지:

| 패키지 | 용도 |
|--------|------|
| `curl_cffi` | HTTP 요청 (브라우저 호환 TLS) |
| `pandas` | 데이터 분석 |
| `geopy` | 지역명 → 좌표 변환 |
| `python-dotenv` | 환경 변수 로드 |
