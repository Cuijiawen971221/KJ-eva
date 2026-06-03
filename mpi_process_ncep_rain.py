import os
import glob
from datetime import datetime, timedelta
import pygrib
import numpy as np
import pandas as pd
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


def calculate_accumulated_precip(input_dir, output_dir, accumulation_hours, ymdh):
    """
    计算累计降水数据
    
    参数:
        input_dir: 输入目录路径(rain3/)
        output_dir: 输出目录路径(rain6/, rain12/, rain24/)
        accumulation_hours: 累计小时数(6,12,24)
    """
    # 确保输出目录存在
    print(input_dir, output_dir, accumulation_hours)
    if not os.path.exists(output_dir):
        print('no path!!!!')
        os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有起报时间文件
    tmp_info = f'fcst{ymdh}*.grb'
    all_files = sorted(glob.glob(os.path.join(input_dir, tmp_info)))
    
    # 按起报时间分组
    forecast_groups = {}
    for file in all_files:
        basename = os.path.basename(file)
        # 提取起报时间部分(YYYYMMDDHH)
        forecast_time = basename[4:14]
        if forecast_time not in forecast_groups:
            forecast_groups[forecast_time] = []
        forecast_groups[forecast_time].append(file)
    
    # 处理每个起报时间组
    for forecast_time, file_list in forecast_groups.items():
        # 按预报时效排序
        file_list.sort(key=lambda x: int(os.path.basename(x)[14:17]))
        
        # 根据累计小时数确定计算方式
        if accumulation_hours == 6:
            calculate_rain6(file_list, output_dir, forecast_time)

                
        elif accumulation_hours == 12:
            calculate_rain12(file_list, output_dir, forecast_time)

            
        elif accumulation_hours == 24:
            calculate_rain24(file_list, output_dir, forecast_time)


def calculate_rain6(file_list, output_dir, forecast_time):
    """计算6小时累计降水"""
    # 每2个文件一组(003+006, 009+012, ...)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    try:
        for i in range(0, len(file_list)-1, 2):
            file1 = file_list[i]
            file2 = file_list[i+1]
        
            # 检查文件时效是否连续
            iii1 = int(os.path.basename(file1)[14:17])
            iii2 = int(os.path.basename(file2)[14:17])
            if iii2 != iii1 + 3:
                continue  # 不连续则跳过
            
            # 读取两个文件的数据
            grb1 = pygrib.open(file1)
            grb2 = pygrib.open(file2)
        
            # 假设只有一个消息(通常是这样的)
            msg1 = grb1.select(shortName = 'prate')[0]
            msg2 = grb2.select(shortName = 'prate')[0]
        
            # 获取降水数据并相加
            data1 = msg1.values
            data2 = msg2.values
            accumulated_data = data1 + data2
        
            # 创建新的grib消息
            new_msg = msg1
            new_msg.values = accumulated_data
        
            # 确定输出文件名(使用第二个文件的时效)
            output_iii = f"{iii2:03d}"
            output_filename = f"fcst{forecast_time}{output_iii}.grb"
            output_path = os.path.join(output_dir, output_filename)
            

            # 写入新文件
            with open(output_path, 'wb') as outfile:
                outfile.write(new_msg.tostring())

            grb1.close()
            grb2.close()
    except:
        print('error')

def calculate_rain12(file_list, output_dir, forecast_time):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    """计算12小时累计降水"""
    # 根据起报时间的小时部分确定计算方式
    hh = int(forecast_time[8:10])
    
    if hh == 0 or hh == 12:
        # 00和12起报: [03+06+09+12], [15+18+21+24], ...
        groups = [(3,6,9,12), (15,18,21,24), (27,30,33,36), 
                 (39,42,45,48), (51,54,57,60), (63,66,69,72),
                 (75,78,81,84), (87,90,93,96), (99,102,105,108),
                 (111,114,117,120), (123,126,129,132), (135,138,141,144),
                 (147,150,153,156), (159,162,165,168), (171,174,177,180),
                 (183,186,189,192), (195,198,201,204), (207,210,213,216),
                 (219,222,225,228), (231,234,237,240)]
    else:
        # 06和18起报: [09+12+15+18], [21+24+27+30], ...
        groups = [(9,12,15,18), (21,24,27,30), (33,36,39,42),
                 (45,48,51,54), (57,60,63,66), (69,72,75,78),
                 (81,84,87,90), (93,96,99,102), (105,108,111,114),
                 (117,120,123,126), (129,132,135,138), (141,144,147,150),
                 (153,156,159,162), (165,168,171,174), (177,180,183,186),
                 (189,192,195,198), (201,204,207,210), (213,216,219,222),
                 (225,228,231,234)]
    
    # 创建文件映射(时效->文件路径)
    iii_to_file = {}
    for file in file_list:
        iii = int(os.path.basename(file)[14:17])
        iii_to_file[iii] = file
    
    # 处理每个组
    for group in groups:
        # 检查是否所有需要的文件都存在
        if all(iii in iii_to_file for iii in group):
            # 读取并累加所有文件的数据
            accumulated_data = None
            first_msg = None
            
            for iii in group:
                file = iii_to_file[iii]
                grb = pygrib.open(file)
                msg = grb.select(shortName = 'prate')[0]
                
                if accumulated_data is None:
                    accumulated_data = msg.values
                    first_msg = msg
                else:
                    accumulated_data += msg.values
                
                grb.close()
            
            # 创建新的grib消息
            if first_msg is not None:
                new_msg = first_msg
                new_msg.values = accumulated_data
                
                # 使用组中最后一个时效作为输出文件名
                output_iii          = f"{group[-1]:03d}"
                output_filename     = f"fcst{forecast_time}{output_iii}.grb"
                output_path         = os.path.join(output_dir, output_filename)
                
                # 写入新文件
                with open(output_path, 'wb') as outfile:
                    outfile.write(new_msg.tostring())



def calculate_rain24(file_list, output_dir, forecast_time):
    """计算24小时累计降水"""
    # 根据起报时间的小时部分确定计算方式
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    hh = int(forecast_time[8:10])
    
    if hh == 0:
        # 00起报: [03+06+09+12+15+18+21+24], [27+30+...+48], ...
        groups = [(3,6,9,12,15,18,21,24), (27,30,33,36,39,42,45,48),
                 (51,54,57,60,63,66,69,72), (75,78,81,84,87,90,93,96),
                 (99,102,105,108,111,114,117,120), (123,126,129,132,135,138,141,144),
                 (147,150,153,156,159,162,165,168), (171,174,177,180,183,186,189,192),
                 (195,198,201,204,207,210,213,216), (219,222,225,228,231,234,237,240)]
    elif hh == 6:
        # 06起报: [21+24+27+30+33+36+39+42], [45+48+...+66], ...
        groups = [(21,24,27,30,33,36,39,42), (45,48,51,54,57,60,63,66),
                 (69,72,75,78,81,84,87,90), (93,96,99,102,105,108,111,114),
                 (117,120,123,126,129,132,135,138), (141,144,147,150,153,156,159,162),
                 (165,168,171,174,177,180,183,186), (189,192,195,198,201,204,207,210),
                 (213,216,219,222,225,228,231,234)]
    elif hh == 12:
        # 12起报: [03+06+...+24], [27+30+...+48], ... (同00起报)
        groups = [(15, 18,  21,  24,  27,  30,  33,  36),  
                 (39,  42,  45,  48,  51,  54,  57,  60), 
                 (63,  66,  69,  72,  75,  78,  81,  84), 
                 (87,   90,  93,  96,  99, 102, 105, 108),
                 (111, 114, 117, 120, 123, 126, 129, 132),
                 (135, 138, 141, 144, 147, 150, 153, 156), 
                 (159, 162, 165, 168, 171, 174, 177, 180), 
                 (183, 186, 189, 192, 195, 198, 201, 204),
                 (207, 210, 213, 216, 219, 222, 225, 228)]
    else:  # hh == 18
        # 18起报: [09+12+...+30], [33+36+...+54], ...
        groups = [(9,12,15,18,21,24,27,30), 
                 (33,36,39,42,45,48,51,54),
                 (57,60,63,66,69,72,75,78), 
                 (81,84,87,90,93,96,99,102),
                 (105,108,111,114,117,120,123,126), 
                 (129,132,135,138,141,144,147,150),
                 (153,156,159,162,165,168,171,174), 
                 (177,180,183,186,189,192,195,198),
                 (201,204,207,210,213,216,219,222)]
    
    # 创建文件映射(时效->文件路径)
    iii_to_file = {}
    for file in file_list:
        iii = int(os.path.basename(file)[14:17])
        iii_to_file[iii] = file
    
    # 处理每个组
    for group in groups:
        # 检查是否所有需要的文件都存在
        if all(iii in iii_to_file for iii in group):
            # 读取并累加所有文件的数据
            accumulated_data = None
            first_msg = None
            
            for iii in group:
                file = iii_to_file[iii]
                grb = pygrib.open(file)
                msg = grb.select(shortName = 'prate')[0]
                
                if accumulated_data is None:
                    accumulated_data = msg.values
                    first_msg = msg
                else:
                    accumulated_data += msg.values
                
                grb.close()
            
            # 创建新的grib消息
            if first_msg is not None:
                new_msg = first_msg
                new_msg.values = accumulated_data
                
                # 使用组中最后一个时效作为输出文件名
                output_iii = f"{group[-1]:03d}"
                output_filename = f"fcst{forecast_time}{output_iii}.grb"
                output_path = os.path.join(output_dir, output_filename)

                # 写入新文件
                with open(output_path, 'wb') as outfile:
                    outfile.write(new_msg.tostring())
   

def date_list_process(time_start, time_end):
    start_date = datetime.strptime(time_start, "%Y%m%d")
    end_date = datetime.strptime(time_end, "%Y%m%d")
    current_date = start_date
    time_list = []
    while current_date <= end_date:
        time_list.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    return time_list


def choose_file(inpath, file_info):
    fn_info = f'*{file_info}'
    matching_files = glob.glob(os.path.join(inpath, fn_info))
    if len(matching_files) > 0:
        indx = True
        for file_path in matching_files:
            filen = (os.path.basename(file_path))
    else:
        indx = False
        filen = None
    return filen, indx


def read_ncep_3h(inpath, timei, stfc_time, outpath):
    """
    inparg:r          ootdir
    timei:            yyyymmdd
    stfc_time:        start fcst time:00 06 12 18
    fc_len:           length of fcst
    """

    for ii in range(3, 241, 3):
        file_info = f'_P_gfs.t{str(stfc_time).zfill(2)}z.pgrb2.0p50.f{str(ii).zfill(3)}.bin'
        inpath_i = f'{inpath}/{timei}'
        filen, indx = choose_file(inpath_i, file_info)
        #print(filen)
        if indx and (int(filen[22:24]) > int(filen[36:38])):
            grbs = pygrib.open(f'{inpath_i}/{filen}')
            #print(filen)
            try:
            #if 1==1:
                #print('======>', f'{inpath_i}/{filen}')
                ds = pygrib.open(f'{inpath_i}/{filen}')
                grbi = ds.select(shortName='tp')

                if len(grbi) > 1:
                    tp = grbi[0]
                else:
                    tp = grbi
                # write into grb
                outname = f'{outpath}/fcst{timei}{str(stfc_time).zfill(2)}{str(ii).zfill(3)}.grb'
                outname_new = f'{outpath}/fcst{timei}{str(stfc_time).zfill(2)}{str(ii).zfill(3)}.grb1'
                # 写入新文件
                with open(outname_new, 'wb') as outfile:
                    outfile.write(tp.tostring())
                pynio_data = xr.open_dataset(outname_new,engine = 'cfgrib',indexpath= '')
                data_tmp   = dataset_to_grib(pynio_data, {"tp":"tp"}, Grib2KeyDict, Pscale=1.0)
                xarray_to_grib.to_grib(data_tmp,outname)
                os.remove(outname_new)

            except:
                print('no data')
        else:
            print('choose data failed!!!')

def run_main(start_time, end_time, length, inpath, outpath, model_n, stfc_timelist, mess_path, hri):
    outpath_03 = f'{outpath}/rain03'
    if not os.path.exists(outpath_03):
        os.makedirs(outpath_03)

    time_list = date_list_process(start_time, end_time)
    for _, timei in enumerate(time_list):
        for _, stfc_time in enumerate(stfc_timelist):
            read_ncep_3h(inpath, timei, stfc_time, outpath_03)

    rain3_dir = outpath_03
    # 计算rain6
    rain6_dir = f"{outpath}/rain06/"
    
    st_ymdh = start_time+hri
    calculate_accumulated_precip(rain3_dir, rain6_dir, 6, st_ymdh)
    
    # 计算rain12
    rain12_dir = f"{outpath}/rain12/"
    calculate_accumulated_precip(rain3_dir, rain12_dir, 12, st_ymdh)
    
    # 计算rain24
    rain24_dir = f"{outpath}/rain24/"
    calculate_accumulated_precip(rain3_dir, rain24_dir, 24, st_ymdh)

    if hri == '00':
        check_filen = f'{rain24_dir}/fcst{start_time}240.grb'
    elif hri == '12':
        check_filen = f'{rain24_dir}/fcst{start_time}228.grb'
    ## 计算完成后检查是否生成240h累计降水
    if os.path.exists(check_filen):
        successmess = f'{mess_path}/NCEP/{start_time}/rain24_NCEP_{start_time}.ok'
        with open(successmess, "w") as f:
            pass

        retrynextmess = f'{mess_path}/NCEP/{start_time}/rain24_NCEP_{start_time}.retry'
        if os.path.exists(retrynextmess):
            os.remove(retrynextmess)


def run_main_process_rain(model_n,length,inpath,outpath,mess_path,timenow):
    if int(timenow[8:10])<12:
        hour_in = '00'
        start_time     = f'{timenow[0:8]}{hour_in}'
        end_time       = f'{timenow[0:8]}{hour_in}'
        stfc_timelist1 = [0]
        check_info1    = f'{outpath}/rain24/fcst{start_time}240.grb'
        
        stfc_timelist2 = [12]
        current_time   = datetime.strptime(start_time, "%Y%m%d%H")
        # check_time     = (current_time - timedelta(hours=12)).strftime("%Y%m%d%H")
        # check_info2    = f'{outpath}/rain24/fcst{check_time}228.grb'
    else:
        hour_in = '12'
        start_time     = f'{timenow[0:8]}{hour_in}'
        end_time       = f'{timenow[0:8]}{hour_in}'
        stfc_timelist1 = [12]
        check_info1    = f'{outpath}/rain24/fcst{start_time}228.grb'
        stfc_timelist2 = [0]
        current_time   = datetime.strptime(start_time, "%Y%m%d%H")


        
    mess_path_i   = f'{mess_path}/NCEP/{start_time[0:8]}/'
    if not os.path.exists(mess_path_i):
        os.makedirs(mess_path_i)
        
    retrynextmess = f'{mess_path}/NCEP/{start_time[0:8]}/rain24_NCEP_{start_time}.retry'
    if not os.path.exists(check_info1):
        ####
        ## 写入retry
        print('***** 002',retrynextmess)
        with open(retrynextmess,"w") as f:
            pass
        ####
        print('不存在文件，开始执行计算',start_time)         
        run_main(start_time[0:8], end_time[0:8], length, inpath, outpath, model_n, stfc_timelist1,mess_path,start_time[8:10])
    else:
        #### 已经存在
        ## double check
        if os.path.exists(retrynextmess):
            os.remove(retrynextmess)
        print('retry文件存在，跳出')
    #################################################################

    for ii in range(1,9):
        check_time     = (current_time - timedelta(hours=12*ii)).strftime("%Y%m%d%H")
        
        if int(check_time[8:10]) == 0:
            check_info2 = f'{outpath}/rain24/fcst{check_time}240.grb'
        else:
            check_info2 = f'{outpath}/rain24/fcst{check_time}228.grb'
        retrynextmess = f'{mess_path}/NCEP/{check_time[0:8]}/rain24_NCEP_{check_time}.retry'
        if not os.path.exists(check_info2):
            print(f'==>{str(ii)}-{check_info2} no exist!!!!')
            with open(retrynextmess,"w") as f:
                pass
            print('不存在文件，开始执行计算',check_time)
            run_main(check_time[0:8], check_time[0:8], length, inpath, outpath, model_n, stfc_timelist2, mess_path, check_time[8:10])
        else:
            
            if os.path.exists(retrynextmess):
                os.remove(retrynextmess)
            final_ok_mess = f'{mess_path}/NCEP/{check_time[0:8]}/rain24_NCEP_{check_time}.ok'
            if not os.path.exists(final_ok_mess):
                print(final_ok_mess)
                with open(final_ok_mess,"w") as f:
                    pass
            print('01文件存在，跳出')



if __name__ == "__main__":
    # 示例用法
    conf       = cf.pparms("./pathconfig.yaml").param
    model_n    = 'NCEP'
    length     = 240
    inpath     = conf.ncepfcstpath + '/' + model_n
    outpath    = conf.ncepoutputpath  + '/' + model_n + '/rain'
    mess_path  = conf.message_rain 
    print('****** 000')
    timenow    = (datetime.now() - timedelta(hours=8)).strftime("%Y%m%d%H")
    print('****** 001',timenow)
    run_main_process_rain(model_n,length,inpath,outpath,mess_path,timenow)



