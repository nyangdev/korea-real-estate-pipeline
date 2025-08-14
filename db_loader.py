import pandas as pd
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

db_configration = {
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT")),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'db': os.getenv("DB_NAME"),
    'charset': os.getenv("DB_CHARSET"),
    'cursorclass': pymysql.cursors.DictCursor
}

def load_csv_to_db(csv_file_path, db_config, table_name='real_estate_trade', delay_seconds=0.05) :
    
    if not os.path.exists(csv_file_path):
        print(f"오류: 지정된 CSV 파일 '{csv_file_path}'을 찾을 수 없습니다.")
        return
    
    try:
        print(f"CSV 파일 '{csv_file_path}'에서 데이터 읽어오는 중...")
        df = pd.read_csv(csv_file_path)

        db_columns = [
            'deal_year', 'deal_month', 'deal_day', 'sgg_cd', 'apt_nm', 'jibun',
            'apt_dong', 'exclu_use_ar', 'floor', 'deal_amount', 'build_year',
            'cdeal_type', 'cdeal_day', 'dealing_gbn', 'estate_agent_sgg_nm',
            'rgst_date', 'sler_gbn', 'buyer_gbn', 'land_leasehold_gbn'
        ]
        df = df.reindex(columns=db_columns)
        # Pandas의 NaN 값을 DB의 NULL로 인식되도록 None으로 변경합니다.
        df = df.where(pd.notnull(df), None)
        
    except Exception as e:
        print(f"CSV 파일을 읽는 도중 오류가 발생했습니다: {e}")

    # 2차 검증
    # 기본키로 쓰이는 필수값이 모두 존재하는 데이터가 넘어오는건지 확인 작업
    required_cols = ['deal_year', 'deal_month', 'deal_day', 'sgg_cd', 'apt_nm', 'jibun', 'apt_dong', 'exclu_use_ar', 'floor', 'deal_amount']
    if not all(col in df.columns for col in required_cols):
        print(f"CSV 데이터에 필요한 컬럼 ({required_cols})가 부족합니다. 저장을 취소합니다")
        return
    
    print("MariaDB에 연결 중....")
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor()
    print("MariaDB 연결 성공!")
    sql = """
    INSERT INTO real_estate_trade (
    deal_year, deal_month, deal_day, sgg_cd, apt_nm, jibun, apt_dong, 
    exclu_use_ar, floor, deal_amount, build_year, cdeal_type, cdeal_day, 
    dealing_gbn, estate_agent_sgg_nm, rgst_date, sler_gbn, buyer_gbn, 
    land_leasehold_gbn)
    VALUES (
    %s, %s, %s, %s, %s, %s, %s, 
    %s, %s, %s, %s, %s, %s, 
    %s, %s, %s, %s, %s, 
    %s)
    ON DUPLICATE KEY UPDATE
    build_year = VALUES(build_year),
    cdeal_type = VALUES(cdeal_type),
    cdeal_day = VALUES(cdeal_day),
    dealing_gbn = VALUES(dealing_gbn),
    estate_agent_sgg_nm = VALUES(estate_agent_sgg_nm),
    rgst_date = VALUES(rgst_date),
    sler_gbn = VALUES(sler_gbn),
    buyer_gbn = VALUES(buyer_gbn),
    land_leasehold_gbn = VALUES(land_leasehold_gbn)
    """
    print(f"데이터를 '{table_name}' 테이블에 저장 시작 (각 {delay_seconds}초 대기)")
    inserted_rows = 0
    updated_rows = 0
    for _, row in df.iterrows():
        try:
            result = cursor.execute(sql, tuple(row))
            if result == 1:
                inserted_rows += 1
            elif result == 2:
                updated_rows +=1
        except Exception as e:
            print(f"데이터 삽입 중 오류 발생: {e}")
        except pymysql.err.IntegrityError as e:
            if e.args[0] == 1062:
                print("기본키가 겹칩니다. 기존 레코드가 업데이트 됩니다.")
    
    connection.commit()
    cursor.close()
    connection.close()
    
    print(f"\n총 {len(df)}건 처리 완료.")
    print(f"새로 추가된 데이터: {inserted_rows}건")
    print(f"업데이트된 데이터: {updated_rows}건")
    print(f"중복으로 인해 변경되지 않은 데이터: {len(df) - inserted_rows - updated_rows}건")


# --- 테스트용 코드 ---
if __name__ == '__main__':
    print("---CSV 파일에서 데이터 로드하여 DB에 저장하기---")

    default_csv_filename = "data/real_estate_202407_11110.csv"
    csv_file_path = input(f"저장할 CSV 파일의 경로를 입력하세요 (예시: data/real_estate_202407_11110.csv) 입력하지않으시면 해당 파일명이 기본값으로 입력됩니다.\n")

    if not csv_file_path:
        csv_file_path = default_csv_filename

    load_csv_to_db(csv_file_path, db_configration, table_name='real_estate_trade', delay_seconds=0.05)