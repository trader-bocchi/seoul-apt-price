# 네이버 부동산 API 참조 문서 (새로운 크롤링 방법)

## 개요
네이버 부동산 모바일 웹사이트(`m.land.naver.com`)에서 특정 행정구역의 모든 부동산 매물 정보를 효율적으로 수집하기 위한 새로운 API 분석 결과입니다.

이 문서는 사용자가 네이버 부동산에서 **"해당 지역만 보기"를 선택하고 "매물목록"을 클릭했을 때** 사용되는 API를 기반으로 합니다.

## 주요 API 엔드포인트

### 1. 지역별 매물 목록 조회 API (페이지네이션 지원)

**엔드포인트:** `GET https://m.land.naver.com/cluster/ajax/articleList`

**설명:** 특정 행정구역(cortarNo)의 모든 매물을 페이지네이션으로 조회하는 API입니다. 이 API는 사용자가 네이버 부동산에서 지역을 선택하고 "매물목록"을 클릭했을 때 사용되는 방식과 동일합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `rletTpCd` | string | 필수 | 부동산 유형 코드 | `APT` (아파트), `OPST` (오피스텔), `VL` (빌라) |
| `tradTpCd` | string | 필수 | 거래 유형 코드 | `A1` (매매), `B1` (전세), `B2` (월세) |
| `z` | number | 필수 | 지도 줌 레벨 | `14` |
| `lat` | number | 필수 | 중심 위도 | `37.4473` |
| `lon` | number | 필수 | 중심 경도 | `127.1493` |
| `btm` | number | 필수 | 지도 하단 경계 위도 | `37.4056195` |
| `lft` | number | 필수 | 지도 왼쪽 경계 경도 | `127.0763439` |
| `top` | number | 필수 | 지도 상단 경계 위도 | `37.4889573` |
| `rgt` | number | 필수 | 지도 오른쪽 경계 경도 | `127.2222561` |
| `cortarNo` | string | 필수 | 지역 코드 | `4113110100` |
| `totCnt` | number | 선택 | 총 매물 개수 (첫 페이지에서 확인 가능) | `209` |
| `page` | number | 선택 | 페이지 번호 (1부터 시작, 기본값: 1) | `1`, `2`, `3` ... |
| `showR0` | string | 선택 | R0 상태 매물 표시 여부 | 빈 문자열 |

#### 요청 예시

**첫 페이지 조회:**
```http
GET https://m.land.naver.com/cluster/ajax/articleList?rletTpCd=APT&tradTpCd=A1&z=14&lat=37.4473&lon=127.1493&btm=37.4056195&lft=127.0763439&top=37.4889573&rgt=127.2222561&showR0=&totCnt=209&cortarNo=4113110100
```

**두 번째 페이지 조회:**
```http
GET https://m.land.naver.com/cluster/ajax/articleList?rletTpCd=APT&tradTpCd=A1&z=14&lat=37.4473&lon=127.1493&btm=37.4056195&lft=127.0763439&top=37.4889573&rgt=127.2222561&showR0=&totCnt=209&cortarNo=4113110100&page=2
```

#### 응답 데이터 구조

```json
{
  "code": "success",
  "hasPaidPreSale": false,
  "more": true,
  "TIME": false,
  "z": 14,
  "page": 1,
  "body": [
    {
      "atclNo": "2601403416",
      "cortarNo": "4113110100",
      "atclNm": "산성역자이푸르지오2단지",
      "atclStatCd": "R0",
      "rletTpCd": "A01",
      "uprRletTpCd": "A01",
      "rletTpNm": "아파트",
      "tradTpCd": "A1",
      "tradTpNm": "매매",
      "vrfcTpCd": "OWNER",
      "flrInfo": "7/29",
      "prc": 145000,
      "rentPrc": 0,
      "hanPrc": "14억 5,000",
      "spc1": "99",
      "spc2": "74.92",
      "direction": "남서향",
      "atclCfmYmd": "26.01.07.",
      "repImgUrl": "/20260107_235/1767756714355VYcQc_JPEG/74A%C5%B8%C0%D4_%289%29.jpg",
      "repImgTpCd": "10",
      "repImgThumb": "f130_98",
      "lat": 37.448918,
      "lng": 127.148165,
      "atclFetrDesc": "입주,최고의뷰,귀한4B,드레스룸,시스템에어컨풀,공청",
      "tagList": ["2년이내", "대단지", "방세개"],
      "bildNm": "204동",
      "minute": 0,
      "sameAddrCnt": 22,
      "sameAddrDirectCnt": 0,
      "sameAddrHash": "24A01A1Nabbe6e1621271270f5c9bd14032f5eba39f7e85f2fb59b2ea4b41f09ba147212",
      "sameAddrMaxPrc": "14억 5,000",
      "sameAddrMinPrc": "14억 5,000",
      "cpid": "bizmk",
      "cpNm": "매경부동산",
      "cpCnt": 8,
      "rltrNm": "산성원탑공인중개사사무소",
      "directTradYn": "N",
      "minMviFee": 0,
      "maxMviFee": 0,
      "etRoomCnt": 0,
      "tradePriceHan": "",
      "tradeRentPrice": 0,
      "tradeCheckedByOwner": false,
      "cpLinkVO": {
        "cpId": "bizmk",
        "mobileArticleLinkTypeCode": "NONE",
        "mobileBmsInspectPassYn": "Y",
        "pcArticleLinkUseAtArticleTitle": false,
        "pcArticleLinkUseAtCpName": false,
        "mobileArticleLinkUseAtArticleTitle": false,
        "mobileArticleLinkUseAtCpName": false
      },
      "dtlAddrYn": "N",
      "dtlAddr": "",
      "isVrExposed": false,
      "isSafeLessorOfHug": false
    }
  ]
}
```

#### 응답 필드 설명

##### body 배열 (개별 매물 상세 정보)

| 필드 | 타입 | 설명 |
|------|------|------|
| `atclNo` | string | 매물 번호 (고유 ID) |
| `cortarNo` | string | 지역 코드 |
| `atclNm` | string | 단지명 |
| `atclStatCd` | string | 매물 상태 코드 (R0: 매물 등록) |
| `rletTpCd` | string | 부동산 유형 코드 (A01: 아파트) |
| `rletTpNm` | string | 부동산 유형명 |
| `tradTpCd` | string | 거래 유형 코드 (A1: 매매) |
| `tradTpNm` | string | 거래 유형명 |
| `vrfcTpCd` | string | 검증 타입 코드 (OWNER: 집주인, DOC: 중개사) |
| `flrInfo` | string | 층수 정보 (예: "7/29" = 7층/29층) |
| `prc` | number | 가격 (만원 단위) |
| `rentPrc` | number | 임대료 (만원 단위, 매매의 경우 0) |
| `hanPrc` | string | 한글 가격 표시 (예: "14억 5,000") |
| `spc1` | string | 전용면적 (평) |
| `spc2` | string | 전용면적 (㎡) |
| `direction` | string | 방향 (예: "남서향") |
| `atclCfmYmd` | string | 매물 확인일자 (예: "26.01.07.") |
| `lat` | number | 위도 |
| `lng` | number | 경도 |
| `atclFetrDesc` | string | 매물 특징 설명 |
| `tagList` | array | 매물 태그 리스트 |
| `bildNm` | string | 동명 (예: "204동") |
| `sameAddrCnt` | number | 동일 주소 매물 개수 |
| `sameAddrMaxPrc` | string | 동일 주소 최고가 |
| `sameAddrMinPrc` | string | 동일 주소 최저가 |
| `cpid` | string | 중개사 플랫폼 ID |
| `cpNm` | string | 중개사 플랫폼명 |
| `rltrNm` | string | 중개사명 |
| `directTradYn` | string | 직접 거래 여부 (Y/N) |
| `minMviFee` | number | 최소 관리비 |
| `maxMviFee` | number | 최대 관리비 |
| `isVrExposed` | boolean | VR 노출 여부 |

##### 페이지네이션 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `more` | boolean | 더 많은 페이지가 있는지 여부 |
| `page` | number | 현재 페이지 번호 |
| `z` | number | 줌 레벨 |

**중요 참고사항:**
- 각 페이지당 최대 20개의 매물이 반환됩니다.
- `more` 필드가 `true`이거나 현재 페이지의 `body` 배열 길이가 20개인 경우, 다음 페이지가 존재할 수 있습니다.
- 총 매물 개수(`totCnt`)는 첫 페이지 요청 시 URL에 포함될 수 있지만, 응답 본문에는 포함되지 않을 수 있습니다.
- 페이지 번호는 1부터 시작합니다.

### 2. 지역 정보 조회 (행정구역명 → cortarNo 변환)

행정구역명(예: "성남시 수정구 신흥동")을 입력받아 해당 지역의 `cortarNo`와 좌표를 조회하는 방법입니다.

#### 방법 1: Geopy를 사용한 주소 → 좌표 변환

```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="naver_land_crawler")
location = geolocator.geocode("성남시 수정구 신흥동", country_codes="kr")
lat = location.latitude
lon = location.longitude
```

#### 방법 2: cluster/clusterList API를 사용한 cortarNo 조회

좌표를 얻은 후, `cluster/clusterList` API를 호출하여 해당 지역의 `cortarNo`를 얻을 수 있습니다.

**엔드포인트:** `GET https://m.land.naver.com/cluster/clusterList`

**요청 파라미터:**
- `view`: `atcl`
- `rletTpCd`: `APT`
- `tradTpCd`: `A1`
- `z`: `14`
- `lat`, `lon`: 조회한 좌표
- `btm`, `lft`, `top`, `rgt`: 좌표 기준 넓은 영역 설정

**응답에서 cortar 정보 추출:**
```json
{
  "data": {
    "cortar": {
      "detail": {
        "cortarNo": "4113110100",
        "cortarNm": "신흥동",
        "regionName": "경기도 성남시 수정구 신흥동",
        "mapXCrdn": "127.1493",
        "mapYCrdn": "37.4473"
      }
    }
  }
}
```

## 사용 방법

### 1. 전체 수집 프로세스

1. **행정구역명 입력**: 사용자가 `.env` 파일에 `REGION_NAME=성남시 수정구 신흥동` 형식으로 입력
2. **지역 정보 조회**: 행정구역명을 기반으로 `cortarNo`와 좌표 조회
3. **경계 좌표 계산**: 중심 좌표를 기준으로 지역 경계 좌표 계산
4. **첫 페이지 조회**: `cluster/ajax/articleList` API로 첫 페이지 조회
5. **페이지네이션 수집**: `more` 필드나 페이지별 매물 개수를 확인하여 모든 페이지 수집
6. **데이터 저장**: 수집한 매물 정보를 CSV 파일로 저장

### 2. 페이지네이션 처리 전략

```python
# 첫 페이지 조회
first_page = get_article_list_by_region(cortar_no, ..., page=1)
properties = first_page.get("body", [])
more = first_page.get("more", False)

# 페이지네이션 처리
page = 2
while more or len(properties) >= 20:
    page_data = get_article_list_by_region(cortar_no, ..., page=page)
    page_body = page_data.get("body", [])
    
    if not page_body:
        break
    
    properties.extend(page_body)
    more = page_data.get("more", False)
    
    if not more and len(page_body) < 20:
        break
    
    page += 1
```

### 3. Python 스크래핑 예시 코드

```python
from src.collectors.region_collector import RegionCollector
from src.collectors.api_client import ApiConfig

# 수집기 초기화
api_config = ApiConfig(min_delay=1.0, timeout=10, max_retries=3)
collector = RegionCollector(api_config)

# 매물 수집
properties, complexes = collector.collect_properties_by_region(
    region_name="성남시 수정구 신흥동",
    rlet_tp_cd="APT",
    trad_tp_cd="A1"
)

print(f"수집된 매물: {len(properties)}개")
```

## 장점

1. **효율성**: 기존 그리드 방식보다 훨씬 적은 API 호출로 모든 매물 수집 가능
2. **정확성**: 네이버 부동산에서 실제로 표시하는 매물과 동일한 데이터 수집
3. **단순성**: 복잡한 클러스터 처리나 영역 분할이 필요 없음
4. **페이지네이션**: 명확한 페이지네이션 구조로 모든 매물을 빠짐없이 수집

## 주의사항

1. **API 접근 제한**: 과도한 요청은 IP 차단을 유발할 수 있으므로 적절한 딜레이를 두고 요청하세요.
2. **인증**: 현재 확인된 API는 별도의 인증이 필요하지 않지만, Referer 헤더가 필요할 수 있습니다.
3. **법적 고지**: 이 API는 네이버의 공식 API가 아닐 수 있으며, 웹사이트 구조 변경에 따라 동작하지 않을 수 있습니다. 스크래핑 시 관련 법규를 준수하세요.
4. **totCnt 파라미터**: 첫 페이지 요청 시 `totCnt` 파라미터가 URL에 포함될 수 있지만, 실제 총 개수는 페이지네이션을 통해 확인해야 합니다.

## 기존 방법과의 비교

### 기존 방법 (그리드 방식)
- 넓은 영역을 작은 그리드로 분할하여 수집
- 클러스터 처리 및 확장 수집 필요
- 많은 API 호출 필요 (수십~수백 회)
- 복잡한 로직

### 새로운 방법 (지역 기반 페이지네이션)
- 행정구역명으로 직접 수집
- 페이지네이션으로 모든 매물 수집
- 적은 API 호출 (페이지 수만큼)
- 간단한 로직

## 추가 조사 필요 사항

1. **totCnt 파라미터**: 응답 본문에 총 매물 개수가 포함되는지 확인 필요
2. **최대 페이지 수**: 실제 최대 페이지 수 제한이 있는지 확인 필요
3. **정렬 방식**: 매물이 어떤 순서로 정렬되는지 확인 필요

