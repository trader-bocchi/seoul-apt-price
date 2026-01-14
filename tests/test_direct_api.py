"""
직접 API 테스트 - 사용자가 제공한 URL 요건대로
"""
from src.collectors.api_client import NaverLandApiClient, ApiConfig

def test_direct_api():
    """사용자가 제공한 URL 요건대로 직접 테스트"""
    print("=" * 60)
    print("직접 API 테스트 (사용자 제공 URL 요건)")
    print("=" * 60)
    
    # 사용자가 제공한 URL의 파라미터
    # https://m.land.naver.com/cluster/ajax/articleList?rletTpCd=APT&tradTpCd=A1&z=14&lat=37.4473&lon=127.1493&btm=37.4056195&lft=127.0763439&top=37.4889573&rgt=127.2222561&showR0=&totCnt=209&cortarNo=4113110100
    
    cortar_no = "4113110100"  # 성남시 수정구 신흥동
    lat = 37.4473
    lon = 127.1493
    zoom = 14
    btm = 37.4056195
    lft = 127.0763439
    top = 37.4889573
    rgt = 127.2222561
    rlet_tp_cd = "APT"
    trad_tp_cd = "A1"
    tot_cnt = 209
    
    print(f"\n파라미터:")
    print(f"  cortarNo: {cortar_no}")
    print(f"  lat: {lat}, lon: {lon}")
    print(f"  zoom: {zoom}")
    print(f"  btm: {btm}, lft: {lft}, top: {top}, rgt: {rgt}")
    print(f"  rletTpCd: {rlet_tp_cd}, tradTpCd: {trad_tp_cd}")
    print(f"  totCnt: {tot_cnt}")
    
    api_config = ApiConfig(min_delay=0.5, timeout=10, max_retries=3)
    api_client = NaverLandApiClient(api_config)
    
    print(f"\n첫 페이지 조회 중...")
    try:
        data = api_client.get_article_list_by_region(
            cortar_no=cortar_no,
            lat=lat,
            lon=lon,
            zoom=zoom,
            btm=btm,
            lft=lft,
            top=top,
            rgt=rgt,
            rlet_tp_cd=rlet_tp_cd,
            trad_tp_cd=trad_tp_cd,
            page=1,
            tot_cnt=tot_cnt
        )
        
        print(f"\n응답:")
        print(f"  code: {data.get('code')}")
        print(f"  more: {data.get('more')}")
        print(f"  page: {data.get('page')}")
        
        body = data.get("body", [])
        print(f"  매물 개수: {len(body)}")
        
        if body:
            print(f"\n첫 3개 매물:")
            for i, article in enumerate(body[:3], 1):
                print(f"  {i}. {article.get('atclNm')} - {article.get('hanPrc')} ({article.get('atclNo')})")
        
        # 페이지네이션 테스트
        if data.get("more") or len(body) >= 20:
            print(f"\n두 번째 페이지 조회 중...")
            data2 = api_client.get_article_list_by_region(
                cortar_no=cortar_no,
                lat=lat,
                lon=lon,
                zoom=zoom,
                btm=btm,
                lft=lft,
                top=top,
                rgt=rgt,
                rlet_tp_cd=rlet_tp_cd,
                trad_tp_cd=trad_tp_cd,
                page=2,
                tot_cnt=tot_cnt
            )
            
            body2 = data2.get("body", [])
            print(f"  두 번째 페이지 매물 개수: {len(body2)}")
            print(f"  more: {data2.get('more')}")
        
        print(f"\n✅ API 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ API 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_direct_api()

