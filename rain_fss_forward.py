import os
import subprocess
import sys
from datetime import datetime, timedelta
# from read_fss import *
from yunyao_met import *
import base64
import re
import json
import datetime
from datetime import timezone
import os
import re
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.colors as colors
from matplotlib.ticker import MultipleLocator

plt.rcParams['font.sans-serif'] = ['SimHei']  # set font type
plt.rcParams['axes.unicode_minus'] = False    #

def pcolor_fss(data, times, outname, rain_scale, level ,distance):
    rain_scale = int(rain_scale)
    fig, ax = plt.subplots(figsize=(12, 8))
    # data = np.flipud(data)
    # set colormap (rainbow, level=10)
    cmap = plt.get_cmap('rainbow')
    bounds = np.linspace(0, 1, 11)  # 10 levels
    norm = colors.BoundaryNorm(bounds, cmap.N)
    
    # pcolor hotmap
    im = ax.matshow(data, cmap=cmap, norm=norm, aspect='auto')
    
    # set title and xlabel/ylabel
    ax.set_title(f"FSS随时间和时效变化 降水>={level}mm  窗口:{int(distance)}", fontsize=14, pad=20)
    ax.set_xlabel("起报时间", fontsize=14, labelpad=10)
    ax.set_ylabel("预报时效", fontsize=14, labelpad=10)
    
    # 设置y轴刻度（从下往上24,48,...,240）
    lead_times = list(range(rain_scale, 241, rain_scale))
    ax.set_yticks(np.arange(len(lead_times)))
    ax.set_yticklabels(lead_times[::-1])  # 反转顺序
    
    # 设置x轴刻度（时间格式化为MM/DD HH）
    if len(times) > 0:
        formatted_times = [f"{time[4:6]}/{time[6:8]} {time[8:10]}" for time in times]
        ax.set_xticks(np.arange(len(times)))
        ax.set_xticklabels(formatted_times, rotation=45, ha='right')
        ax.xaxis.set_ticks_position('bottom')
    
    # 创建colorbar(10级)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.2)
    cbar = plt.colorbar(im, cax=cax, ticks=np.linspace(0.05, 0.95, 10))
    cbar.set_label("FSS", rotation=270, labelpad=20, fontsize=14)
    # 添加网格线
    ax.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    plt.tight_layout()
    # plt.show()
    plt.savefig(outname)

def process_files(inputdir, starttime, endtime, level, distance, rain_scale, length):
    # 将时间字符串转换为datetime对象用于比较
    start_dt = datetime.strptime(starttime, "%Y%m%d%H")
    end_dt   = datetime.strptime(endtime, "%Y%m%d%H")
    # 定义所有可能的时效值（24到240，步长24）
    lead_times = list(range(rain_scale, length+1, rain_scale))  # [24, 48, 72, ..., 240]/[3,6,9,...,240]
    
    # 初始化结果字典：{起报时间: {时效: FSS值}}
    result_dict = {}
    
    # 获取所有符合命名规则的文件
    all_files = [f for f in os.listdir(inputdir) 
                if re.match(r'fss\d+\.\d{10}$', f)]
    print(f"找到{len(all_files)}个符合命名规则的文件")
    
    # 筛选在时间范围内的文件并计算起报时间
    valid_files = []
    initial_timelist = []
    for filename in all_files:
        # if 1==1:
        try:
            # 从文件名提取时效和验证时间
            ## fss024.2025050200  ||||||     024   2025050200
            match = re.match(r'fss(\d+)\.(\d{10})', filename)
            lead_time = int(match.group(1))
            valid_time_str = match.group(2)   ## obs time
            valid_dt = datetime.strptime(valid_time_str, "%Y%m%d%H")
            
            ## 计算起报时间 = 验证时间 - 时效
            initial_dt = valid_dt - timedelta(hours=lead_time)  ## forcast starttime
            initial_time_str = initial_dt.strftime("%Y%m%d%H")  ## 
            ## time modifty 
            left_t   = start_dt - timedelta(hours=length)## fss fig time_min

            ## 
            if (lead_time in lead_times) and (initial_dt >= left_t):## (start_dt <= valid_dt <= end_dt) and 
                valid_files.append(f'{filename}')               ## filename list
                initial_timelist.append(initial_time_str)       ## forecast strattime list

        except Exception as e:
            print(f"处理文件{filename}时出错: {e}")
            continue
    
    # 收集所有唯一的起报时间并排序
    unique_initial_times = sorted(list(set([t for t in initial_timelist])))

    # print(unique_initial_times)
    # 初始化结果数组：行是时效，列是起报时间
    result_array = np.full((len(lead_times), len(unique_initial_times)), np.nan)
    # 创建起报时间到列索引的映射
    initial_to_col = {time: idx for idx, time in enumerate(unique_initial_times)}

    # 创建时效到行索引的映射（从24到240）
    lead_to_row = {lead: idx for idx, lead in enumerate(sorted(lead_times))}

    # 处理每个文件
    for ii,filenameii in enumerate(valid_files):
        lead_time = int(filenameii[3:6].lstrip('0'))
        initial_time = initial_timelist[ii]
        row = lead_to_row[lead_time]
        col = initial_to_col[initial_time]
        # print('>>>>>>>>>>>>>>>>>>>>>>>>>>>',filenameii,lead_time,initial_time,row,col)
        try:
        # if 1==1:
            # 读取文件内容
            with open(f'{inputdir}/{filenameii}', 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 8:
                    file_level = float(parts[0])
                    file_distance = int(parts[2])
                    fss = float(parts[5])
                    # print('*****',file_level,level,file_distance, distance)
                    if file_level == level and file_distance == distance:
                        result_array[row, col] = fss
                        break
        except Exception as e:
            print(f"无法读取文件{inputdir}/{filenameii}: {e}")
        #     continue
    
    # 反转行顺序，使24时效在最下面，240在最上面
    result_array = np.flipud(result_array)
    
    return result_array, unique_initial_times

def get_filename(fig_path):
    filenlist = []
    for root,dirs,files in os.walk(fig_path):
        for file in files:
            if os.path.splitext(file)[-1].lower() == '.jpg':
                filenlist.append(file)
    return filenlist

def process_fssout(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size_str):
    status = True
    mess = []
    etime = datetime(int(etime[0:4]),int(etime[4:6]),int(etime[6:8]))
    half_size = list(map(int, half_size_str.split(',')))
    length = int(length)*24
    area_ = getregion(area)
    result_fss = {}
    with open(f"/home/user/workshop/met/met_backend/config_rain.txt", "r") as f:
        config = json.load(f)
    testdir1 = config["testdir1"]
    outpath_fss_fig = config["outpath_fss_fig"]
    fig_path = f'{outpath_fss_fig}/rain{rain_scale}/{expn}_{ref}/{cycl}/{stime}to{etime.strftime("%Y%m%d")}_{length}'

    if os.path.exists(fig_path):
        outname_list = get_filename(fig_path)
        nn = len(outname_list)

    if ((os.path.exists(fig_path)) and (nn>0)):
        print('****************  path is exists')
        outname_list = get_filename(fig_path)
        for _,filen in enumerate(outname_list):
            outname = f'{fig_path}/{filen}'
            with open(outname, "rb") as image_file:
                result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")
    elif not os.path.exists(fig_path):
        print('****************  path is not exists')
        os.makedirs(fig_path)
        outputrootfss_ii_ = os.path.join(testdir1, f'./output/gridrain/fss/data/rain{rain_scale}/{expn}_{ref}/{cycl}/')
        starttime_ = stime + cycl
        endtime_   = etime.strftime("%Y%m%d") + cycl
        
        if expn == 'KT1279':
            res = 25
        elif expn == 'NCEP':
            res = 50
        elif (expn == 'EC') or (expn == 'ECMWF'):
            res = 12.5
        if int(rain_scale)==3:
            level_list = [0.1, 3,   10, 20, 25, 30]
            distance_list   = np.array(half_size)*res
        elif int(rain_scale)==6:
            level_list = [0.1, 4, 12.5, 25, 40, 50]
            distance_list   = np.array(half_size)*res
        elif int(rain_scale)==12:
            level_list = [0.1, 5, 15,   30, 70, 140]
            distance_list   = np.array(half_size)*res
        elif int(rain_scale)==24:
            level_list = [0.1,10, 25,   50,70, 100]
            distance_list   = np.array(half_size)*res

        for _,level in enumerate(level_list):
            for ii,distance in enumerate(distance_list):
                distance = round(distance)
                result, initial_times = process_files(outputrootfss_ii_, starttime_, endtime_, level, distance, int(rain_scale), int(length))
                tlength = result.shape[1]            
                result[np.where(result<-99)] = np.nan
                outname = f'{fig_path}/FSS_pre{level}_res{distance}.jpg'
                pcolor_fss(result, initial_times, outname, rain_scale, level ,np.array(half_size)[ii])
                with open(outname, "rb") as image_file:
                    result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")

    return status,mess,result_fss


if __name__=="__main__":
    rain_scale      = '24'
    expn            = 'ECMWF'
    cycl            = '00'
    stime           = '20250519'
    etime           = '20250523'
    length          = '10'
    ref             = 'GPM'
    area            = '6'
    half_size_str   = '1,3,5,10,15'
    status,mess,result_fss = process_fssout(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size_str)