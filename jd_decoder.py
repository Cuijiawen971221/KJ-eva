import numpy as np
from humidity_calc import hum  # 假设该模块已正确实现相对湿度计算

import re
from clickhouse_util import clickclient
import pandas as pd
from datetime import datetime, timedelta

#把2025010124这种改为2025010200
def parse_special_time(date_str):
    if date_str.endswith('24') == False:
        return date_str

    # 提取日期部分（前 8 位）
    date_part = date_str[:8]
    # 解析为日期
    date_obj = datetime.strptime(date_part, "%Y%m%d")
    # 加一天并设置时间为 00:00
    next_day = date_obj + timedelta(days=1)
    return next_day.strftime("%Y%m%d%H")




def visibility_code_convert(code):
    """
    将水平能见度编码转换为实际能见度值（千米）
    :param code: 能见度编码（数值类型）
    :return: 对应的能见度值（千米，数值类型），若编码无效则返回 None
    """
    # 特殊映射关系（输入为数值，输出为数值）
    special_mappings = {
        0: 0.09,   # 编码 0 对应 0.01 千米 意思是小于0.1
        89: 70.1,  # 编码 89 对应 70.1 千米  意思是大于等于70
        90: 0.049,  # 编码 90 对应 小于0.05 千米
        91: 0.05,
        92: 0.2,
        93: 0.5,
        94: 1,
        95: 2,
        96: 4,
        97: 10,
        98: 20,
        99: 50.1,   # 编码 99 对应 50.1 千米  意思是大于等于50
    }
    if code == -2 or code == -1:
        return -1
    # 处理特殊映射
    if code in special_mappings:
        return special_mappings[code]
    # 处理标准映射
    if code <= 50:
        return code / 10.0  # 编码 1-49 对应 0.1-4.9 千米
    elif code <= 80:
        return code - 50    # 编码 55-59 对应 6-10 千米
    elif code <= 88:
        return (code - 75) * 5  # 编码 80-88 对应 35-70 千米（间隔5）
    else:
        return -1         # 无效编码返回 None




def delete_jd_data(start_date_num):
    """
    删除指定日期范围内的 mh 类型数据
    :param start_date_num: 起始日期（数值型，如 20250501）
    """
    # 1. 转换参数为日期对象
    try:
        # 数值转字符串（确保8位）
        start_date_str = str(start_date_num).zfill(8)
        # 解析为 datetime 对象
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        # 计算结束日期（start_date + 1天）
        end_date = start_date + timedelta(days=1)
    except ValueError as e:
        print(f"日期格式错误：{e}")
        return


    # 2. 格式化时间字符串（ClickHouse 支持的 DateTime 格式）
    start_time = start_date.strftime("%Y-%m-%d 00:00:00")  # 如 '2025-05-01 00:00:00'
    end_time = end_date.strftime("%Y-%m-%d 00:00:00")      # 如 '2025-05-02 00:00:00'
    print(start_time)
    print(end_time)

    try:

        
        # 构造删除 SQL（参数化查询，避免注入）
        query = """
        DELETE FROM airport_observation_data 
        WHERE 
            observation_timestamp > %(start_time)s 
            AND observation_timestamp <= %(end_time)s
            AND station_type = 'jd'
        """
        
        # 使用 command() 方法执行删除（HTTP 客户端无 execute 方法）
        clickclient.command(query, parameters={
            'start_time': start_time,
            'end_time': end_time
        })
        
        print(f"成功删除 {start_time} 至 {end_time} 的 mh 类型数据")
        
    except Exception as e:
        print(f"删除失败：{str(e)}")
        
    finally:
        clickclient.close()


def decoder_main(time):
    status = True
    mess = ""
    name = f"jdsk{time}"

    # 定义数据类型
    dt = np.dtype([
        ('hour', np.int32),
        ('min', np.int16),
        ('w', 'i1'),
        ('n', 'i1'),
        ('dd', 'i1'),
        ('ff', 'i1'),
        ('vv', 'i1'),
        ('ww', 'i1'),
        ('ns1', 'i1'),
        ('c1', 'i1'),
        ('hh1', np.int16),
        ('ns2', 'i1'),
        ('c2', 'i1'),
        ('hh2', np.int16),
        ('ns3', 'i1'),
        ('c3', 'i1'),
        ('hh3', np.int16),
        ('ns4', 'i1'),
        ('c4', 'i1'),
        ('hh4', np.int16),
        ('tt', np.int16),
        ('td', np.int16),
        ('ppp', np.int16),
        ('spsp1', np.int16),
        ('spsp2', np.int16),
        ('rrr', np.int16),
        ('r', np.int16),
        ('s', np.int16),
        ('quesheng', np.int32)
    ])

      # 读取数据
    a = np.fromfile(f"./obs/JDPORT/{name}.dbf", dtype=dt)

      # 1. 筛选有效记录：hour != -1 且 min == 0
    valid_mask = (a['hour'] != -1) & (a['min'] == 0)
    valid_records = a[valid_mask]
    n_rows = len(valid_records)
    if n_rows == 0:
        return True, "无有效记录"

      # 2. 处理风向（dd）
    dd_raw = valid_records['dd'].astype(np.int32) * 10  # 基础计算
    dd = dd_raw.copy()
    # 条件：(dd==0且ff==0) 或 dd==-1 → 设为-999
    mask_dd_invalid = (valid_records['dd'] == 0) & (valid_records['ff'] == 0) | (valid_records['dd'] == -1)
    dd[mask_dd_invalid] = -999

      # 3. 处理风速（ff）：ff==-1 → 设为-999
    ff = valid_records['ff'].copy().astype(np.int32)
    ff[ff == -1] = -999


    vv_codes = valid_records['vv'].astype(np.float64)
    visibility_array = np.full(n_rows, -999.0)
    # 批量处理特殊值
    mask_vv_neg4 = (vv_codes == -4)
    visibility_array[mask_vv_neg4] = 10.1
    mask_vv_neg3 = (vv_codes == -3)
    visibility_array[mask_vv_neg3] = -999
    mask_vv_neg1 = (vv_codes == -1)
    visibility_array[mask_vv_neg1] = -999
    # 处理其他编码（使用vectorize批量转换）
    vectorized_vis = np.vectorize(visibility_code_convert)
    mask_other = ~mask_vv_neg4 & ~mask_vv_neg3 & ~mask_vv_neg1
    visibility_array[mask_other] = vectorized_vis(vv_codes[mask_other])
    visibility_array = np.where(visibility_array == -1, -999, visibility_array)


    visibility_array = np.where(
    visibility_array != -999,  # 条件：不为-999
    visibility_array * 1000,  # 满足条件时乘以1000
    visibility_array          # 不满足条件时保持原值（-999）
    )
      # 5. 处理低云要素（ns1-ns4, hh1-hh4）
    # 堆叠成二维数组（n_rows, 4）
    ns_array = np.stack([valid_records[f'ns{i}'] for i in range(1, 5)], axis=1)
    hh_array = np.stack([valid_records[f'hh{i}'] for i in range(1, 5)], axis=1)
    # 找到每行第一个非-1的低云索引
    first_non_neg1 = np.argmax(ns_array != -1, axis=1)
    all_neg1 = np.all(ns_array == -1, axis=1)
    first_non_neg1[all_neg1] = -1  # 全为-1的行标记为无效
    # 提取低云量和云高
    low_cloud_amount = np.where(
        first_non_neg1 == 0, ns_array[:, 0],
        np.where(first_non_neg1 == 1, ns_array[:, 1],
        np.where(first_non_neg1 == 2, ns_array[:, 2],
        np.where(first_non_neg1 == 3, ns_array[:, 3], -1)))
    ).astype(np.int32)
    low_cloud_height = np.where(
        first_non_neg1 == 0, hh_array[:, 0],
        np.where(first_non_neg1 == 1, hh_array[:, 1],
        np.where(first_non_neg1 == 2, hh_array[:, 2],
        np.where(first_non_neg1 == 3, hh_array[:, 3], -1)))
    ).astype(np.int32)
    # 低云量特殊值：-2 → 9
    low_cloud_amount[low_cloud_amount == -2] = 9
    # 云高无效条件：>=2500 或 低云量=-1 或 云高=-1/0
    mask_cloud_invalid = (low_cloud_height >= 2500) | (low_cloud_amount == -1) | \
                         (low_cloud_height == -1) | (low_cloud_height == 0)
    low_cloud_amount[mask_cloud_invalid] = -999
    low_cloud_height[mask_cloud_invalid] = -999
    # 处理器测值（hh%10==1 → 减1）
    mask_measure = (low_cloud_height % 10 == 1)
    low_cloud_height[mask_measure] -= 1
    low_cloud_height = np.where(low_cloud_height < 0, -999, low_cloud_height)   


    hour_str = valid_records['hour'].astype(str)
    # 批量处理"24时"转为次日0时（复用parse_special_time函数）
    date_str_series = pd.Series(hour_str).apply(parse_special_time)
    # 批量转换为datetime


       # 6. 处理总云量（n）：-2→9，-1→-999
    n = np.where(valid_records['n'] == -2, 9, valid_records['n']).astype(np.int32)
    n[n == -1] = -999

      # 提取温度、露点、气压数组（已过滤无效值）
    temp_raw = valid_records['tt'].astype(np.float64)
    dew_raw = valid_records['td'].astype(np.float64)        

      # 向量化实现原逻辑：value/10 if value < 500 else (500 - value)/10
    temp = np.where(temp_raw < 500, temp_raw / 10.0, (500 - temp_raw) / 10.0)
    temp = np.where(temp < -60, -999, temp)  
    dew = np.where(dew_raw < 500, dew_raw / 10.0, (500 - dew_raw) / 10.0)    
    dew = np.where(dew < -60, -999, dew)   

    press = valid_records['ppp'].astype(np.int32)  # 原始气压值
    # 第一步：若pressure == -1，则设为-999（对应原逻辑第一行）
    press = np.where(press == -1, -999, press)

      # 第二步：若pressure <800 或 >1200，则设为-999（对应原逻辑第二行）
    press = np.where((press < 800) | (press > 1200), -999, press)

    total_cloud_cover = valid_records['n'].astype(np.int32)  # 原始气压值
    total_cloud_cover = np.where(total_cloud_cover == -1, -999, total_cloud_cover)

      # 过滤无效值（温度<露点、气压无效等）
    mask_valid_hum = (temp != -999) & (dew != -999) & (press != -999) & (temp >= dew)
    rel_humidity = np.full(len(temp), -999.0)  # 初始化默认值        

    hum2 = np.vectorize(hum)
    # 批量计算有效样本的相对湿度
    rel_humidity[mask_valid_hum] = hum2(
        temp[mask_valid_hum] + 273.15,
        dew[mask_valid_hum] + 273.15,
        press[mask_valid_hum] * 100,
        True
    )
    mask_invalid1 = (press == -999) | (temp == -999) | (dew == -999)
    rel_humidity[mask_invalid1] = -999        

      # 条件2：temperature < dew_point → 设为-999
    mask_invalid2 = (temp < dew)
    rel_humidity[mask_invalid2] = -999

      # 新增：将NaN值改为-999
    mask_nan = np.isnan(rel_humidity)
    rel_humidity[mask_nan] = -999

    temp = np.where(
    temp != -999,  # 条件：不为-999
    temp  + 273.15,  # 满足条件时乘以1000
    temp          # 不满足条件时保持原值（-999）
    )
    dew = np.where(
    dew != -999,  # 条件：不为-999
    dew  + 273.15,  # 满足条件时乘以1000
    dew          # 不满足条件时保持原值（-999）
    )

      # 10. 处理24h降水（rrr）：rrr==-1→-999
    rrr = valid_records['rrr'].copy().astype(np.int32)
    rrr[rrr == -1] = -999


       # 提取hour字段并转换为字符串
    hour_str = valid_records['hour'].astype(str)
    # 批量处理"24时"转为次日0时（复用parse_special_time函数）
    date_str_series = pd.Series(hour_str).apply(parse_special_time)
    # 批量转换为datetime
    observation_time = pd.to_datetime(date_str_series, format="%Y%m%d%H")
    # 2. 再将无时区的 datetime 类型转换为带时区的类型
    observation_time = observation_time.dt.tz_localize('Asia/Shanghai')

      # 12. 构建DataFrame并写入CSV
    df = pd.DataFrame({
        'station_code': valid_records['s'].astype(str),
        'observation_time': observation_time - pd.Timedelta(hours=8), #北京转UTC
        'observation_timestamp':observation_time,
        'temperature': temp,
        'dew_point_temperature': dew,
        'humidity': rel_humidity,
        'wind_direction': dd,
        'wind_speed': ff,
        'visibility': visibility_array,  # 提前用向量处理visibility_code_convert
        'total_cloud_cover': total_cloud_cover,
        'low_cloud_cover': low_cloud_amount,
        'cloud_height': low_cloud_height,
        'sea_level_pressure': press,


            # 处理固定值字段（关键修改）
        'radiation': np.full(n_rows, -999),  # 生成长度为n_rows、值全为-999的数组
        'precipitation': np.full(n_rows, -999),
        'pressure': np.full(n_rows, -999),
        'station_type': np.full(n_rows, 'jd', dtype=object)  # 生成长度为n_rows、值全为'mh'的字符串数组


           # 其他字段...


       })

            # ----------------------
    # 2. 读取站号映射表（关键新增步骤）
    # ----------------------
    # 假设映射关系存储在ClickHouse的`station_info`表中，包含字段：station_code、station_id、station_name
    # 若映射表是本地文件，可用pd.read_csv()读取
    try:
        # 从ClickHouse查询映射关系
        station_info_sql = "SELECT station_code, station_id, station_name,longitude,latitude FROM station_info"
        station_info_df = clickclient.query_df(station_info_sql)
    except Exception as e:
        return False, f"读取映射表失败：{str(e)}"
    df = df.merge(
        station_info_df[['station_code', 'station_id', 'station_name', 'longitude','latitude']],  # 只取需要的字段
        on='station_code',  # 关联键：站号
        how='inner'
    )       

    delete_jd_data(time)
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

    return status, mess


if __name__ == "__main__":
    # 示例调用：处理20250611的数据
    status, message = decoder_main(20250610)
    print(message)