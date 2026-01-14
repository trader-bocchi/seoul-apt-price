# 네이버 부동산 매물 수집 및 텔레그램 알림 시스템

네이버 부동산 API를 활용하여 관심 단지의 매물 정보를 수집하고, 텔레그램으로 분석 리포트를 전송하는 시스템입니다.

## 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
```

## 환경 변수 설정

`.env` 파일 생성 및 설정:

```env
# 행정구역명 설정 (필수)
REGION_NAME=성남시 수정구 신흥동
# 또는 여러 지역 지정 (쉼표로 구분)
REGION_NAME=성남시 수정구 신흥동,서울시 강동구 상일동

# 분석 대상 단지 설정 (필수, 텔레그램 리포트용)
MY_HOME_COMPLEX_NAME=내_집_단지명
TARGET_HOME_COMPLEX_NAME=관심_단지명1,관심_단지명2,관심_단지명3

# 텔레그램 알림 설정 (선택)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 필터 조건 (선택사항)
FILTER_DPRC_MIN=80000   # 최소 가격: 8억 (만원 단위)
FILTER_DPRC_MAX=130000  # 최대 가격: 13억 (만원 단위)
FILTER_SPC_MIN=33       # 최소 면적: 33평
FILTER_SPC_MAX=99       # 최대 면적: 99평
```

**참고:** 
- `REGION_NAME`에 행정구역명을 입력하면 시스템이 자동으로 CSV 파일(`data/ref/국토교통부_행정구역법정동코드_20250807.CSV`)에서 `cortarNo`를 찾아 사용합니다.
- 수동으로 `cortarNo`를 지정할 필요가 없습니다.

## 실행

### 지역별 매물 수집

지역을 지정하여 매물을 수집합니다:

```bash
python scripts/collect_by_region.py
```

### 텔레그램 리포트 전송

수집된 데이터를 분석하여 텔레그램으로 리포트를 전송합니다:

```bash
python scripts/send_telegram_report.py
```

**리포트 내용:**
- 각 단지별 개별 분석 리포트 (평형별 가격 정보 포함)
- 내 단지와 목표 단지 간 비교 분석 리포트

**참고:**
- `data/raw`에 저장된 모든 데이터를 읽어서 분석합니다
- `MY_HOME_COMPLEX_NAME`과 `TARGET_HOME_COMPLEX_NAME`에 설정한 단지명과 일치하는 매물만 분석합니다
- 전체 매물을 분석합니다 (최근 30일 제한 없음)

## 프로젝트 구조

```
seoul-apt-price/
├── scripts/                    # 실행 스크립트
│   ├── collect_by_region.py   # 지역별 매물 수집
│   └── send_telegram_report.py # 텔레그램 리포트 전송
├── tests/                      # 테스트 파일
│   ├── test_direct_api.py
│   └── test_region_search.py
├── src/                        # 소스 코드
│   ├── collectors/            # 데이터 수집 모듈
│   ├── config/               # 설정 관리
│   ├── notifiers/            # 알림 모듈 (텔레그램)
│   ├── processors/           # 데이터 처리 모듈
│   ├── storage/              # 데이터 저장 모듈
│   └── utils/                # 유틸리티 함수
├── data/                      # 데이터 파일
│   ├── raw/                  # 수집된 원시 데이터
│   │   └── {지역명}/
│   │       └── offers_YYYYMMDD.csv
│   ├── ref/                  # 참조 데이터
│   │   └── 국토교통부_행정구역법정동코드_20250807.CSV
│   └── telegram_logs/        # 텔레그램 로그
├── old/                       # 오래된 파일 (보관용)
└── venv/                      # 가상환경
```

## 데이터 저장 위치

- Raw 데이터: `data/raw/{지역명}/offers_YYYYMMDD.csv`
- 참조 데이터: `data/ref/국토교통부_행정구역법정동코드_20250807.CSV`
- 텔레그램 로그: `data/telegram_logs/`

## Git 연동

Git 저장소에 업로드하는 방법은 `GIT_SETUP.md` 파일을 참고하세요.

## 주요 기능

- **지역별 매물 수집**: 행정구역명을 입력하면 자동으로 매물 수집
- **평형별 분석**: 같은 단지 내에서 평형별로 가격 분석
- **가격 필터**: 가격대와 면적대 필터 조건 지원
- **텔레그램 리포트**: 개별 단지 분석 + 비교 분석 리포트 자동 전송
