from clickhouse_util import clickclient,clickclient_file
import config as cf
import traceback
from py2java import *
import os

globalConf = cf.pparms("./pathconfig.yaml").param

### 保存站点数据到文件
def save_station_to_file():
    sql = f"""
            SELECT station_id, station_code, longitude, latitude FROM station_info
            """
    return save_to_file(sql)

### 保存区域数据到文件
def save_area_to_file():
    sql = f"""
        SELECT id, region_name, region_code, left_top_lon, left_top_lat, right_bottom_lon, right_bottom_lat FROM szybjydb.sys_region_config
        """
    return save_to_file(sql)

### 保存插值或检验数据到数据库
def save_data_to_ck():
    root_path = globalConf.clickTofile
    for file in os.listdir(root_path):
        if file.endswith(".OK") and file.startswith("HPC_insert_df_"):
            original_file = file[:-3]  # 从末尾截取掉最后3个字符（即.OK）
            original_file_path = os.path.join(root_path, original_file)
            ##加异常处理
            try:
                clickclient_file.insert_df_from_HPC_MET(original_file_path,clickclient)
            except Exception as e:
                print(f"插入文件{file}失败")
                traceback.print_exc()
    return True,""

def save_to_file(sql):
    status = True
    mess = ""
    try:
        obs = clickclient.query_df(sql)
        clickclient_file.insert_df(sql,obs)
    except Exception as e:
        status = False
        mess = str(e)
    return status,mess

def save_surface_real_data_to_file(obsdate):
    VAR = ['2t', '2d', '10u', '10v', 'sp', 'mslp', 'vis', 'tcc', 'lcc', 'ch', 'rad', 'wind', 'wdir'] 
    ppp = ",".join([pyweb2java(var) for var in VAR])
    sql = f"""
        SELECT {ppp}, station_code, longitude, latitude, message_type FROM surface_observation_data 
        WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
        """
    return save_to_file(sql)

def save_upper_real_data_to_file(obsdate):
    VAR = ['t', 'gh', 'r', 'wind', 'wdir'] 
    ppp = ",".join([pyweb2java(var) for var in VAR])
    sql = f"""
        SELECT {ppp}, station_code, longitude, latitude FROM upper_observation_data 
        WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
        """
    return save_to_file(sql)

