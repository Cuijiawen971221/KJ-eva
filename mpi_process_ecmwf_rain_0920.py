import os
import pygrib
import numpy as np
from datetime import datetime, timedelta
import sys
import config as cf
import grid_proc
from pydantic import BaseModel
from  main  import quyu_grid,airport_interp_single,airport_interp,Plev,dimian_single,gaokong_single
import asyncio
import sys
import yunyao_met
from clickhouse_util import clickclient
import glob
import xarray as xr
from pynio_split import dataset_to_grib
from grib_dict import Grib2KeyDict
from cfgrib import xarray_to_grib

def check_data(time_str,mess_path):
    """
    time_str = yyyymmdd
    """
    mess_file   = f'{mess_path}/ECMWF/{time_str[0:8]}/rain24_ECMWF_{time_str}.ok'
    print('检查文件:',mess_file)
    if os.path.exists(mess_file):
        indx = True
    else:
        indx = False
    return indx

def calculate_accum_rain(valid_hours,precip_data,cycl):

    precip_accum = {'3h': {}, '6h': {}, '12h': {}, '24h': {}}

    for hours in sorted(h for h in valid_hours if h <= 72):
        ## 3h rain
        if hours==3:
            precip_accum['3h'][hours] = precip_data[hours]
        elif hours>3  and ((hours-3) in valid_hours) :
            precip_accum['3h'][hours] = precip_data[hours] - precip_data[hours-3]
        ## 6h rain
        if hours % 6 == 0:# and (hours-3) in valid_hours:
            if hours==6:
                precip_accum['6h'][hours] = precip_data[hours]
            elif hours>6 and ((hours-6) in valid_hours) :
                precip_accum['6h'][hours] = precip_data[hours] - precip_data[hours-6]
        ## 12h rain
        if hours % 12 == 0 and (hours-12) in valid_hours:
            if hours == 12:
                precip_accum['12h'][hours] = precip_data[hours]
            elif  hours> 12 and ((hours-12) in valid_hours) :
                precip_accum['12h'][hours] = precip_data[hours] - precip_data[hours-12]
        
        ## 24h rain
        if cycl == '12' and hours % 24 == 12:
            if hours >= 36  and ((hours-24) in valid_hours) :
                precip_accum['24h'][hours] = precip_data[hours] - precip_data[hours-24]
        elif cycl == '00' and hours % 24 ==0:
            if hours == 24:
                precip_accum['24h'][hours] = precip_data[hours]
            elif hours>24 and ((hours-24) in valid_hours) :
                precip_accum['24h'][hours] = precip_data[hours] - precip_data[hours - 24]
    for hours in sorted(h for h in valid_hours if h > 72):

        ## 6h rain
        if hours % 6 == 0 :
            precip_accum['6h'][hours] = precip_data[hours]

        ## 12h rain
        if hours % 12 == 0:
            if hours == 12:
                precip_accum['12h'][hours] = precip_data[hours]
            elif hours>12 and (hours-12 in valid_hours):
                precip_accum['12h'][hours] = precip_data[hours] - precip_data[hours-12]
        if cycl == '00' and hours % 24 == 0:
            if hours ==24:
                precip_accum['24h'][hours] = precip_data[hours]
            elif hours>24 and (hours-24 in valid_hours):
                precip_accum['24h'][hours] = precip_data[hours] - precip_data[hours-24]

        elif cycl == '12' and hours % 24 == 12:
            if hours >= 36 and (hours-24 in valid_hours):
                precip_accum['24h'][hours] = precip_data[hours] - precip_data[hours-24]
    return precip_accum

def save_result(precip_accum,outpath,folder_name,example_n,mess_path_i):
    for accum_type in ['3h', '6h', '12h', '24h']:
    # 输出目录：rain03、rain06、rain12、rain24
        output_dir = os.path.join(outpath, f'rain{accum_type[:-1].zfill(2)}')
        os.makedirs(output_dir, exist_ok=True)

        for hours, data in precip_accum[accum_type].items():
            # 输出文件名格式：fcst+起报时间+预报时效.grb（如fcst2024050100024.grb）
            output_filename = f"fcst{folder_name}{str(hours).zfill(3)}.grb1"
            output_newname  = f"fcst{folder_name}{str(hours).zfill(3)}.grb"
            output_path1    = os.path.join(output_dir, output_filename)
            output_path2    = os.path.join(output_dir, output_newname)
            # 基于示例GRIB文件的格式保存（复用投影、参数等元信息）
            ## 参考陈光灿 CGC
            ##
            try:
                with pygrib.open(example_n) as grbs_e:
                    example_grib = grbs_e.select(shortName='tp')[0]
                    # 替换数据值，保留其他元信息
                    msg = example_grib
                    data[data<0] = 0
                    msg.values = data
                    # print('写入文件:',output_path)
                    with open(output_path1, 'wb') as out:
                        out.write(msg.tostring())
                print(f"Saved {output_path1}")
                # pynio_data = xr.open_dataset(output_path1, engine="pynio")  #
                ##
                pynio_data = xr.open_dataset(output_path1,engine = 'cfgrib',indexpath= '')
                data_tmp   = dataset_to_grib(pynio_data, {"tp":"tp"}, Grib2KeyDict, Pscale=1.0)
                xarray_to_grib.to_grib(data_tmp,output_path2)
                os.remove(output_path1)

            except Exception as e:
                print(f"Error writing {output_path}: {e}")
                continue
    if int(folder_name[8:10])==12:
        check_info = f'{output_dir}/fcst{folder_name}228.grb'
    elif int(folder_name[8:10])==0:
        check_info = f'{output_dir}/fcst{folder_name}240.grb'
    if os.path.exists(check_info):
        indx_save = True
    else:
        indx_save = False
                  
    if indx_save:                     
        successmess = f'{mess_path_i}/ECMWF/{folder_name[0:8]}/rain24_ECMWF_{start_time}.ok'
        with open(successmess,"w") as f:
            pass
        try:
            retrynextmess = f'{mess_path_i}/ECMWF/{folder_name[0:8]}/rain24_ECMWF_{start_time}.retry'
            os.remove(retrynextmess)
        except:
            print('no mess!')
    else:
        retrynextmess = f'{mess_path_i}/ECMWF/{folder_name[0:8]}/rain24_ECMWF_{start_time}.retry'
        with open(retrynextmess,"w") as f:
            pass

def process_ecmwf_precip(input_dir, start_time, end_time, outpath,mess_path,example_n):
    for folder in ['rain03', 'rain06', 'rain12', 'rain24']:
        os.makedirs(os.path.join(outpath, folder), exist_ok=True)
    current_time = datetime.strptime(start_time, "%Y%m%d%H")
    end_time     = datetime.strptime(end_time, "%Y%m%d%H")
    
    while current_time <= end_time:
        folder_name = current_time.strftime("%Y%m%d%H")
        folder_path = os.path.join(input_dir, folder_name)
        
        if not os.path.exists(folder_path):
            current_time += timedelta(hours=12)
            continue
        
        print(f"Processing forecast from {folder_name}")
        precip_data = {}  #
        valid_hours = set()  #
        
        for filename in sorted(os.listdir(folder_path)):
            if filename.startswith('W_NAFP_C_ECMF_') and len(filename)==51:
            
                forecast_info = filename.split('_')[-1]
                ##print('预报信息--->',forecast_info)
                forecast_hour = folder_name[0:4] + forecast_info[11:17]  # YYYYMMDD
                forecast_hh = forecast_info[15:17]  # HH


                forecast_date  = datetime.strptime(forecast_hour, "%Y%m%d%H")
                init_date      = datetime.strptime(folder_name, "%Y%m%d%H")
                forecast_delta = forecast_date - init_date                          ## 预报时间-起报时间
                print('fcst=',forecast_date, '  init time=',init_date, '  dt=',forecast_date - init_date)
                forecast_hours = round(forecast_delta.total_seconds()/3600)         ## 预报时效
                print('delta time-->',forecast_hours)

                if forecast_hours > 240:
                    continue

                # 读取数据
                filepath = f'{folder_path}/{filename}'
                try:
                    grbs = pygrib.open(filepath)
                    precip_msg_1 = grbs.select(shortName='tp')[0]
                    precip_msg   = precip_msg_1
                    rain_ = precip_msg.values
                    rain_[np.where(rain_<0.000001)] = 0

                    if precip_msg.units == 'm':
                        rain_ = 1000 * rain_
                    else:
                        rain_ = rain_
                    precip_data[forecast_hours] = rain_
                    valid_hours.add(forecast_hours)
                    grbs.close()
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue
        print('输入参数：',folder_name,valid_hours)

        precip_accum = calculate_accum_rain(valid_hours,precip_data,folder_name[8:10])
        save_result(precip_accum,outpath,folder_name,example_n,mess_path)
        current_time += timedelta(hours=12)

    mess   = 'success'
    status = True
    return mess,status




if __name__ == "__main__":
    conf = cf.pparms("./pathconfig.yaml").param
    model_n         = 'ECMWF'
    input_directory = conf.ecmwffcstpath + '/' + model_n
    outpath1        = conf.ecmwfoutputpath + '/' + model_n + '/rain/'      
    example_n       = conf.ecmwf_example         
    mess_path       = conf.message_rain
    
    timenow = sys.argv[1] #(datetime.now() - timedelta(hours=8)).strftime("%Y%m%d%H")
    
    if int(timenow[8:10])<12:
        hour_in = '00'
    else:
        hour_in = '12'
    
    
    start_time   = f'{timenow[0:8]}{hour_in}'
    end_time     = f'{timenow[0:8]}{hour_in}'
    print(start_time)
    current_time = datetime.strptime(start_time, "%Y%m%d%H")                   ## now time
    check_time   = (current_time - timedelta(hours=12)).strftime("%Y%m%d%H")   ## now time - 12hours
    #(1) check mess_path exists???    
    if not os.path.exists(f'{mess_path}/ECMWF/{start_time[0:8]}'):
        os.makedirs(f'{mess_path}/ECMWF/{start_time[0:8]}')
    if not os.path.exists(f'{mess_path}/ECMWF/{check_time[0:8]}'):
        os.makedirs(f'{mess_path}/ECMWF/{check_time[0:8]}')
   
    #(2) 检查当前时刻
    indx1 = check_data(start_time,mess_path)
    retrynextmess = f'{mess_path}/ECMWF/{start_time[0:8]}/rain24_ECMWF_{start_time}.retry'
    if not indx1:## ok文件不存在
        with open(retrynextmess,"w") as f:
            pass
        mees,status = process_ecmwf_precip(input_directory, start_time, end_time, outpath1, mess_path, example_n)
    else:
        print('存在文件')

    ## 检查前一时刻
    indx2 = check_data(check_time,mess_path)
    retrynextmess = f'{mess_path}/ECMWF/{check_time[0:8]}/rain24_ECMWF_{check_time}.retry'
    if not indx2:
        with open(retrynextmess,"w") as f:
            pass
        mees,status = process_ecmwf_precip(input_directory, check_time, check_time, outpath1, mess_path, example_n)
