import datetime
import glob
import pytz
import numpy as np
import pandas as pd
import os
import requests
import subprocess
import json
import os
from datetime import datetime,time,timedelta
import re
import os
import json
from pathlib import Path
import sys
def switch(case):
    cases = {
        'AL': 'L',
        'EP': 'E',
        'CP': 'C',
        'WP': 'W',
        'SC': 'O',
        'AU': 'U',
        'SP': 'P',
        'SI': 'S',
        'BB': 'B',
        'AA': 'A',
        'SL': 'Q'
    }
    return cases.get(case,'HC')

def parse_wmo_bulletin(file_path, output_dir, separate_files=False):
    bulletin = read_bulletin_from_file(file_path)
    utc_date = get_date_from_bulletin(file_path)

    """
    解析WMO热带气旋电报，提取关键信息
    参数：bulletin - 电报文本字符串
    返回：包含解析结果的字典
    """
    result={
        'issue_time':utc_date.strftime('%Y-%m-%d %H:%M UTC') if utc_date else None,
        'storms':[]
    }
    ii = 0
    lines = bulletin.strip().split('\n')
    storm_blocks=split_storm_blocks(lines)
    for block in storm_blocks:
        storm_data=process_storm_block(block,utc_date)
        if storm_data:
            ii += 1
            result['storms'].append(storm_data)
    if ii>0:
        time_ = save_to_json(result,output_dir,separate_files)
    else:
         time_ = None
    return time_    


def split_storm_blocks(lines):
    storm_blocks=[]
    current_block = []
    block_started = False
    for line in lines:
        stripped_line = line.strip()
        if re.match(r'^\S+\s+BABJ\b',stripped_line):
            if current_block:
                storm_blocks.append(current_block)
                current_block = []
            current_block.append(stripped_line)
            block_started = True
            continue
        if block_started:
            if stripped_line:
                current_block.append(stripped_line)
            else:
                block_started = False
    if current_block:
        storm_blocks.append(current_block)
    return storm_blocks

def process_storm_block(block,utc_date):
    storm = {
        'bulletin_id': None,
        'storm_name': None,
        'storm_number': None,
        'storm_type': None,
        'initial_position': None,
        'initial_pressure': None,
        'initial_wind_speed': None,
        'movement': None,
        'forecasts': [],
        'wind_radii': {},
    }
    current_wind_speed = None
    # 提取电报标识和时间
    for line in block:
        # 电报标识（如WTPQ20 BABJ 242100）
        if re.match(r'^[A-Z0-9]{6}\s+[A-Z]{4}\s+\d{6}', line):
            parts = line.split()
            storm['bulletin_id'] = parts[0]
        if line.startswith(('TD','TS','TY','STY','Super','SUPER')):
            parts=re.split(r'\s+',line.strip())
            storm['storm_type']   = parts[0]
            storm['storm_name']   = parts[1]
            storm['storm_number'] = parts[2]        
        if line.startswith('00HR'):
            position_data = re.findall(r'[\d.]+\w', line)
            if len(position_data) >= 4:
                # 解析经纬度（格式示例：10.8N 110.6E）
                lat_value = float(position_data[1][:-1])
                lat_dir = position_data[1][-1]
                lon_value = float(position_data[2][:-1])
                lon_dir = position_data[2][-1]
                
                storm['initial_position'] = {
                    'latitude':f"{lat_value}{lat_dir}",
                    'longitude':f"{lon_value}{lon_dir}"
                }

                # 解析气象要素
                storm['initial_pressure'] = position_data[3] + 'Pa'
                storm['initial_wind_speed'] = position_data[4]+'/s'
 
        if line.startswith('MOVE'):
            if move_match := re.search(r'MOVE\s+([A-Z]+)\s+(\d+)KM/H', line):
                storm['movement'] = {
                    'direction': move_match.group(1),
                    'speed': f"{move_match.group(2)} km/h"
                }
        if forecast_match := re.match(
            r'P\+(\d+)HR\s+(\d+\.\d+)([NS])\s+(\d+\.\d+)([EW])\s+(\d+)HPA\s+(\d+)M/S=',
            line
        ):
        
            storm['forecasts'].append({
                'lead_time': int(forecast_match.group(1)),  # 预报时效（小时）
                'latitude': f"{forecast_match.group(2)}{forecast_match.group(3)}",  # 纬度
                'longitude': f"{forecast_match.group(4)}{forecast_match.group(5)}",  # 经度
                'pressure': f"{forecast_match.group(6)}hPa",  # 中心气压
                'wind_speed': f"{forecast_match.group(7)}m/s"  # 最大风速
            })

        current_wind_speed = None
        if wind_speed_match := re.match(r'^\s*(\d+)KTS\s+WINDS\s*', line):
            wind_radii_str     = f"{wind_speed_match.group(1)}KTS"
            storm['wind_radii']= {wind_radii_str:{}}

    for line in block:
        if line.endswith(('NORTHEAST','SOUTHEAST','SOUTHWEST','NORTHWEST')):
            info = line.split()
            print(info)
            if len(info)==4:
                storm['wind_radii'][wind_radii_str][info[3]] = {}
                storm['wind_radii'][wind_radii_str][info[3]] = info[2]
            elif len(info)==2:
                storm['wind_radii'][wind_radii_str][info[1]] = {}
                storm['wind_radii'][wind_radii_str][info[1]] = info[0]
    print(storm['storm_name'])
    if storm['initial_pressure'] == None or storm['storm_name'] == None or storm['storm_name'].isdigit():
        storm = None
    return storm #if any(storm.values()) else None


def get_date_from_bulletin(file_path):
    basename = os.path.basename(file_path)
    timestamp = basename.split('_')[8].split('.')[0]
    year = timestamp[:4]
    month = timestamp[4:6]
    day = timestamp[6:8]
    hour = timestamp[8:10]
    bjt_date = datetime.strptime(f'{year}-{month}-{day} {hour}:00:00', '%Y-%m-%d %H:%M:%S')
    utc_date = bjt_date - timedelta(hours=8)
    return utc_date

def read_bulletin_from_file(file_path):
    """
    从txt文件读取电报内容
    参数：file_path - 电报文件路径
    返回：电报文本字符串
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到")
        return None
    except Exception as e:
        print(f"读取文件时发生错误：{str(e)}")
        return None


# save to json
def save_to_json(parsed_data, output_dir,separate_files=False):
    """
    将解析结果保存为JSON文件
    参数：parsed_data - 解析结果字典
         output_path - 输出文件路径
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    base_name = parsed_data['issue_time'].replace(' ','').replace(':','').replace('-','')[:12]
    time      = datetime.strptime(parsed_data['issue_time'], "%Y-%m-%d %H:%M UTC")
    time_     = time.strftime("%Y%m%d%H%M")
    if separate_files and parsed_data['storms']:
        for idx,storm in enumerate(parsed_data['storms'],1):
            filename=f"{time_}.json"
            with open(output_dir / filename,'w') as f:
                json.dump(storm,f,ensure_ascii=False,indent=2)
    else:
        filename=f"{time_}.json"
        with open(output_dir / filename,'w') as f:
            json.dump(parsed_data,f,ensure_ascii=False,indent=2)
    return time_


def run_main_decode_tfb(filen_tfb,tfb_path_json,separate_files=False):
    time_ = parse_wmo_bulletin(
            file_path=filen_tfb,
            output_dir=tfb_path_json,
            separate_files=False
        )
    return time_
