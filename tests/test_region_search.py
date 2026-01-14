"""
지역 정보 조회 테스트 스크립트
"""
import sys
from src.collectors.api_client import NaverLandApiClient, ApiConfig
from src.collectors.region_collector import RegionCollector

def test_region_search(region_name: str):
    """지역 정보 조회 테스트"""
    print(f"=" * 60)
    print(f"지역 정보 조회 테스트: {region_name}")
    print(f"=" * 60)
    
    api_config = ApiConfig(min_delay=0.5, timeout=10, max_retries=3)
    collector = RegionCollector(api_config)
    
    # 직접 API 클라이언트 사용
    api_client = collector.api_client
    
    print("\n1. Geopy로 좌표 변환 시도...")
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="naver_land_crawler")
        location = geolocator.geocode(region_name, country_codes="kr", timeout=10)
        
        if location:
            print(f"   성공: lat={location.latitude}, lon={location.longitude}")
            lat, lon = location.latitude, location.longitude
        else:
            print("   실패: Geopy에서 좌표를 찾을 수 없음")
            lat, lon = 37.4201, 127.1266  # 성남시 기본 좌표
            print(f"   기본 좌표 사용: lat={lat}, lon={lon}")
    except Exception as e:
        print(f"   Geopy 오류: {str(e)}")
        lat, lon = 37.4201, 127.1266  # 성남시 기본 좌표
        print(f"   기본 좌표 사용: lat={lat}, lon={lon}")
    
    print(f"\n2. cluster/clusterList API 호출 시도...")
    print(f"   좌표: lat={lat}, lon={lon}")
    
    zoom = 13
    area_size = 0.05
    btm = lat - area_size
    lft = lon - area_size
    top = lat + area_size
    rgt = lon + area_size
    
    print(f"   영역: btm={btm}, lft={lft}, top={top}, rgt={rgt}")
    
    try:
        data = api_client.get_cluster_list(
            lat=lat,
            lon=lon,
            zoom=zoom,
            btm=btm,
            lft=lft,
            top=top,
            rgt=rgt,
            rlet_tp_cd="APT",
            trad_tp_cd="A1"
        )
        
        print(f"\n3. API 응답 확인...")
        print(f"   응답 코드: {data.get('code')}")
        
        if data.get("code") != "success":
            print(f"   오류: API 응답이 성공이 아님")
            print(f"   전체 응답: {data}")
            return
        
        cortar_info = data.get("data", {}).get("cortar", {})
        print(f"   cortar 정보 존재: {bool(cortar_info)}")
        
        if cortar_info:
            detail = cortar_info.get("detail", {})
            print(f"\n4. cortar 상세 정보:")
            print(f"   cortarNo: {detail.get('cortarNo')}")
            print(f"   cortarNm: {detail.get('cortarNm')}")
            print(f"   regionName: {detail.get('regionName')}")
            print(f"   mapXCrdn (lon): {detail.get('mapXCrdn')}")
            print(f"   mapYCrdn (lat): {detail.get('mapYCrdn')}")
            print(f"   cityNm: {detail.get('cityNm')}")
            print(f"   dvsnNm: {detail.get('dvsnNm')}")
            print(f"   secNm: {detail.get('secNm')}")
            
            if detail.get("cortarNo"):
                print(f"\n✅ 성공! cortarNo를 찾았습니다: {detail.get('cortarNo')}")
            else:
                print(f"\n❌ 실패: cortarNo가 없습니다")
        else:
            print(f"\n❌ 실패: cortar 정보가 응답에 없습니다")
            print(f"   data 키: {list(data.get('data', {}).keys())}")
            
    except Exception as e:
        print(f"\n❌ API 호출 오류: {str(e)}")
        import traceback
        traceback.print_exc()

def test_article_list_api(cortar_no: str, lat: float, lon: float):
    """articleList API 테스트"""
    print(f"\n" + "=" * 60)
    print(f"articleList API 테스트")
    print(f"=" * 60)
    print(f"cortarNo: {cortar_no}")
    print(f"좌표: lat={lat}, lon={lon}")
    
    api_config = ApiConfig(min_delay=0.5, timeout=10, max_retries=3)
    api_client = NaverLandApiClient(api_config)
    
    zoom = 14
    area_size = 0.01
    btm = lat - area_size
    lft = lon - area_size
    top = lat + area_size
    rgt = lon + area_size
    
    try:
        # 첫 페이지 조회
        data = api_client.get_article_list_by_region(
            cortar_no=cortar_no,
            lat=lat,
            lon=lon,
            zoom=zoom,
            btm=btm,
            lft=lft,
            top=top,
            rgt=rgt,
            rlet_tp_cd="APT",
            trad_tp_cd="A1",
            page=1
        )
        
        print(f"\n응답 코드: {data.get('code')}")
        print(f"more: {data.get('more')}")
        print(f"page: {data.get('page')}")
        
        body = data.get("body", [])
        print(f"매물 개수: {len(body)}")
        
        if body:
            print(f"\n첫 번째 매물 정보:")
            first = body[0]
            print(f"  atclNo: {first.get('atclNo')}")
            print(f"  atclNm: {first.get('atclNm')}")
            print(f"  prc: {first.get('prc')}")
            print(f"  hanPrc: {first.get('hanPrc')}")
        
        return data
        
    except Exception as e:
        print(f"\n❌ API 호출 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 테스트할 지역명
    region_name = "성남시 수정구 신흥동"
    
    if len(sys.argv) > 1:
        region_name = sys.argv[1]
    
    # 1. 지역 정보 조회 테스트
    test_region_search(region_name)
    
    # 2. 알려진 cortarNo로 직접 테스트
    print(f"\n" + "=" * 60)
    print(f"알려진 cortarNo로 직접 테스트")
    print(f"=" * 60)
    known_cortar_no = "4113110100"  # 성남시 수정구 신흥동
    known_lat = 37.4473
    known_lon = 127.1493
    
    test_article_list_api(known_cortar_no, known_lat, known_lon)

