import numpy as np
import pandas as pd
from clickhouse_connect import get_client
from faker import Faker
from datetime import datetime, timedelta
import random
import tqdm
import time
import logging
import threading
from queue import Queue

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

def insert_worker(worker_id, task_queue, results_queue, mode_types, forecast_dates, forecast_hours):
    """工作线程函数：从队列获取任务并执行数据插入"""
    # 每个线程创建自己的客户端连接
    thread_client = get_client(
        host='192.168.3.224',
        port=8123,
        username='default',
        password='Abc123456@',
        database='szybjydb',
        compression=True
    )
    
    while True:
        task = task_queue.get()
        if task is None:  # 收到退出信号
            break
            
        batch_idx, batch_size = task
        
        try:
            # 生成一批数据
            batch_data = generate_weather_data(batch_size, mode_types, forecast_dates, forecast_hours)
            
            # 使用clickhouse-connect的insert方法
            start_time = time.time()
            thread_client.insert(
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
            elapsed_time = time.time() - start_time
            
            # 将结果放入结果队列
            results_queue.put((batch_idx, batch_size, elapsed_time))
            
            print(f"线程 {worker_id} 完成批次 {batch_idx+1}，用时: {elapsed_time:.2f} 秒，"
                  f"速度: {batch_size/elapsed_time:.0f} 条/秒")
        except Exception as e:
            print(f"线程 {worker_id} 处理批次 {batch_idx+1} 时出错: {e}")
        finally:
            task_queue.task_done()
    
    # 关闭线程内的客户端连接
    thread_client.close()

def batch_insert_data_multithreaded(
    num_threads=4, 
    batch_size=100000, 
    total_records=1000000
):
    """使用多线程批量插入数据到ClickHouse并统计用时"""
    # 预定义模式类型和预报日期范围
    mode_types = ['ECMWF', 'GFS', 'WRF', 'HRRR', 'ICON']
    forecast_dates = [(datetime.now() - timedelta(days=i)).strftime('%Y%m%d') for i in range(30)]
    forecast_hours = ['08', '20']
    
    # 计算批次数量
    num_batches = (total_records + batch_size - 1) // batch_size
    
    # 创建任务队列和结果队列
    task_queue = Queue()
    results_queue = Queue()
    
    # 填充任务队列
    for batch_idx in range(num_batches):
        task_queue.put((batch_idx, batch_size))
    
    # 启动工作线程
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(
            target=insert_worker,
            args=(i+1, task_queue, results_queue, mode_types, forecast_dates, forecast_hours)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 等待所有任务完成
    task_queue.join()
    
    # 发送退出信号给所有线程
    for _ in range(num_threads):
        task_queue.put(None)
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 计算总用时
    total_elapsed_time = time.time() - total_start_time
    
    # 收集所有批次的用时数据
    batch_times = []
    while not results_queue.empty():
        batch_times.append(results_queue.get()[2])
    
    # 打印统计信息
    print("\n===== 插入统计 =====")
    print(f"总记录数: {total_records:,}")
    print(f"批次大小: {batch_size:,}")
    print(f"总批次: {num_batches}")
    print(f"线程数: {num_threads}")
    print(f"总用时: {total_elapsed_time:.2f} 秒")
    print(f"平均批次用时: {np.mean(batch_times):.2f} 秒")
    print(f"最快批次: {np.min(batch_times):.2f} 秒")
    print(f"最慢批次: {np.max(batch_times):.2f} 秒")
    print(f"平均插入速度: {total_records/total_elapsed_time:.0f} 条/秒")

if __name__ == "__main__":
    # 使用10个线程插入100万条数据，每批10万条
    batch_insert_data_multithreaded(num_threads=4, batch_size=100000, total_records=1000000)    
