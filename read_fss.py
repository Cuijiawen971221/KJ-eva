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


plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']  # 使用文泉驿微米黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def pcolor_fss(data, times, outname, rain_scale,level ,distance):
    fig, ax = plt.subplots(figsize=(12, 8))
    # data = np.flipud(data)
    # 创建分段的colormap (rainbow, 10级)
    cmap = plt.get_cmap('rainbow')
    bounds = np.linspace(0, 1, 11)  # 10级
    norm = colors.BoundaryNorm(bounds, cmap.N)
    
    # 绘制热图
    im = ax.matshow(data, cmap=cmap, norm=norm, aspect='auto')
    
    # 设置标题和标签
    ax.set_title(f"FSS随时间和时效变化 降水>={level}mm  窗口:{int(distance)/50}", fontsize=14, pad=20)
    ax.set_xlabel("起报时间", fontsize=12, labelpad=10)
    ax.set_ylabel("预报时效", fontsize=12, labelpad=10)
    
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
    
    # 创建colorbar（10级）
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.2)
    cbar = plt.colorbar(im, cax=cax, ticks=np.linspace(0.05, 0.95, 10))
    cbar.set_label("FSS", rotation=270, labelpad=20, fontsize=12)
    
    # 添加网格线
    ax.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    
    plt.tight_layout()
    # plt.show()
    plt.savefig(outname)
    # plt.close()


def pcolor_fss_all(data, expn, outname, level, distance):
    fig, ax = plt.subplots(figsize=(12, 8))

    # 创建分段的colormap (rainbow, 10级)
    cmap = plt.get_cmap('rainbow')
    bounds = (np.linspace(0.12, 0.72, 11))  # 10级
    norm = colors.BoundaryNorm(bounds, cmap.N)

    # 绘制热图
    im = ax.matshow(np.flipud(data), cmap=cmap, norm=norm, aspect='auto')

    # 设置标题和标签
    ax.set_title(f"{expn}", fontsize=14, pad=20)
    ax.set_xlabel("grade", fontsize=12, labelpad=10)
    ax.set_ylabel("half_window_size", fontsize=12, labelpad=10)
    # 设置y轴刻度（从下往上24,48,...,240）
    ax.set_yticks(np.arange(len(distance)))
    ax.set_yticklabels(distance[::-1])  # 反转顺序
    ax.set_xticks(np.arange(len(level)))
    ax.set_xticklabels(level)  # 反转顺序
    # 创建colorbar（10级）
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.2)
    cbar = plt.colorbar(im, cax=cax, ticks=(np.linspace(0.12, 0.72, 11)))
    cbar.set_label("FSS", rotation=270, labelpad=20, fontsize=12)
    # 添加网格线
    ax.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outname)
    
def process_files(inputdir, starttime, endtime, level, distance, rain_scale, length):

    # 将时间字符串转换为datetime对象用于比较
    start_dt = datetime.strptime(starttime, "%Y%m%d%H")
    end_dt = datetime.strptime(endtime, "%Y%m%d%H")
    # 定义所有可能的时效值（24到240，步长24）
    lead_times = list(range(rain_scale, length+1, rain_scale))  # [24, 48, 72, ..., 240]
    
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
        try:
            # 从文件名提取时效和验证时间
            match = re.match(r'fss(\d+)\.(\d{10})', filename)
            lead_time = int(match.group(1))
            valid_time_str = match.group(2)
            valid_dt = datetime.strptime(valid_time_str, "%Y%m%d%H")
            
            # 计算起报时间 = 验证时间 - 时效
            initial_dt = valid_dt - timedelta(hours=lead_time)
            initial_time_str = initial_dt.strftime("%Y%m%d%H")

            if start_dt <= valid_dt <= end_dt:
                valid_files.append(f'{filename}')
                initial_timelist.append(initial_time_str)

        except Exception as e:
            print(f"处理文件{filename}时出错: {e}")
            continue
    
    # 收集所有唯一的起报时间并排序
    unique_initial_times = sorted(list(set([t for t in initial_timelist])))

    
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
            # 读取文件内容
            with open(f'{inputdir}/{filenameii}', 'r') as f:
                lines = f.readlines()
            # 查找匹配level和distance的数据
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
            continue
    
    # 反转行顺序，使24时效在最下面，240在最上面
    result_array = np.flipud(result_array)
    
    return result_array, unique_initial_times


def process_files_all(inputdir, starttime, endtime, level, distance, rain_scale, length):
    # 将时间字符串转换为datetime对象用于比较
    start_dt = datetime.strptime(starttime, "%Y%m%d%H")
    end_dt = datetime.strptime(endtime, "%Y%m%d%H")
    # 定义所有可能的时效值（24到240，步长24）
    lead_times = list(range(rain_scale, length + 1, rain_scale))  # [24, 48, 72, ..., 240]

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
        try:
            # 从文件名提取时效和验证时间
            match = re.match(r'fss(\d+)\.(\d{10})', filename)
            lead_time = int(match.group(1))
            valid_time_str = match.group(2)
            valid_dt = datetime.strptime(valid_time_str, "%Y%m%d%H")

            # 计算起报时间 = 验证时间 - 时效
            initial_dt = valid_dt - timedelta(hours=lead_time)
            initial_time_str = initial_dt.strftime("%Y%m%d%H")

            if start_dt <= valid_dt <= end_dt:
                valid_files.append(f'{filename}')
                initial_timelist.append(initial_time_str)

        except Exception as e:
            print(f"处理文件{filename}时出错: {e}")
            continue

    # 收集所有唯一的起报时间并排序
    unique_initial_times = sorted(list(set([t for t in initial_timelist])))

    # 初始化结果数组：行是时效，列是起报时间
    result_array = np.full((len(lead_times), len(unique_initial_times)), np.nan)
    # 创建起报时间到列索引的映射
    initial_to_col = {time: idx for idx, time in enumerate(unique_initial_times)}

    # 创建时效到行索引的映射（从24到240）
    lead_to_row = {lead: idx for idx, lead in enumerate(sorted(lead_times))}

    # 处理每个文件
    for ii, filenameii in enumerate(valid_files):
        lead_time = int(filenameii[3:6].lstrip('0'))
        initial_time = initial_timelist[ii]
        row = lead_to_row[lead_time]
        col = initial_to_col[initial_time]

        try:
            # 读取文件内容
            with open(f'{inputdir}/{filenameii}', 'r') as f:
                lines = f.readlines()
            # 查找匹配level和distance的数据
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
            continue

    # 反转行顺序，使24时效在最下面，240在最上面
    result_array = np.flipud(result_array)

    return result_array, unique_initial_times
# # 使用示例
# inputdir = r"E:/云遥有关文档/FSS_rain/rain24/"
# starttime = "2025051000"
# endtime = "2025051500"
# level = 0.1
# distance = 450
# result, initial_times = process_files(inputdir, starttime, endtime, level, distance)
# outname = f'{outpath}/{starttime}to{endtime}_{level}-{distance}km_FSS.jpg'
# pcolor_fss(result, initial_times,outname)