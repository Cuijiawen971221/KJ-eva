import numpy as np
from humidity_calc import hum  # 假设该模块已正确实现相对湿度计算

import re
from clickhouse_util import clickclient
import pandas as pd
from datetime import datetime, timedelta


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
        return -999
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
        return -999         # 无效编码返回 None



def extract_four_char_groups(data, end):
    # 截取前end个字符
    substring = data[:end]
    
    # 使用正则表达式匹配所有由4个字母或数字组成的完整单元
    return re.findall(r'\b[a-zA-Z0-9]{4}\b', substring)

def extract_four_char_groups2(data,  end=None):
    # 如果未指定end，则默认为数据长度
    if end is None:
        end = len(data)
    # 结果数组
    result = []
    # 从start开始，每5个字节为一组进行处理
    current_pos = 0
    while current_pos + 5 <= end:
        # 提取5字节组
        group = data[current_pos:current_pos + 5]
        
        # 检查该组是否全为0
        # 检查该组是否全为ASCII码0（即空字节'\x00'）
        if all(ord(c) == 0 for c in group):
            break
        
        # 提取前四个字符
        first_four = group[:4]
        
        # 将前四个字符添加到结果数组中
        result.append(first_four)
        
        # 移动到下一组
        current_pos += 5
    
    return result


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



dt = np.dtype([
    ('hour', np.int32),
    ('min', np.int16),      # 0-59 分钟
    ('w', 'i1'),           # 危险标志  -1无危险
    ('n', 'i1'),           # 总云量  -1无危险
    ('dd', 'i1'),          # 风向 值范围0-36,乘10为实际值
    ('ff', 'i1'),          # 风速 米/秒
    ('vv', 'i1'),          # 能见度  
    ('ww', 'i1'),
    ('ns1', 'i1'),         # 第一层分云量  
    ('c1', 'i1'),          # 第一层分云状
    ('hh1', np.int16),     # 第一层云底高
    ('ns2', 'i1'),         # 第二层分云量
    ('c2', 'i1'),          # 第二层分云状
    ('hh2', np.int16),     # 第二层云底高
    ('ns3', 'i1'),         # 第三层分云量
    ('c3', 'i1'),          # 第三层分云状
    ('hh3', np.int16),     # 第三层云底高
    ('ns4', 'i1'),         # 第四层分云量
    ('c4', 'i1'),          # 第四层分云状
    ('hh4', np.int16),     # 第四层云底高
    ('tt', np.int16),      # 气温，值/10
    ('td', np.int16),      # 露点温度，(500-值)/10
    ('ppp', np.int16),     # 海平面气压  
    ('spsp1', np.int16),   # 危险天气补充组一
    ('spsp2', np.int16),   # 危险天气补充组二
    ('rrr', np.int16),     # 24小时降水量
    ('r', np.int16),       # 跑道视程
    ('s', np.int16),       # 站号
    ('quesheng', np.int32) # 未知字段
])


def delete_mh_data(start_date_num):
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
            AND station_type = 'mh'
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
    print(f'处理{time}数据')
    status = True
    mess = ""
    # 定义目标日期
    target_date = time    
    with open(f"./obs/MHPORT/mhsk{target_date}.dbf", 'rb') as file:
    # 读取整个文件内容
        data = file.read()
        
        # 查找目标日期的位置
        target_bytes = (int(target_date)*100+1).to_bytes(4, byteorder='little')  # 转换为4字节整数（小端序）
        start_pos = data.find(target_bytes)    

        sites =extract_four_char_groups2(data[72:start_pos].decode('utf-8'), start_pos)
        #print(sites)
        #print(len(sites))   
        if start_pos == -1:
            return False, f"未找到起始标记 {target_date}"

    
        # 从起始位置开始加载数据
        a = np.frombuffer(data[start_pos:], dtype=dt)

        valid_mask = (a['hour'] != 0) & (a['min'] == 0)
        valid_records = a[valid_mask]  # 仅保留有效记录
        valid_indices = np.where(valid_mask)[0]  # 有效记录的原始索引
        n_rows = len(valid_records)  # 或 len(site_array)，确保所有列长度相同
        # 批量计算风向（dd）
        dd = valid_records['dd'].astype(np.int32) * 10 # 基础计算
        # 批量应用条件（用布尔索引替代if）
        dd[(valid_records['dd'] == 0) & (valid_records['ff'] == 0)] = -999  # 静风
        dd[dd == -40] = -999  # 风向不定
        dd[(dd == -10) | (dd > 360)] = -999  # 无效值

        # 批量计算风速（ff）
        ff = (valid_records['ff'].copy()).astype(np.int32)
        ff[ff < 0] = -999  # 无效值
        ff[ff == -1] = -999


        vv_codes = valid_records['vv'].astype(np.float64)
        visibility_array = np.full(n_rows, -999.0)

        # 批量处理特殊值
        mask_vv_neg4 = (vv_codes == -4)
        visibility_array[mask_vv_neg4] = 10.1

        mask_vv_neg3 = (vv_codes == -3)
        visibility_array[mask_vv_neg3] = -999

        # 处理其他编码（使用vectorize批量转换）
        vectorized_vis = np.vectorize(visibility_code_convert)
        mask_other = ~mask_vv_neg4 & ~mask_vv_neg3
        visibility_array[mask_other] = vectorized_vis(vv_codes[mask_other])
        
        visibility_array = np.where(
        visibility_array != -999,  # 条件：不为-999
        visibility_array * 1000,  # 满足条件时乘以1000
        visibility_array          # 不满足条件时保持原值（-999）
        )


        # 构建ns1-ns4和hh1-hh4的二维数组（形状：[有效记录数, 4]）
        ns_array = np.stack([valid_records[f'ns{i}'] for i in range(1,5)], axis=1)
        hh_array = np.stack([valid_records[f'hh{i}'] for i in range(1,5)], axis=1)        

        # 找到每行第一个非-1的低云索引（向量操作替代小循环）
        first_non_neg1 = np.argmax(ns_array != -1, axis=1)  # 每行第一个非-1的位置
        all_neg1 = np.all(ns_array == -1, axis=1)  # 全为-1的行
        first_non_neg1[all_neg1] = -1  # 标记无效        

        # 批量提取低云量和云高
        low_cloud_amount = (np.where(
            first_non_neg1 == 0, ns_array[:,0],
            np.where(first_non_neg1 == 1, ns_array[:,1],
            np.where(first_non_neg1 == 2, ns_array[:,2],
            np.where(first_non_neg1 == 3, ns_array[:,3], -1)))
        )).astype(np.int32)
        low_cloud_height = (np.where(
            first_non_neg1 == 0, hh_array[:,0],
            np.where(first_non_neg1 == 1, hh_array[:,1],
            np.where(first_non_neg1 == 2, hh_array[:,2],
            np.where(first_non_neg1 == 3, hh_array[:,3], -1)))
        )).astype(np.int32)        

        # 过滤无效低云（>=2500米或无效值）
        mask_invalid_cloud = (low_cloud_height >= 2500) | (low_cloud_height < 0)  | (low_cloud_height == -1)
        low_cloud_amount[mask_invalid_cloud] = -999
        low_cloud_height[mask_invalid_cloud] = -999        

        # 处理器测值（末尾为1的情况）
        mask_measure = (low_cloud_height % 10 == 1)
        low_cloud_height[mask_measure] -= 1
        low_cloud_height = np.where(low_cloud_height < 0, -999, low_cloud_height)    

        # 提取hour字段并转换为字符串
        hour_str = valid_records['hour'].astype(str)
        # 批量处理"24时"转为次日0时（复用parse_special_time函数）
        date_str_series = pd.Series(hour_str).apply(parse_special_time)
        # 批量转换为datetime
        # 1. 先将字符串转换为无时区的 datetime 类型
        observation_time = pd.to_datetime(date_str_series, format="%Y%m%d%H")

        # 2. 再将无时区的 datetime 类型转换为带时区的类型
        observation_time = observation_time.dt.tz_localize('Asia/Shanghai')

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

        # 提取站点信息（批量计算索引）
        site_indices = valid_indices // 96  # 有效记录对应的站点索引
        site_array = np.array(sites)[site_indices]


        # 构建DataFrame
        df = pd.DataFrame({
            # 'station_id': site_array,
            'station_code': site_array,
            'observation_time': observation_time  - pd.Timedelta(hours=8),  #北京转UTC,
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
            'station_type': np.full(n_rows, 'mh', dtype=object)  # 生成长度为n_rows、值全为'mh'的字符串数组


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
        # 处理未匹配到的站号（如设为-999或空字符串）
        #df['station_id'] = df['station_id'].fillna(-999)  # 数值型用-999
        #df['station_name'] = df['station_name'].fillna('未知')  # 字符串型用'未知'

        delete_mh_data(time)
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
    return status,mess            

if __name__ == "__main__":

    #decoder_main(20250101)
    for date_num in range(20250501, 20250526 + 1):
        decoder_main(date_num)
    


