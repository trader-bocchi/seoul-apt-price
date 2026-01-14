import requests

cookies = {
    'NNB': 'VNIW2RPMX74WG',
    'ASID': '3ae38d8100000186f49a6a7100000050',
    'NAC': 'KmByBMQI1kvu',
    'nid_inf': '1475415340',
    'NID_AUT': 'GDmCIxCj4h4jXADjiqWFf1EEcg2/j8RKjbzGFVtPv9rNkMwXde3hEo5/TK6e1vfa',
    'bnb_tooltip_shown_finance_v1': 'true',
    'nhn.realestate.article.rlet_type_cd': 'A01',
    'nhn.realestate.article.trade_type_cd': '""',
    'nhn.realestate.article.ipaddress_city': '5000000000',
    '_fwb': '205RmOZVkCytawGqNaWIXcs.1767181684207',
    'landHomeFlashUseYn': 'Y',
    '_fwb': '205RmOZVkCytawGqNaWIXcs.1767181684207',
    'NACT': '1',
    'SRT30': '1767341174',
    'realestate.beta.lastclick.cortar': '4100000000',
    'page_uid': 'jSP5AsqX5mhsshVX1IV-462947',
    'NID_SES': 'AAABtGC3DHzidYZSUC1n8look2k+h4LUj9LE0sPPD1zLVXx+qF9rbhfJUSuE34OKXApNziLzdxjy/0XYpxZ/6zqIlaHSNhwwUAqdaRSVVM50d6EiZnpueTFTAhKy22bS4WAVa1SoRJm1iSNg/AkxPSHuOQK96odpjcCvtI0EUzQ7tI0mseghrcV3dK+x2dgeQvoz6pEixAZ3tbZxe0cKo2FY7aab/ZbzO6E4yHZICS7ErPv1iwfAEfdlENpf7Yu8X+L80dhZUPpZ87Qs/NShNbJnoc1G3CluQFZCC8QSxVqR/y34qmhNZ1A9m9WKNVL3yCyMd9Yge1hmnMEP5LBhiNjTN/FbPR0eHrSjRTvMALT0ifchKq7/87m20FXAy+diQoFoQSK0YD9KpKm5bWm4+aw1EOIwDdmnpkQsvZuZfDolLFr/zfBQJ6I3QPZ2nhCkOonMXvMJcse3JwntSRFofBH1Woh6QoDNDUw9v+hnZItw56Wo/2eLbXCZNxQt2Q7L54cQcFDR6fHUhRvq99LJltn+65omw3prq2BzRrgw2gKaXTV0+qoZ+uUc7NCQqg8nrqq+HF3J133Lixod3gH4T7BIjIw=',
    'REALESTATE': 'Fri%20Jan%2002%202026%2018%3A02%3A05%20GMT%2B0900%20(Korean%20Standard%20Time)',
    'PROP_TEST_KEY': '1767344525684.46536a44b286369316c1b8ea8327c8962dbc81254d2ece1566ed8293d347c3a3',
    'PROP_TEST_ID': 'cf6f77b8a5e6e86f54e375566fe6a68fd2935c031afc51a6f40b7bf00bcb4c3f',
    'SRT5': '1767344850',
    'BUC': 'e3DfNAjM6-PSIbEu-24EESSP8uIjXQmGgyBaTR3rFyk=',
}

headers = {
    'accept': '*/*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NjczNDQ1MjUsImV4cCI6MTc2NzM1NTMyNX0.W_P7qskrQE7FCACix1-714szRmH22JOgaFQIlLIk69k',
    'priority': 'u=1, i',
    'referer': 'https://new.land.naver.com/complexes/118771?ms=37.4551211,127.1502506,17&a=APT:PRE:ABYG:JGC&e=RETAIL',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    # 'cookie': 'NNB=VNIW2RPMX74WG; ASID=3ae38d8100000186f49a6a7100000050; NAC=KmByBMQI1kvu; nid_inf=1475415340; NID_AUT=GDmCIxCj4h4jXADjiqWFf1EEcg2/j8RKjbzGFVtPv9rNkMwXde3hEo5/TK6e1vfa; bnb_tooltip_shown_finance_v1=true; nhn.realestate.article.rlet_type_cd=A01; nhn.realestate.article.trade_type_cd=""; nhn.realestate.article.ipaddress_city=5000000000; _fwb=205RmOZVkCytawGqNaWIXcs.1767181684207; landHomeFlashUseYn=Y; _fwb=205RmOZVkCytawGqNaWIXcs.1767181684207; NACT=1; SRT30=1767341174; realestate.beta.lastclick.cortar=4100000000; page_uid=jSP5AsqX5mhsshVX1IV-462947; NID_SES=AAABtGC3DHzidYZSUC1n8look2k+h4LUj9LE0sPPD1zLVXx+qF9rbhfJUSuE34OKXApNziLzdxjy/0XYpxZ/6zqIlaHSNhwwUAqdaRSVVM50d6EiZnpueTFTAhKy22bS4WAVa1SoRJm1iSNg/AkxPSHuOQK96odpjcCvtI0EUzQ7tI0mseghrcV3dK+x2dgeQvoz6pEixAZ3tbZxe0cKo2FY7aab/ZbzO6E4yHZICS7ErPv1iwfAEfdlENpf7Yu8X+L80dhZUPpZ87Qs/NShNbJnoc1G3CluQFZCC8QSxVqR/y34qmhNZ1A9m9WKNVL3yCyMd9Yge1hmnMEP5LBhiNjTN/FbPR0eHrSjRTvMALT0ifchKq7/87m20FXAy+diQoFoQSK0YD9KpKm5bWm4+aw1EOIwDdmnpkQsvZuZfDolLFr/zfBQJ6I3QPZ2nhCkOonMXvMJcse3JwntSRFofBH1Woh6QoDNDUw9v+hnZItw56Wo/2eLbXCZNxQt2Q7L54cQcFDR6fHUhRvq99LJltn+65omw3prq2BzRrgw2gKaXTV0+qoZ+uUc7NCQqg8nrqq+HF3J133Lixod3gH4T7BIjIw=; REALESTATE=Fri%20Jan%2002%202026%2018%3A02%3A05%20GMT%2B0900%20(Korean%20Standard%20Time); PROP_TEST_KEY=1767344525684.46536a44b286369316c1b8ea8327c8962dbc81254d2ece1566ed8293d347c3a3; PROP_TEST_ID=cf6f77b8a5e6e86f54e375566fe6a68fd2935c031afc51a6f40b7bf00bcb4c3f; SRT5=1767344850; BUC=e3DfNAjM6-PSIbEu-24EESSP8uIjXQmGgyBaTR3rFyk=',
}

response = requests.get(
    'https://new.land.naver.com/api/articles/complex/118771?realEstateType=APT%3APRE%3AABYG%3AJGC&tradeType=&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears&recentlyBuildYears&minHouseHoldCount&maxHouseHoldCount&showArticle=false&sameAddressGroup=false&minMaintenanceCost&maxMaintenanceCost&priceType=RETAIL&directions=&page=1&complexNo=118771&buildingNos=&areaNos=&type=list&order=rank',
    cookies=cookies,
    headers=headers,
)

print(response.json())