# CLAUDE.md — 서울/수도권 아파트 호가 리포트 시스템

> 개인 작업 스타일·환경 설정은 `.claude/CLAUDE.md` 참고. 이 문서는 **프로젝트 자체**의 구조·실행·관례를 다룬다.

## 한 줄 요약
네이버 부동산(`fin.land.naver.com`) 매물을 행정구역 단위로 수집 → 면적·층·향·동별 호가 분석 → 텔레그램 리포트 자동 전송. GitHub Actions로 주 3회(월·목·토 08:30 KST) 실행.

## 아키텍처 (데이터 흐름)
```
.env (REGION_NAME, MY_HOME, TARGET_HOME, TELEGRAM_*, FILTER_*)
   │
   ▼
RegionCollector ──→ NaverLandApiClient (curl_cffi, chrome131 impersonate)
   │   1) 행정구역명 → cortarNo (data/ref CSV 우선, geopy 좌표)
   │   2) complexClusters(POST) → 단지번호 목록 (공급면적 필터)
   │   3) article/list(POST, cursor 페이지네이션) → 매물 → Property
   ▼
properties_to_dataframe (한글 컬럼) ──→ data/raw/{지역명}/properties_YYYYMMDD_HHMMSS.csv
   │   (my_home은 basicInfo API로 매물특징설명 보강 후 재저장)
   ▼
ComplexAnalyzer.analyze_complex_from_dataframe  (단지별 매매 A1 기준)
   │   면적대(floor m²)별 가격분포 / 층·향·동 상세 / 특이매물(키워드) / 전세 B1 분포
   ▼
migration_analyzer.build_migration_report  (내 단지 vs 타겟, 59·84㎡, 1M/3M/6M/1Y 추세)
   ▼
TelegramNotifier  ──→ ① 내 단지 상세 ② 전 단지 호가 ③ 이사 비교(스냅샷+추세)
                     (전송 성공분은 data/telegram_logs/ 에 CSV 로깅)
```

## 핵심 모듈
| 경로 | 역할 | 비고 |
|------|------|------|
| `scripts/run_pipeline.py` | 인메모리 파이프라인 엔트리 | `python scripts/run_pipeline.py` |
| `src/collectors/api_client.py` | 네이버 API 클라이언트 | **fin API**(`get_complex_clusters_fin`, `get_complex_article_list_fin`, `get_article_basic_info`)가 활성 경로 |
| `src/collectors/region_collector.py` | 행정구역→매물 수집 + cortarNo 매핑 | `collect_properties_by_region`가 메인 |
| `src/analyzers/complex_analyzer.py` | 단지 분석 | **`analyze_complex_from_dataframe`만 활성**(아래 주의) |
| `src/analyzers/migration_analyzer.py` | 이사 비교/시계열 | 파일명 날짜 기반 구간 매칭 |
| `src/notifiers/telegram.py` | 리포트 포맷·전송 | `parse_mode=HTML` |
| `src/config/env_loader.py` | `.env` 로더 | `EnvConfig` 정적 메서드 |
| `data/ref/국토교통부_행정구역법정동코드_*.CSV` | cortarNo 매핑 소스 | 정부 공식 데이터 |

## 실행
```bash
python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt
# 최소 의존성만: curl_cffi pandas numpy requests python-dotenv pytz geopy
./venv/bin/python scripts/run_pipeline.py
```
`.env` 필수 키: `REGION_NAME`(쉼표 구분), `MY_HOME_COMPLEX_NAME`, `MY_HOME_COMPLEX_AREA`(전용 ㎡), `TARGET_HOME_COMPLEX_NAME`(쉼표 구분), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. 선택: `FILTER_DPRC_MIN/MAX`(만원), `FILTER_SPC_MIN/MAX`(공급 ㎡).

## 데이터 관례
- raw CSV 컬럼은 **한글**(`거래유형코드`, `가격`(만원), `전용면적제곱미터`, `층수정보`(`현재/전체`), `방향`, `매물특징설명` 등).
- 거래유형코드: `A1`=매매, `B1`=전세, `B2`=월세. 가격 분석은 A1 기준, 전세는 별도.
- 면적대 = `floor(전용면적제곱미터)` (예: 51.5·51.9 → 51로 묶음).
- 시계열은 `data/raw/{지역}/properties_*.csv` 파일명의 날짜로 1M/3M/6M/1Y 구간에 1:1 매칭(중복 배정 없음).
- `data/raw/`, `data/telegram_logs/`는 gitignore 대상(런타임 산출물).

## ⚠️ 알려진 함정 (수정 전 인지)
- `ComplexAnalyzer.analyze_complex()` / `load_recent_offers()`는 `offers_*.csv`를 찾지만 파이프라인은 `properties_*.csv`를 쓴다 → **파일 기반 경로는 끊겨 있음.** DataFrame 경로(`analyze_complex_from_dataframe`)만 사용.
- API 호출 실패·429는 **조용히 빈 결과를 반환**(로그 없음)해 수집 누락이 보이지 않을 수 있다.
- cortarNo 하드코딩 폴백(`generate_cortar_no_from_region_name`)과 `search_region_info`/`get_article_list_by_region`는 CSV 조회 성공 시 사실상 죽은 경로.
- 자동 테스트 없음(`tests/*`는 라이브 API를 때리는 print 스크립트, assertion 없음).

## gstack 워크플로 (이 프로젝트에 적용)
UI(웹/iOS)가 없는 Python 데이터 파이프라인 → 다음 스킬만 유효:

| 스킬 | 용도 | 트리거 시점 |
|------|------|-------------|
| `/review` | 버그·경쟁상태·escaping·완결성 감사 | 수집/분석 로직 변경 후 |
| `/cso` | 시크릿(텔레그램 토큰)·`.env`·외부호출 보안 감사 | 토큰/입출력 경로 변경 시 |
| `/health` | 타입체커·린터·테스트·데드코드 점수화 | 정기 / 리팩터링 전 |
| `/investigate` | 수집 0건·429·파싱 실패 근본원인 추적 | 파이프라인 장애 시 |
| `/document-release` | README·이 문서 최신화 | 출하 직전 |
| `/ship` | 테스트 부트스트랩 + PR | 변경 출하 시 |
| `/retro` | 커밋 기반 주간 회고 | 주 단위 |
| `/careful`·`/guard` | 파괴적 명령/편집 가드 | 데이터/운영 작업 시 |

**해당 없음**(UI·앱 부재): `/design-*`, `/qa`, `/browse`, `/canary`, `/benchmark`, `/ios-*`, `/setup-deploy`(서버 배포 아님).

**권장 순서:** 변경 → `/review` (+ `/cso` 시크릿 영향 시) → `/health`로 회귀 확인 → `/ship`.
