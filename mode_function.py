import pygrib
import xarray as xr
import numpy as np
from datetime import datetime
import sys
from datetime import datetime, timedelta
import meteva.base as meb
import meteva.product as mpd
import numpy as np
import pandas as pd
import meteva.method as mem
import math
import copy
import datetime
import xarray as xr
import matplotlib.pyplot as plt
import datetime
import os
import base64


plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']  # 使用文泉驿微米黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题




def calculate_future_time(time_str, hours_to_add):
    # 解析输入时间字符串
    year = int(time_str[0:4])
    month = int(time_str[4:6])
    day = int(time_str[6:8])
    hour = int(time_str[8:10])
    
    # 创建 datetime 对象
    input_time = datetime.datetime(year, month, day, hour)
    
    # 加上指定的小时数
    future_time = input_time + timedelta(hours=int(hours_to_add))
    
    # 格式化为 yyyymmddhh
    future_time_str = future_time.strftime("%Y%m%d%H")
    
    return future_time_str


def grib_2_nc(inpath, filen, outpath, indx):
    if indx == 'fcst':
        outname = f'fcst{filen[4:-4]}.nc'
        
    elif indx == 'obs':
        outname = f'obs{filen[4:-5]}.nc'
    grbs = pygrib.open(f'{inpath}/{filen}')
    try:
        grb = grbs.select(shortName='tp')[0]
    except:
        for grb in grbs:
            print(grb)
    
    values = grb.values
    lats, lons = grb.latlons()
    lat_values = np.unique(lats[:, 0])
    lon_values = np.unique(lons[0, :])
    
    member = ['member1']  # Member as object
    level = np.array([0.0], dtype='float64')  # Level as float64
    
    
    date_str = f'{filen[4:8]}/{filen[8:10]}/{filen[10:12]} {filen[12:14]}:00:00'#'2025/05/01 00:00:00'
    time = np.array([np.datetime64(date_str.replace('/', '-'), 'ns')])  # Note the array brackets
    if indx == 'fcst':
        dtime = np.array(int(filen[14:17])).astype(np.int32) # Forecast hour as int32
    elif indx == 'obs':
        dtime = np.array(int('000')).astype(np.int32) # Forecast hour as int32

    
    
    # Create DataArray with proper dimensions
    data = xr.DataArray(
        values[np.newaxis, np.newaxis, np.newaxis, np.newaxis, :, :],  # Add 4 new dimensions
        dims=('member', 'level', 'time', 'dtime', 'lat', 'lon'),
        coords={
            'member': member,
            'level': level,
            'time': time,  # Now has shape (1,)
            'dtime': np.array([dtime]),
            'lat': lat_values,
            'lon': lon_values
        },
        name='data0'
    )
    
    # Create Dataset and add attributes
    ds = xr.Dataset({'data0': data})
    ds['data0'].attrs = {
        'long_name': 'Total precipitation',
        'units': 'mm'  # or whatever units your GRIB file uses
    }
    
    # Add global attributes
    ds.attrs = {
        'source': 'GRIB file processed',
        'created': datetime.datetime.now().isoformat()
    }
    
    # Save to NetCDF
    output_file = f'{outpath}/{outname}'##f'{outpath}/{filen.replace(".grb", ".nc")}'
    ds.to_netcdf(output_file)
    print(f"Saved to {output_file}")
    
    # Close GRIB file
    grbs.close()


def get_filen(stime,cycl,expn,ref,rain_scale,fcst_delta):
    """
    stime 起报日期
    cycl  起报时刻
    expn  评估模式
    ref   参考数据
    rian_scale  降水的累计时间尺度
    fcst_delta  预报时效
    """
    config = {
        'batch': False,                 
        'conda_path': "/home/devopler/miniconda3/envs/met/bin/activate",
        'obs_path': "/home/devopler/workshop/met_backend/obs/rain",
        'python_3': "/usr/bin/python",
        'testdir1': "/home/devopler/workshop/met_backend/",
        'expn_path': "/home/devopler/workshop/met_backend/fcst/"
    }
    expn_path = config['expn_path']
    obs_path  = config['obs_path']
    obs_time = calculate_future_time(stime+cycl, fcst_delta)
    outpath = '/home/devopler/workshop/met_backend/run/tmp/mode/'
#    print('fcst data is',stime,cycl,str(fcst_delta).zfill(3))
    grib_2_nc(f'{expn_path}/{expn}/rain/rain{str(rain_scale)}', f'fcst{stime}{cycl}{str(fcst_delta).zfill(3)}.grb', outpath, 'fcst')
    grib_2_nc(f'{obs_path}/{ref}/rain{str(rain_scale).zfill(2)}/{obs_time[0:6]}',f'obs.{obs_time}.grb1' , outpath, 'obs')    
    filen_fcst = f'fcst{stime}{cycl}{str(fcst_delta).zfill(3)}.nc'
    filen_obs  = f'obs{obs_time}.nc'
    return outpath,filen_obs,filen_fcst


def rain_mode_(path_fcst,path_obs,filen_obs,filen_fcst,stime,cycl,expn,smooth,threshold,minsize,delta_hour):
    result_mode = {}
    status = True
    mess = []
    #读取观测和预报数据
    grid1 = meb.grid([50,140,0.5],[0,60,0.5])
    path_ob = f'{path_obs}/{filen_obs}'
    
    path_fo = f'{path_fcst}/{filen_fcst}'
    real_time = calculate_future_time(stime+cycl, int(delta_hour))

    grd_ob = meb.read_griddata_from_nc(path_ob, grid = grid1, time = real_time, dtime = 0, data_name = "OBS",outer_value=np.nan)
    grd_fo = meb.read_griddata_from_nc(path_fo, grid = grid1, time = stime, dtime = delta_hour, data_name = expn)

    #当smoothpar平滑次数较小时，thresh的值扩大的倍数小,小于1，如果平滑次数较大，则thresh阈值扩大了30倍左右
    look_ff = mem.mode.feature_finder(grd_ob,grd_fo,smooth = smooth,threshold = threshold,minsize = minsize)
##,save_path = '/home/devopler/workshop/met_backend/run/tmp/mode/1.png'
    print("*** 目标识别完成 ***\n")
    savepath1 = '/home/devopler/workshop/met_backend/run/tmp/mode/1.png'
    mem.mode.plot_value_and_label(look_ff, cmap = "rain_3h",clevs = np.arange(0,61,3),save_path = savepath1)
    look_match = mem.mode.centmatch(look_ff)
    print("*** 目标匹配完毕 ***\n")
    with open(savepath1, "rb") as image_file:
        result_mode['fig1'] = base64.b64encode(image_file.read()).decode("utf-8")
    plt.close()

    savepath2 = '/home/devopler/workshop/met_backend/run/tmp/mode/2.png'
    look_merge = mem.mode.merge_force(look_match)
    mem.mode.plot_label(look_merge,save_path = savepath2)
    with open(savepath1, "rb") as image_file:
        result_mode['fig2'] = base64.b64encode(image_file.read()).decode("utf-8")
    plt.close()
    #对于匹配未匹配的目标以统一以灰色显示，匹配的目标则以彩色显示，左右两侧相同颜色的目标是一对匹配的目标

    # interest = mem.mode.interester(look_merge)
    # print("*** 相似度计算完毕 ***\n")
    # mem.mode.plot_interest(interest)

    features = mem.mode.feature_merged_analyzer(look_merge)
    # print(features)
    savepath3 = '/home/devopler/workshop/met_backend/run/tmp/mode/3.png'
    mem.mode.plot_feature(features,save_path = savepath3,show = False)
    plt.close()

    with open(savepath3, "rb") as image_file:
        result_mode['fig3'] = base64.b64encode(image_file.read()).decode("utf-8")

    return status,mess,result_mode


def run_main_mode_(stime,cycl,expn,ref,rain_scale,fcst_delta,area,smooth,threshold,minsize):

    config = {
        'conda_path': "/home/devopler/miniconda3/envs/met/bin/activate",
        'cdo': "/home/devopler/miniconda3/envs/met/bin/cdo",
        'wgrib': "/home/devopler/workshop/met_backend/wgrib/wgrib",
        'obs_path': "/home/devopler/workshop/met_backend/obs/rain/",
        'python_3': "/usr/bin/python",
        'expn_path': "/home/devopler/workshop/met_backend/obs/rain/fcst/"
    }
    cmd = 'source /home/devopler/miniconda3/envs/met/bin/activate'
    os.system(cmd)

    outpath,filen_obs,filen_fcst = get_filen(stime,cycl,expn,ref,rain_scale,fcst_delta)
    status,mess,result_mode = rain_mode_(outpath,outpath,filen_obs,filen_fcst,stime,cycl,expn,smooth,threshold,minsize,fcst_delta)
    return status,mess,result_mode
    

    








