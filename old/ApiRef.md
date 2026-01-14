# 네이버 부동산 API 참조 문서

## 개요
네이버 부동산 모바일 웹사이트(`m.land.naver.com`)에서 특정 지역의 부동산 매물 정보를 스크래핑하기 위한 API 분석 결과입니다.

## 주요 API 엔드포인트

### 1. 클러스터 목록 조회 API

**엔드포인트:** `GET https://m.land.naver.com/cluster/clusterList`

**설명:** 특정 지역의 부동산 매물 클러스터 정보와 단지 정보를 조회하는 API입니다. 지도에 표시되는 매물 마커와 단지 정보를 제공합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `view` | string | 필수 | 조회 타입 | `atcl` (매물) |
| `rletTpCd` | string | 필수 | 부동산 유형 코드 | `APT:JGC` (아파트, 재건축) |
| `tradTpCd` | string | 필수 | 거래 유형 코드 | `A1` (매매), `B1` (전세), `B2` (월세) |
| `z` | number | 필수 | 지도 줌 레벨 | `17` |
| `lat` | number | 필수 | 중심 위도 | `37.4514469` |
| `lon` | number | 필수 | 중심 경도 | `127.1504679` |
| `btm` | number | 필수 | 지도 하단 경계 위도 | `37.4462086` |
| `lft` | number | 필수 | 지도 왼쪽 경계 경도 | `127.1437516` |
| `top` | number | 필수 | 지도 상단 경계 위도 | `37.4566848` |
| `rgt` | number | 필수 | 지도 오른쪽 경계 경도 | `127.1571842` |
| `pCortarNo` | string | 선택 | 상위 지역 코드 | 빈 문자열 또는 지역 코드 (클러스터 클릭 시 `17_4113110100` 형식으로 전달) |
| `addon` | string | 선택 | 추가 정보 타입 | `COMPLEX` (단지 정보 포함) |
| `bAddon` | string | 선택 | 추가 정보 타입 (클러스터 클릭 시) | `COMPLEX` (클러스터 클릭 시 자동 포함) |
| `isOnlyIsale` | boolean | 선택 | 전매만 조회 여부 | `false` |

#### 요청 예시

**기본 호출:**
```http
GET https://m.land.naver.com/cluster/clusterList?view=atcl&rletTpCd=APT%3AJGC&tradTpCd=A1&z=17&lat=37.4514469&lon=127.1504679&btm=37.4462086&lft=127.1437516&top=37.4566848&rgt=127.1571842&pCortarNo=&addon=COMPLEX&isOnlyIsale=false
```

**클러스터 클릭 시 자동 호출 (pCortarNo와 bAddon 파라미터 포함):**
```http
GET https://m.land.naver.com/cluster/clusterList?view=atcl&rletTpCd=APT&tradTpCd=A1&z=17&lat=37.4514469&lon=127.1504679&btm=37.4460979&lft=127.1436122&top=37.4567956&rgt=127.1573236&pCortarNo=17_4113110100&addon=COMPLEX&bAddon=COMPLEX&isOnlyIsale=false
```

**참고:** 클러스터를 클릭하면 네이버는 자동으로 `cluster/clusterList` API를 호출하며, 이 호출에는 `pCortarNo`와 `bAddon=COMPLEX` 파라미터가 포함됩니다. 이 응답에는 해당 클러스터 영역의 단지 정보(COMPLEX 배열)가 포함되어 있어, 클러스터 내부 단지 정보를 효율적으로 수집할 수 있습니다.

#### 응답 데이터 구조

```json
{
  "code": "success",
  "data": {
    "ARTICLE": [
      {
        "lgeo": "2120333113022",
        "count": 15,
        "z": 17,
        "lat": 37.44892579,
        "lon": 127.1485616,
        "psr": 0.6,
        "tourExist": false
      },
      {
        "lgeo": "2120333112311",
        "count": 1,
        "z": 17,
        "lat": 37.449275,
        "lon": 127.147274,
        "itemId": "2566550454",
        "tradTpCd": "A1",
        "rletNm": "아파트",
        "tradNm": "매매",
        "prc": "130000",
        "priceTtl": "13억",
        "psr": 0.5,
        "minMviFee": 0,
        "maxMviFee": 0,
        "tourExist": false
      }
    ],
    "COMPLEX": [
      {
        "lgeo": "2121222002222",
        "lat": "37.452426",
        "lon": "127.156264",
        "count": 1,
        "itemId": "14525",
        "ttl": "진흥더블파크",
        "si1": "200505",
        "si2": "188",
        "si3": "1,981",
        "li1": "200505",
        "li2": "188",
        "li3": "1,981",
        "poiType": "CC",
        "dealMedianUnitPrice": "2,418",
        "isComplexTourExist": false,
        "articleCount": 0,
        "itemIdList": ["14525"]
      }
    ],
    "cpolygon": {
      "crdnData": "37.45633406,127.14918883|37.45599791,127.1497378|..."
    },
    "z": 17,
    "cortar": {
      "detail": {
        "cortarNo": "4113110100",
        "cortarNm": "신흥동",
        "cortarType": "sec",
        "cityLngNm": "경기도",
        "cityNm": "경기도",
        "dvsnNm": "성남시 수정구",
        "secNm": "신흥동",
        "mapXCrdn": "127.1493",
        "mapYCrdn": "37.4473",
        "cityNo": "4100000000",
        "dvsnNo": "4113100000",
        "secNo": "4113110100",
        "regionName": "경기도 성남시 수정구 신흥동"
      },
      "dvsnLat": "37.450396",
      "dvsnLon": "127.145634"
    },
    "NOEXPSCNT": 0
  }
}
```

#### 응답 필드 설명

##### ARTICLE 배열 (매물 클러스터 정보)

| 필드 | 타입 | 설명 |
|------|------|------|
| `lgeo` | string | 지역 지오코드 |
| `count` | number | 해당 클러스터의 매물 개수 |
| `z` | number | 줌 레벨 |
| `lat` | number | 위도 |
| `lon` | number | 경도 |
| `psr` | number | 클러스터 표시 크기 비율 |
| `tourExist` | boolean | VR 투어 존재 여부 |
| `itemId` | string | (개별 매물인 경우) 매물 ID |
| `tradTpCd` | string | (개별 매물인 경우) 거래 유형 코드 |
| `rletNm` | string | (개별 매물인 경우) 부동산 유형명 |
| `tradNm` | string | (개별 매물인 경우) 거래 유형명 |
| `prc` | string | (개별 매물인 경우) 가격 (만원 단위) |
| `priceTtl` | string | (개별 매물인 경우) 가격 전체 표시 문자열 |
| `minMviFee` | number | (개별 매물인 경우) 최소 관리비 |
| `maxMviFee` | number | (개별 매물인 경우) 최대 관리비 |

**참고:** `count`가 1인 경우 개별 매물 정보가 포함되며, 1보다 큰 경우 클러스터 정보만 포함됩니다.

##### COMPLEX 배열 (단지 정보)

| 필드 | 타입 | 설명 |
|------|------|------|
| `lgeo` | string | 지역 지오코드 |
| `lat` | string | 위도 |
| `lon` | string | 경도 |
| `count` | number | 단지 개수 |
| `itemId` | string | 단지 ID |
| `ttl` | string | 단지명 |
| `si1` | string | 시세 정보 1 (건축년도?) |
| `si2` | string | 시세 정보 2 |
| `si3` | string | 시세 정보 3 |
| `li1` | string | 리스 정보 1 |
| `li2` | string | 리스 정보 2 |
| `li3` | string | 리스 정보 3 |
| `poiType` | string | POI 타입 (CC = Complex?) |
| `dealMedianUnitPrice` | string | 매매 중위 평당가 (만원) |
| `leaseMedianRate` | string | 전세 중위 보증금 (만원) |
| `isComplexTourExist` | boolean | 단지 VR 투어 존재 여부 |
| `articleCount` | number | 매물 개수 |
| `itemIdList` | array | 단지 ID 목록 |

##### cortar 객체 (지역 정보)

| 필드 | 타입 | 설명 |
|------|------|------|
| `detail.cortarNo` | string | 지역 코드 |
| `detail.cortarNm` | string | 지역명 |
| `detail.cortarType` | string | 지역 타입 |
| `detail.cityLngNm` | string | 시/도명 (전체) |
| `detail.cityNm` | string | 시/도명 |
| `detail.dvsnNm` | string | 시/군/구명 |
| `detail.secNm` | string | 동명 |
| `detail.mapXCrdn` | string | 지도 X 좌표 (경도) |
| `detail.mapYCrdn` | string | 지도 Y 좌표 (위도) |
| `detail.regionName` | string | 전체 지역명 |

#### 실제 응답 예시

```json
{
  "code": "success",
  "data": {
    "ARTICLE": [
      {
        "lgeo": "2120333112311",
        "count": 1,
        "z": 17,
        "lat": 37.449275,
        "lon": 127.147274,
        "itemId": "2566550454",
        "tradTpCd": "A1",
        "rletNm": "아파트",
        "tradNm": "매매",
        "prc": "130000",
        "priceTtl": "13억",
        "psr": 0.5,
        "minMviFee": 0,
        "maxMviFee": 0,
        "tourExist": false
      },
      {
        "lgeo": "2120333112313",
        "count": 1,
        "z": 17,
        "lat": 37.450842,
        "lon": 127.147726,
        "itemId": "2600693288",
        "tradTpCd": "A1",
        "rletNm": "아파트",
        "tradNm": "매매",
        "prc": "55000",
        "priceTtl": "5억 5,000",
        "psr": 0.5,
        "minMviFee": 0,
        "maxMviFee": 0,
        "tourExist": false
      },
      {
        "lgeo": "2120333113022",
        "count": 15,
        "z": 17,
        "lat": 37.44892579,
        "lon": 127.1485616,
        "psr": 0.6,
        "tourExist": false
      }
    ],
    "COMPLEX": [
      {
        "lgeo": "2121222002222",
        "lat": "37.452426",
        "lon": "127.156264",
        "count": 1,
        "itemId": "14525",
        "ttl": "진흥더블파크",
        "si1": "200505",
        "si2": "188",
        "si3": "1,981",
        "li1": "200505",
        "li2": "188",
        "li3": "1,981",
        "poiType": "CC",
        "dealMedianUnitPrice": "2,418",
        "isComplexTourExist": false,
        "articleCount": 0,
        "itemIdList": ["14525"]
      },
      {
        "lgeo": "2120333112130",
        "lat": "37.447418",
        "lon": "127.146797",
        "count": 1,
        "itemId": "137596",
        "ttl": "산성역자이푸르지오1단지",
        "si1": "202403",
        "si2": "1,852",
        "si3": "3,424",
        "li1": "202403",
        "li2": "1,852",
        "li3": "3,424",
        "poiType": "CC",
        "dealMedianUnitPrice": "5,231",
        "leaseMedianRate": "47",
        "isComplexTourExist": true,
        "articleCount": 0,
        "itemIdList": ["137596"]
      }
    ],
    "cpolygon": {
      "crdnData": "37.45633406,127.14918883|37.45599791,127.1497378|37.45625098,127.14996014|37.45295244,127.14960728|37.45259977,127.14951421|37.45227292,127.14937174|37.44970619,127.15295182|37.44942448,127.15329506|37.44902933,127.15359545|37.44820673,127.15394551|37.4475025,127.15440923|37.44502524,127.15690319|37.44463213,127.15642818|37.44440597,127.1560597|37.4425895,127.15232582|37.44197849,127.15098433|37.44117876,127.14858676|37.44013992,127.14576519|37.43954476,127.1446651|37.43967421,127.14458344|37.43766582,127.14090334|37.43836489,127.13998346|37.43853426,127.13970453|37.43911168,127.13793819|37.43926832,127.13764644|37.43938284,127.13751131|37.43962787,127.13732736|37.44221185,127.13614261|37.44410113,127.14248998|37.44420514,127.14273454|37.44468066,127.14367126|37.4454641,127.14471698|37.44583767,127.14510019|37.44628185,127.14542174|37.4467881,127.14459092|37.45173766,127.14079373|37.45172302,127.14074411|37.45243756,127.14060283|37.45271923,127.14046239|37.45278013,127.14039117|37.45342482,127.14064985|37.4540477,127.14062972|37.45404061,127.14079643|37.45462411,127.14119901|37.45484418,127.14142422|37.45485106,127.14170163|37.45527172,127.14244482|37.45532821,127.1430702|37.45525569,127.1435721|37.45538386,127.14405753|37.4556036,127.14455587|37.45594845,127.14500754|37.45598017,127.14511152|37.45602185,127.14543104|37.45589217,127.14569392|37.45599784,127.14645911|37.45595017,127.14666369|37.45605637,127.14711344|37.45642797,127.1478137|37.45629146,127.14870648|37.45645995,127.14904554|37.45633406,127.14918883"
    },
    "z": 17,
    "cortar": {
      "detail": {
        "cortarNo": "4113110100",
        "cortarNm": "신흥동",
        "cortarType": "sec",
        "cityLngNm": "경기도",
        "cityNm": "경기도",
        "dvsnNm": "성남시 수정구",
        "secNm": "신흥동",
        "mapXCrdn": "127.1493",
        "mapYCrdn": "37.4473",
        "cityNo": "4100000000",
        "dvsnNo": "4113100000",
        "secNo": "4113110100",
        "regionName": "경기도 성남시 수정구 신흥동"
      },
      "dvsnLat": "37.450396",
      "dvsnLon": "127.145634"
    },
    "NOEXPSCNT": 0
  }
}
```

### 2. 클러스터 내부 매물 목록 조회 API

**엔드포인트:** `GET https://m.land.naver.com/cluster/ajax/articleList`

**설명:** 클러스터(`count > 1`) 내부의 개별 매물 상세 목록을 조회하는 API입니다. `cluster/clusterList` API에서 발견된 클러스터의 `lgeo` 또는 `itemId`를 사용하여 해당 클러스터 내부의 모든 개별 매물 정보를 가져올 수 있습니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `itemId` | string | 필수 | 클러스터의 itemId (lgeo와 동일한 값) | `2120333113022` |
| `lgeo` | string | 필수 | 지역 지오코드 (itemId와 동일한 값) | `2120333113022` |
| `rletTpCd` | string | 필수 | 부동산 유형 코드 | `APT` (아파트) |
| `tradTpCd` | string | 필수 | 거래 유형 코드 | `A1` (매매), `B1` (전세), `B2` (월세) |
| `z` | number | 필수 | 지도 줌 레벨 | `17` |
| `lat` | number | 필수 | 중심 위도 | `37.4514469` |
| `lon` | number | 필수 | 중심 경도 | `127.1504679` |
| `btm` | number | 필수 | 지도 하단 경계 위도 | `37.4462086` |
| `lft` | number | 필수 | 지도 왼쪽 경계 경도 | `127.1437516` |
| `top` | number | 필수 | 지도 상단 경계 위도 | `37.4566848` |
| `rgt` | number | 필수 | 지도 오른쪽 경계 경도 | `127.1571842` |
| `mapKey` | string | 선택 | 지도 키 (보통 빈 문자열) | 빈 문자열 |
| `cortarNo` | string | 선택 | 지역 코드 | 빈 문자열 또는 지역 코드 |
| `showR0` | string | 선택 | R0 상태 매물 표시 여부 | 빈 문자열 |

#### 요청 예시

```http
GET https://m.land.naver.com/cluster/ajax/articleList?itemId=2120333113022&mapKey=&lgeo=2120333113022&rletTpCd=APT&tradTpCd=A1&z=17&lat=37.4514469&lon=127.1504679&btm=37.4462086&lft=127.1437516&top=37.4566848&rgt=127.1571842&cortarNo=&showR0=
```

#### 응답 데이터 구조

```json
{
  "code": "success",
  "hasPaidPreSale": false,
  "more": false,
  "TIME": false,
  "z": 17,
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
| `vrfcTpCd` | string | 검증 타입 코드 (OWNER: 집주인, DOC: 중개사, NDOC1: 중개사 등) |
| `flrInfo` | string | 층수 정보 (예: "7/29" = 7층/29층, "고/29" = 고층/29층) |
| `prc` | number | 가격 (만원 단위) |
| `rentPrc` | number | 임대료 (만원 단위, 매매의 경우 0) |
| `hanPrc` | string | 한글 가격 표시 (예: "14억 5,000") |
| `spc1` | string | 전용면적 (평) |
| `spc2` | string | 전용면적 (㎡) |
| `direction` | string | 방향 (예: "남서향", "남동향") |
| `atclCfmYmd` | string | 매물 확인일자 (예: "26.01.07.") |
| `repImgUrl` | string | 대표 이미지 URL |
| `repImgTpCd` | string | 대표 이미지 타입 코드 |
| `repImgThumb` | string | 대표 이미지 썸네일 |
| `lat` | number | 위도 |
| `lng` | number | 경도 |
| `atclFetrDesc` | string | 매물 특징 설명 |
| `tagList` | array | 매물 태그 리스트 (예: ["2년이내", "대단지", "방세개"]) |
| `bildNm` | string | 동명 (예: "204동") |
| `minute` | number | 분 (보통 0) |
| `sameAddrCnt` | number | 동일 주소 매물 개수 |
| `sameAddrDirectCnt` | number | 동일 주소 직접 거래 개수 |
| `sameAddrHash` | string | 동일 주소 해시 |
| `sameAddrMaxPrc` | string | 동일 주소 최고가 |
| `sameAddrMinPrc` | string | 동일 주소 최저가 |
| `cpid` | string | 중개사 플랫폼 ID |
| `cpNm` | string | 중개사 플랫폼명 |
| `cpCnt` | number | 중개사 개수 |
| `rltrNm` | string | 중개사명 |
| `directTradYn` | string | 직접 거래 여부 (Y/N) |
| `minMviFee` | number | 최소 관리비 |
| `maxMviFee` | number | 최대 관리비 |
| `etRoomCnt` | number | 기타 방 개수 |
| `tradePriceHan` | string | 거래 가격 한글 표시 |
| `tradeRentPrice` | number | 거래 임대료 |
| `tradeCheckedByOwner` | boolean | 집주인 확인 거래 여부 |
| `cpLinkVO` | object | 중개사 링크 정보 |
| `dtlAddrYn` | string | 상세 주소 여부 (Y/N) |
| `dtlAddr` | string | 상세 주소 |
| `isVrExposed` | boolean | VR 노출 여부 |
| `isSafeLessorOfHug` | boolean | 안전 임대인 여부 |

**중요 참고사항:**
- 이 API는 `cluster/clusterList` API에서 `count > 1`인 클러스터를 발견했을 때, 해당 클러스터 내부의 모든 개별 매물 정보를 가져오기 위해 사용됩니다.
- 클러스터의 `lgeo` 값을 `itemId`와 `lgeo` 파라미터에 모두 전달하면 됩니다.
- **이 API는 매물 정보(`body` 배열)만 반환하며, 단지 정보(COMPLEX 배열)는 포함하지 않습니다.**
- 클러스터 내부의 단지 정보를 얻으려면 클러스터 중심 좌표로 작은 영역을 설정하고 높은 줌 레벨로 `cluster/clusterList` API를 재호출해야 합니다.

## 사용 방법

### 1. 전체 지역 스크래핑 전략

특정 지역의 모든 매물을 스크래핑하려면 다음 단계를 따르세요:

1. **지역 범위 설정**: 지도의 경계 좌표(`btm`, `lft`, `top`, `rgt`)를 설정하여 조회할 영역을 지정합니다.

2. **API 호출**: `cluster/clusterList` API를 호출하여 해당 영역의 매물 클러스터 정보를 가져옵니다.

3. **개별 매물 추출**: 
   - `ARTICLE` 배열에서 `count`가 1인 항목은 개별 매물 정보가 포함되어 있습니다.
   - `count`가 1보다 큰 경우, `cluster/ajax/articleList` API를 호출하여 해당 클러스터 내부의 모든 개별 매물 정보를 가져옵니다.
   - 클러스터의 `lgeo` 값을 `itemId`와 `lgeo` 파라미터로 전달합니다.

4. **영역 분할**: 넓은 지역의 경우, 영역을 작은 단위로 나누어 여러 번 API를 호출해야 합니다.

### 2. 파라미터 설명

#### 부동산 유형 코드 (rletTpCd)
- `APT`: 아파트
- `APT:JGC`: 아파트, 재건축
- `OPST`: 오피스텔
- `VL`: 빌라
- `ABYG`: 아파트 분양권
- 기타

#### 거래 유형 코드 (tradTpCd)
- `A1`: 매매
- `B1`: 전세
- `B2`: 월세

#### 줌 레벨 (z)
- 숫자가 클수록 더 상세한 지도
- 일반적으로 15~18 사이의 값을 사용

### 3. Python 스크래핑 예시 코드

```python
import requests
from typing import List, Dict
import time

def get_property_clusters(
    lat: float,
    lon: float,
    zoom: int,
    btm: float,
    lft: float,
    top: float,
    rgt: float,
    rlet_tp_cd: str = "APT:JGC",
    trad_tp_cd: str = "A1"
) -> Dict:
    """
    네이버 부동산 클러스터 정보 조회
    
    Args:
        lat: 중심 위도
        lon: 중심 경도
        zoom: 줌 레벨
        btm: 하단 경계 위도
        lft: 왼쪽 경계 경도
        top: 상단 경계 위도
        rgt: 오른쪽 경계 경도
        rlet_tp_cd: 부동산 유형 코드
        trad_tp_cd: 거래 유형 코드
    
    Returns:
        API 응답 데이터
    """
    url = "https://m.land.naver.com/cluster/clusterList"
    
    params = {
        "view": "atcl",
        "rletTpCd": rlet_tp_cd,
        "tradTpCd": trad_tp_cd,
        "z": zoom,
        "lat": lat,
        "lon": lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
        "pCortarNo": "",
        "addon": "COMPLEX",
        "isOnlyIsale": "false"
    }
    
    headers = {
        "Accept": "application/json",
        "Referer": "https://m.land.naver.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    
    return response.json()

def get_cluster_articles(
    item_id: str,
    lgeo: str,
    lat: float,
    lon: float,
    zoom: int,
    btm: float,
    lft: float,
    top: float,
    rgt: float,
    rlet_tp_cd: str = "APT",
    trad_tp_cd: str = "A1"
) -> Dict:
    """
    클러스터 내부의 개별 매물 목록 조회
    
    Args:
        item_id: 클러스터의 itemId (lgeo와 동일)
        lgeo: 지역 지오코드
        lat: 중심 위도
        lon: 중심 경도
        zoom: 줌 레벨
        btm: 하단 경계 위도
        lft: 왼쪽 경계 경도
        top: 상단 경계 위도
        rgt: 오른쪽 경계 경도
        rlet_tp_cd: 부동산 유형 코드
        trad_tp_cd: 거래 유형 코드
    
    Returns:
        API 응답 데이터
    """
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    
    params = {
        "itemId": item_id,
        "mapKey": "",
        "lgeo": lgeo,
        "rletTpCd": rlet_tp_cd,
        "tradTpCd": trad_tp_cd,
        "z": zoom,
        "lat": lat,
        "lon": lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
        "cortarNo": "",
        "showR0": ""
    }
    
    headers = {
        "Accept": "application/json",
        "Referer": "https://m.land.naver.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    
    return response.json()

def extract_individual_properties(data: Dict) -> List[Dict]:
    """
    응답 데이터에서 개별 매물 정보 추출 (count == 1인 경우)
    
    Args:
        data: API 응답 데이터
    
    Returns:
        개별 매물 정보 리스트
    """
    articles = data.get("data", {}).get("ARTICLE", [])
    individual_properties = []
    
    for article in articles:
        if article.get("count") == 1 and "itemId" in article:
            individual_properties.append({
                "itemId": article["itemId"],
                "lat": article["lat"],
                "lon": article["lon"],
                "price": article.get("prc"),
                "priceDisplay": article.get("priceTtl"),
                "propertyType": article.get("rletNm"),
                "tradeType": article.get("tradNm"),
                "tradeTypeCode": article.get("tradTpCd")
            })
    
    return individual_properties

def extract_clusters(data: Dict) -> List[Dict]:
    """
    응답 데이터에서 클러스터 정보 추출 (count > 1인 경우)
    
    Args:
        data: API 응답 데이터
    
    Returns:
        클러스터 정보 리스트
    """
    articles = data.get("data", {}).get("ARTICLE", [])
    clusters = []
    
    for article in articles:
        count = article.get("count", 0)
        if count > 1:
            clusters.append({
                "lgeo": article.get("lgeo"),
                "itemId": article.get("lgeo"),  # lgeo와 itemId는 동일
                "count": count,
                "lat": article.get("lat"),
                "lon": article.get("lon")
            })
    
    return clusters

# 사용 예시
if __name__ == "__main__":
    import time
    
    # 성남시 수정구 신흥동 예시
    result = get_property_clusters(
        lat=37.4514469,
        lon=127.1504679,
        zoom=17,
        btm=37.4462086,
        lft=127.1437516,
        top=37.4566848,
        rgt=127.1571842
    )
    
    # 개별 매물 추출 (count == 1)
    properties = extract_individual_properties(result)
    print(f"개별 매물 개수: {len(properties)}")
    for prop in properties:
        print(f"매물 ID: {prop['itemId']}, 가격: {prop['priceDisplay']}")
    
    # 클러스터 추출 (count > 1)
    clusters = extract_clusters(result)
    print(f"\n클러스터 개수: {len(clusters)}")
    
    # 각 클러스터의 개별 매물 수집
    all_cluster_properties = []
    for cluster in clusters:
        print(f"\n클러스터 {cluster['lgeo']} 처리 중... (매물 {cluster['count']}개)")
        cluster_result = get_cluster_articles(
            item_id=cluster["itemId"],
            lgeo=cluster["lgeo"],
            lat=37.4514469,
            lon=127.1504679,
            zoom=17,
            btm=37.4462086,
            lft=127.1437516,
            top=37.4566848,
            rgt=127.1571842
        )
        
        # 클러스터 내부 매물 정보 추출
        cluster_properties = cluster_result.get("body", [])
        all_cluster_properties.extend(cluster_properties)
        
        print(f"  수집된 매물: {len(cluster_properties)}개")
        time.sleep(0.5)  # API 호출 간 딜레이
    
    print(f"\n총 수집된 매물: {len(properties) + len(all_cluster_properties)}개")
```

## 주의사항

1. **API 접근 제한**: 과도한 요청은 IP 차단을 유발할 수 있으므로 적절한 딜레이를 두고 요청하세요.

2. **인증**: 현재 확인된 API는 별도의 인증이 필요하지 않지만, Referer 헤더가 필요할 수 있습니다.

3. **데이터 완전성**: `count`가 1보다 큰 클러스터의 경우, `cluster/ajax/articleList` API를 호출하여 개별 매물 정보를 얻을 수 있습니다. 이 API는 클러스터 내부의 모든 개별 매물 상세 정보를 제공합니다.

4. **법적 고지**: 이 API는 네이버의 공식 API가 아닐 수 있으며, 웹사이트 구조 변경에 따라 동작하지 않을 수 있습니다. 스크래핑 시 관련 법규를 준수하세요.

## 클러스터 처리 전략

### 클러스터 발견 및 확장 수집 (3단계 통합 전략)

클러스터 내부에는 개별 매물뿐만 아니라 단지 정보도 포함될 수 있습니다. 완전한 데이터 수집을 위해 다음 3단계 전략을 사용합니다:

1. **1단계: 기본 영역 수집 (Maximal 단지 및 클러스터 조회)**
   - `cluster/clusterList` API를 사용하여 넓은 영역을 그리드로 분할하여 수집
   - `addon=COMPLEX` 파라미터를 사용하여 단지 정보(COMPLEX 배열)도 함께 수집
   - `count == 1`인 개별 매물은 바로 수집
   - `count > 1`인 클러스터는 위치(`lat`, `lon`), `lgeo`, `count` 정보를 기록
   - 각 영역에서 발견된 모든 단지 정보(COMPLEX)를 수집하여 중복 제거

2. **2단계: 클러스터 내부 숨겨진 단지 및 매물 수집**
   - 1단계에서 발견된 각 클러스터에 대해 다음 두 가지 작업을 수행:
     
     **2-1. 클러스터 내부 단지 정보 수집**
     - **방법 A: 클러스터 클릭 시 자동 호출되는 API 활용 (권장)**
       - 클러스터를 클릭하면 네이버는 자동으로 `cluster/clusterList` API를 호출합니다
       - 이 API 호출에는 `pCortarNo`와 `bAddon=COMPLEX` 파라미터가 포함됩니다
       - 응답에 `COMPLEX` 배열이 포함되어 클러스터 내부의 단지 정보를 제공합니다
       - 이 방법은 클러스터의 `lgeo`를 사용하여 클러스터 중심 영역의 단지 정보를 효율적으로 가져올 수 있습니다
     
     - **방법 B: 줌인 방식 (대안)**
       - 클러스터 중심 좌표(`lat`, `lon`)를 사용
       - 더 높은 줌 레벨(19-20)로 작은 영역을 설정하여 `cluster/clusterList` API를 재호출
       - `addon=COMPLEX`를 사용하여 클러스터 내부의 숨겨진 단지 정보(COMPLEX 배열) 수집
       - 새로 발견된 단지 정보를 기존 단지 목록에 추가 (중복 제거)
     
     - **왜 두 가지 방법이 필요한가?**
       - `cluster/ajax/articleList` API는 매물 정보(`body` 배열)만 반환하고 단지 정보(`COMPLEX` 배열)는 제공하지 않습니다
       - 단지 정보를 얻으려면 `cluster/clusterList` API를 사용해야 합니다
       - 클러스터 클릭 시 자동 호출되는 `cluster/clusterList` API는 `pCortarNo`와 `bAddon=COMPLEX` 파라미터를 포함하여 단지 정보를 함께 제공합니다
     
     **2-2. 클러스터 내부 개별 매물 수집**
     - 클러스터의 `lgeo` 값을 사용하여 `cluster/ajax/articleList` API 호출
     - 클러스터 내부의 모든 개별 매물 정보 수집
     - 각 매물의 `atclNm`(단지명) 필드를 활용하여 단지 매칭 개선
     - **참고**: 이 API는 매물 정보(`body` 배열)만 제공하므로, 단지 정보는 2-1 단계에서 수집한 데이터를 사용합니다.

3. **3단계: 데이터 통합 및 매칭**
   - 1단계와 2단계에서 수집한 단지 정보를 통합
   - 1단계와 2단계에서 수집한 매물 정보를 통합
   - 매물과 단지 정보를 매칭 (lgeo, 좌표 기반)
   - 최종 데이터 정제 및 중복 제거

### 전략의 핵심 포인트

- **Maximal 수집**: 1단계에서 가능한 한 많은 단지와 클러스터 정보를 수집
- **숨겨진 데이터 발견**: 클러스터 내부에 숨겨진 단지 정보를 높은 줌 레벨로 재수집하여 발견
- **데이터 통합**: 여러 단계에서 수집한 데이터를 결합하여 완전한 데이터셋 구성

### 효율적인 수집을 위한 팁

- 클러스터가 많은 경우, 클러스터 크기(`count`)에 따라 우선순위를 정할 수 있습니다
- **클러스터 클릭 시 자동 호출되는 `cluster/clusterList` API 활용**: 클러스터를 클릭하면 네이버는 자동으로 `cluster/clusterList` API를 `pCortarNo`와 `bAddon=COMPLEX` 파라미터와 함께 호출합니다. 이 응답에는 해당 클러스터 영역의 단지 정보(COMPLEX 배열)가 포함되어 있어, 줌인 방식보다 더 효율적으로 단지 정보를 수집할 수 있습니다.
- 클러스터 내부 단지 수집 시 줌 레벨 19-20을 사용하면 더 상세한 정보를 얻을 수 있습니다 (줌인 방식 사용 시)
- `cluster/ajax/articleList` API는 매물 정보만 제공하므로, 단지 정보는 `cluster/clusterList` API를 사용해야 합니다
- 클러스터 클릭 시 호출되는 `cluster/clusterList` API는 클러스터 영역에 해당하는 단지 정보를 자동으로 필터링하여 제공하므로, 전체 영역을 스캔하는 것보다 효율적입니다

## 추가 조사 필요 사항

1. **개별 매물 상세 정보 API**: `atclNo`를 사용하여 개별 매물의 더 상세한 정보(면적, 층수, 건축년도 등)를 가져오는 API가 별도로 존재할 수 있습니다.

2. **페이지네이션**: `cluster/ajax/articleList` API의 응답에 `more` 필드가 있어, 대량의 매물이 있는 경우 페이지네이션이 필요할 수 있습니다.

