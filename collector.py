from dotenv import load_dotenv
import os
import requests
import pandas as pd
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import certifi

# 통신 오류 해결
class Tls12Adapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

    # 프록시 환경을 위한 메서드 추가
    def proxy_manager_for(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().proxy_manager_for(*args, **kwargs)

# 인증키 설정
load_dotenv()
SERVICE_KEY = os.getenv("SERVICE_KEY")

if not SERVICE_KEY:
    # 의도적으로 에러 발생시켜서 중지
    raise ValueError("환경 변수에서 해당하는 값을 찾을 수 없습니다.")


API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

def collect_real_estate_data(year_month, region_code):
    print(f"------{year_month} {region_code} 데이터 수집 시작------")

# 요청 메시지 명세
    params = {
        'serviceKey' : SERVICE_KEY,
        'LAWD_CD' : region_code,
        'DEAL_YMD' : year_month,
        'numOfRows' : 1000
    }

    session = requests.Session()
    session.mount("https://", Tls12Adapter())

    try:
        print("보안 프로토콜(TLSv1.2, SECLEVEL=1)을 강제하여 API를 호출합니다.")
        response = session.get(API_URL, params=params, timeout=15, verify=certifi.where())
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
        return
    
    try:
        df = pd.read_xml(response.content, xpath=".//item")

        if df.empty:
            print("수집된 데이터가 없습니다")
            return
        
    except:
        print("XML 변환 중 오류 발생")
        return
    
    # 지번, 전용면적, 층, 아파트 동명은 필수값 아니므로 존재하지않을시에 기본값으로 채워줘야함
    # 기본값 세팅
    optional_cols = {
        'jibun' : '0',
        'excluUseAr' : 0.0,
        'floor' : 0,
        'aptDong' : '0'
    }

    for col, default_value in optional_cols.items():
        # df 컬럼에 non 필수값 존재하지않으면
        if col not in df.columns:
            df[col] = default_value

        # 컬럼은 존재시
        else:
            if pd.api.types.is_numeric_dtype(default_value):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default_value)
            
            else:
                df[col].fillna(default_value, inplace=True)
                # 문자열 공백 제거
                df[col] = df[col].astype(str).str.strip()
                df.loc[df[col] == '', col] = default_value

    
    df['dealAmount'] = df['dealAmount'].astype(str).str.replace(',', '').astype(int)

    # 나머지 값들 db에 맞게 한번 더 정제
    int_cols = ['dealYear', 'dealMonth', 'dealDay', 'buildYear']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    str_cols = ['sggCd', 'umdNm', 'aptNm', 'cdealType', 'cdealDay', 'dealingGbn', 'estateAgentSggNm', 'rgstDate', 'slerGbn', 'buyerGbn', 'landLeaseholdGbn']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)

    # db 컬럼명에 맞게 변환
    df.rename(columns={
        'dealYear': 'deal_year',
        'dealMonth': 'deal_month',
        'dealDay': 'deal_day',
        'sggCd': 'sgg_cd',
        'umdNm': 'umd_nm',
        'aptNm': 'apt_nm',
        'jibun': 'jibun',
        'aptDong': 'apt_dong',
        'excluUseAr': 'exclu_use_ar',
        'floor': 'floor',
        'dealAmount': 'deal_amount',
        'buildYear': 'build_year',
        'cdealType': 'cdeal_type',
        'cdealDay': 'cdeal_day',
        'dealingGbn': 'dealing_gbn',
        'estateAgentSggNm': 'estate_agent_sgg_nm',
        'rgstDate': 'rgst_date',
        'slerGbn': 'sler_gbn',
        'buyerGbn': 'buyer_gbn',
        'landLeaseholdGbn': 'land_leasehold_gbn'
    }, inplace=True)

    # csv 파일로 저장
    if not os.path.exists('data'):
        os.makedirs('data')
        
    file_path = f"data/real_estate_{year_month}_{region_code}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"데이터가 '{file_path}' 경로에 성공적으로 저장되었습니다. (총 {len(df)}건)")

# main 호출 함수
if __name__ == "__main__":
    print("부동산 실거래가 데이터 수집 도구")

    default_year_month = "202407"
    default_region_code = "11110"

    input_year_month = input(f"조회할 계약년월을 입력하세요 YYYYMM 형식, 기본값 {default_year_month}\n")
    input_region_code = input(f"조회할 지역 코드를 입력하세요 행정표준코드관리시스템의 법정동코드 10자리 중 앞 5자리 입력, 기본값 {default_region_code}\n")

    if not input_year_month:
        input_year_month = default_year_month

    if not input_region_code:
        input_region_code = default_region_code
        
    print(f"\n>> {input_year_month} 기간의 {input_region_code} 지역 데이터 수집을 시작합니다.")

    collect_real_estate_data(input_year_month, input_region_code)