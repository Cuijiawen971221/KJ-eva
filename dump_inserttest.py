import numpy as np
import pandas as pd
from clickhouse_connect import get_client
from faker import Faker
from datetime import datetime, timedelta
import random
import tqdm
import time
import logging

# 配置ClickHouse连接
client = get_client(
    host='192.168.3.224',
    port=8123,
    username='default',
    password='Abc123456@',
    database='szybjydb',
    compression=True
)

# 初始化Faker生成器
fake = Faker()

# 配置日志记录器，打印SQL语句
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('clickhouse_connect.driver.httpclient')

def generate_lat_lon():
    """生成全球随机经纬度"""
    return fake.longitude(), fake.latitude()

def generate_weather_data(num_records, mode_types, forecast_dates, forecast_hours):
    """生成模拟气象数据"""
    data = []
    
    for _ in range(num_records):
        # 基础信息
        longitude, latitude = generate_lat_lon()
        mode_type = random.choice(mode_types)
        forecast_date = random.choice(forecast_dates)
        forecast_hour = random.choice(forecast_hours)
        forecast_interval = random.randint(0, 168)
        
        # 气象参数
        temperature = round(np.random.normal(15, 10), 2)
        dew_point = round(min(temperature - 2, np.random.normal(10, 8)), 2)
        humidity = round(min(100, np.random.normal(60, 20)), 2)
        wind_speed = round(np.random.gamma(2, 2), 2)
        wind_direction = round(random.uniform(0, 360), 2)
        precipitation = round(np.random.exponential(10), 2)
        pressure = round(np.random.normal(1013, 10), 2)
        sea_level_pressure = round(pressure + np.random.normal(0, 5), 2)
        radiation = round(np.random.gamma(2, 20), 2)
        visibility = round(min(40, np.random.lognormal(2, 1)), 2)
        total_cloud_cover = round(min(100, np.random.normal(50, 30)), 2)
        low_cloud_cover = round(min(total_cloud_cover, np.random.normal(30, 20)), 2)
        cloud_height = round(np.random.lognormal(8, 0.5), 2)
        
        data.append((
           longitude,
             latitude,
            forecast_date,
             forecast_hour,
            mode_type,
             forecast_interval,
             temperature,
            dew_point,
             humidity,
             wind_speed,
             wind_direction,
             precipitation,
             pressure,
            sea_level_pressure,
             radiation,
             visibility,
             total_cloud_cover,
            low_cloud_cover,
            cloud_height
        ))
    
    return data

def batch_insert_data(batch_size=100000, total_records=1000000):
    """批量插入数据到ClickHouse并统计用时"""
    # 预定义模式类型和预报日期范围
    mode_types = ['ECMWF', 'GFS', 'WRF', 'HRRR', 'ICON']
    forecast_dates = [(datetime.now() - timedelta(days=i)).strftime('%Y%m%d') for i in range(30)]
    forecast_hours = ['08', '20']
    
    # 计算批次数量
    num_batches = (total_records + batch_size - 1) // batch_size
    
    # 记录总开始时间
    total_start_time = time.time()
    batch_times = []
    
    # 批量插入
    for batch_idx in tqdm.tqdm(range(num_batches), desc="插入批次"):
        # 记录批次开始时间
        batch_start_time = time.time()
        
        # 生成一批数据
        batch_data = generate_weather_data(batch_size, mode_types, forecast_dates, forecast_hours)
#        single_data = batch_data[0]
        print(batch_data[0])
        # 使用clickhouse-connect的insert方法
#        try:
        client.insert(
                table='surface_forecast_data',
                data=batch_data,
                column_names=[
                'longitude', 'latitude', 'forecast_date', 'forecast_hour', 'mode_type',
                'forecast_interval', 'temperature', 'dew_point_temperature', 'humidity',
                'wind_speed', 'wind_direction', 'precipitation', 'pressure',
                'sea_level_pressure', 'radiation', 'visibility', 'total_cloud_cover',
                'low_cloud_cover', 'cloud_height'
                ]
        )
#        except Exception as e:
#            print(f"完整错误信息: {e}")
#            return
        
        # 计算批次用时并记录
        batch_elapsed_time = time.time() - batch_start_time
        batch_times.append(batch_elapsed_time)
        
        # 打印批次用时信息
        print(f"批次 {batch_idx+1}/{num_batches} 完成，用时: {batch_elapsed_time:.2f} 秒，"
              f"速度: {batch_size/batch_elapsed_time:.0f} 条/秒")
    
    # 计算总用时
    total_elapsed_time = time.time() - total_start_time
    
    # 打印统计信息
    print("\n===== 插入统计 =====")
    print(f"总记录数: {total_records:,}")
    print(f"批次大小: {batch_size:,}")
    print(f"总批次: {num_batches}")
    print(f"总用时: {total_elapsed_time:.2f} 秒")
    print(f"平均批次用时: {np.mean(batch_times):.2f} 秒")
    print(f"最快批次: {np.min(batch_times):.2f} 秒")
    print(f"最慢批次: {np.max(batch_times):.2f} 秒")
    print(f"平均插入速度: {total_records/total_elapsed_time:.0f} 条/秒")

if __name__ == "__main__":
    # 插入100万条数据，每批10万条
    batch_insert_data(batch_size=100000, total_records=1000000)
