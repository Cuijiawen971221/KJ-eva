import os
import sys
import json
from typhoon_decode_function import *  # 导入外部解码函数
from datetime import datetime, timedelta

def get_processed_files(info_file):
    """从信息文件(JSON)中获取已处理的文件列表及最后修改时间"""
    if os.path.exists(info_file):
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_processed_files(info_file, data):
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def process_typhoon_reports(txt_path, json_path, config_dir, typhoon_mess_path):
    path1 = txt_path
    """处理path1路径下的台风报文件，包括更新的文件"""
    os.makedirs(config_dir, exist_ok=True)
    
    # 彻底告别笨重的 txt 逐行解析，改为纯 JSON 字典映射记录 state
    info_file = os.path.join(config_dir, 'decode_history.json')
    processed_files = get_processed_files(info_file)
    
    if not os.path.exists(path1):
        print(f"路径 {path1} 不存在")
        return
        
    all_txt_files = [f for f in os.listdir(path1) 
                    if f.endswith('.TXT') and os.path.isfile(os.path.join(path1, f))]
    
    # 处理新文件或更新的文件
    updated_files_count = 0
    for txt_file in all_txt_files:
        file_path = os.path.join(path1, txt_file)
        current_mtime = os.path.getmtime(file_path)
        
        # 只要文件是新的或者被修改过，就重新解析
        if txt_file not in processed_files or current_mtime != processed_files[txt_file]:
            try:                
                pp_info = run_main_decode_tfb(file_path, json_path, separate_files=False)
                
                folder_name = txt_file[-21:-9]               ## orig tfb:type=*.txt
                utc_t = (datetime.strptime(folder_name,"%Y%m%d%H%M") - timedelta(hours=8)).strftime("%Y%m%d%H%M")
                                                         
                mess_dir = os.path.join(typhoon_mess_path, f'{utc_t[0:10]}00')
                os.makedirs(mess_dir, exist_ok=True)

                # 留下干净的解码成功标志给主调度器抓取
                if pp_info:
                    ok_path = os.path.join(mess_dir, 'decoded.ok')
                    with open(ok_path, 'w', encoding='utf-8') as f:
                        pass
                    print(f"已在 {mess_dir} 中创建 decoded.ok")
                
                # 记录在历史字典中
                processed_files[txt_file] = current_mtime
                save_processed_files(info_file, processed_files)
                
                print(f"已成功处理（新文件或更新）: {txt_file}")
                updated_files_count += 1
            except Exception as e:
                print(f"处理 {txt_file} 时出错: {str(e)}")
    
    if updated_files_count == 0:
        print("没有新的或更新的台风报文件需要处理")
    else:
        print(f"共处理了 {updated_files_count} 个新的或更新的台风报文件")

if __name__ == "__main__":
    # 实际的台风报文件路径和配置目录
    datetime_now      = sys.argv[1] #(datetime.datetime.now()).strftime("%Y%m%d")#sys.argv[1]
    txt_path          = f'/vol8/home/kongjun/OBS/TFB/{datetime_now}/'
    json_path         = '/vol8/home/kongjun/VERIFY/OBS_typhoon/tfb_json/'
    config_path       = '/vol8/home/kongjun/VERIFY/OBS_typhoon/tfb_mess/'  # 配置目录，例如"config"
    typhoon_mess_path = '/vol8/home/kongjun/VERIFY/OBS_typhoon/typhoon_mess/'
    process_typhoon_reports(txt_path, json_path, config_path, typhoon_mess_path)
    
