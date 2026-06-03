import pandas as pd 
import sys 
import argparse
import datetime
import numpy as np
from clickhouse_util import clickclient
parser = argparse.ArgumentParser()
parser.add_argument("--filename","-f",nargs="+",help="filename")
parser.add_argument("--ID","-i",help="station id")

args = parser.parse_args()
filel = args.filename
result = pd.DataFrame()

for filen in filel:
    data = pd.read_csv(filen,sep="\t")
    select = data[data["Station_Id_C"]==int(args.ID)]
    result = pd.concat([result,select],ignore_index=True)

indata = result[["Station_Id_C","Lat", "Lon",  "Alti",  "Year",  "Mon" , "Day","Hour", "SRA_Max"]]
objtime = []
for i,tmp in indata.iterrows():
    objtime.append(datetime.datetime(int(tmp["Year"]),int(tmp["Mon"]),int(tmp["Day"]),int(tmp["Hour"]),0,0)- datetime.timedelta(hours=16))
fill_value = np.ones_like(objtime)*-999
n_row = len(fill_value)
df = pd.DataFrame({
        'station_code': indata["Station_Id_C"].astype(str),
        'observation_time': objtime, #北京转UTC
        'observation_timestamp':objtime,
        'temperature': fill_value,
        'dew_point_temperature': fill_value,
        'humidity': fill_value,
        'wind_direction': fill_value,
        'wind_speed': fill_value,
        'visibility': fill_value,  # 提前用向量处理visibility_code_convert
        'total_cloud_cover': fill_value,
        'low_cloud_cover': fill_value,
        'cloud_height': fill_value,
        'sea_level_pressure': fill_value,


            # 处理固定值字段（关键修改）
        'radiation': indata["SRA_Max"].astype(str),  # 生成长度为n_rows、值全为-999的数组
        'precipitation': fill_value,
        'pressure': fill_value,
        'station_type': np.full(n_row, 'gts', dtype=object),  # 生成长度为n_rows、值全为'mh'的字符串数组


           # 其他字段...


       })
try:
    # 从ClickHouse查询映射关系
    station_info_sql = "SELECT station_code, station_id, station_name,longitude,latitude FROM station_info"
    station_info_df = clickclient.query_df(station_info_sql)
except Exception as e:
    print( False, f"读取映射表失败：{str(e)}")
df = df.merge(
    station_info_df[['station_code', 'station_id', 'station_name', 'longitude','latitude']],  # 只取需要的字段
    on='station_code',  # 关联键：站号
    how='inner'
)
print(df)
try:
 # 将 DataFrame 插入 ClickHouse
    insert_result = clickclient.insert_df(
     table='airport_observation_data',
     df=df
     )
    #print(f"批量插入成功")

except Exception as e:
    print(f"插入失败: {e}")
finally:
    clickclient.close()
#print(data[data["Station_Id_C"]==str(args.ID)])
