import numpy as np  
import os
import pygrib
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
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

def fcst_time_list(dt,length):
    """
    calculate --> fxxx  
    """
    list_ = []
    for ii in range(dt,length+1,dt):
        list_.append(str(ii).zfill(3))
    return list_

def check_file_exists(outpath_i,datei,timescale_i,hr_i):
    """
    判断当前操作的目标文件是否存在？
    """
    if hr_i == '12':
        if timescale_i == 3:
            filename = f'{outpath_i}/fcst{datei}12120.grb'
        elif timescale_i == 6 or timescale_i == 12:
            filename = f'{outpath_i}/fcst{datei}12240.grb'
        elif timescale_i == 24:
            filename = f'{outpath_i}/fcst{datei}12228.grb'
        
    else:
        if timescale_i == 3:
            filename = f'{outpath_i}/fcst{datei}00120.grb'
        else:
            filename = f'{outpath_i}/fcst{datei}00240.grb'
    
    if os.path.exists(filename):
        indx_f = True
    else:
        indx_f = False
    
    return indx_f


def process_KT_rain_grid(inpath:str,outpath:str,time_start:str,time_end:str,mess_path:str)->tuple:
    timescale  = [3,6,12,24]
    fcst_hr    = ['00','12']
    length     = 240
    start_date = datetime.strptime(time_start,"%Y%m%d")
    end_date   = datetime.strptime(time_end,"%Y%m%d")
    current_date = start_date
    time_list = []
    
    while current_date<=end_date:
        time_list.append(current_date.strftime("%Y%m%d"))
        current_date+=timedelta(days=1)
    status = True
    ## fcst_hr: 3,6,12,24
    mess = []
    for _,timescale_i in enumerate(timescale):               ## 3,6,12,24
        if timescale_i==3:
            ff_list = fcst_time_list(timescale_i, 120)
        else:
            ff_list = fcst_time_list(timescale_i, length)
        ## 判断是否执行
        
        
        ## make outputdir
        for hr_i in fcst_hr:                                 ## 00,12
            for _,datei in enumerate(time_list):             ## day by day
                inpath_i = f'{inpath}/{datei}{hr_i}'
                outpath_i = f'{outpath}/rain{str(timescale_i).zfill(2)}/'#{datei}{hr_i}'
                
                if not os.path.exists(outpath_i):
                    os.makedirs(outpath_i)
                ## 检查是否已经存在目标文件，若存在，则不执行
                
                indx_f = check_file_exists(outpath_i,datei,timescale_i,hr_i)
                ## 240h累计降水文件名

                if hr_i == '00':
                    hr_last = '240'
                elif hr_i == '12':
                    hr_last = '228'
                check_filen = f'{outpath_i}/fcst{datei}{hr_i}{hr_last}.grb'

                if not indx_f:
                
                    for _,fi in enumerate(ff_list):
                        inname  = f'KTR2TRG{datei}{hr_i}-{fi}.grb'
                    
                        if hr_i=='12' and timescale_i==24:
                            ed = int(fi) + 12
                            st = int(fi) - timescale_i + 12
                            outname = f'fcst{datei}{hr_i}{str(int(fi)+int(hr_i)).zfill(3)}.grb'
                        else:
                            ed = int(fi) 
                            st = int(fi) - timescale_i
                            outname = f'fcst{datei}{hr_i}{str(int(fi)).zfill(3)}.grb'
                        #print(ed,'***',st)
                    ##
                        outname_new = f'{outname}1'
                    ##   

                        precip_msgs = []
                        print('outname is --->',outname)
                        try:
                            st_filen = f'{inpath_i}/KTR2TRG{datei}{hr_i}-{str(st).zfill(3)}.grb'
                            ed_filen = f'{inpath_i}/KTR2TRG{datei}{hr_i}-{str(ed).zfill(3)}.grb'

                            ds_st = pygrib.open(st_filen)
                            ds_ed = pygrib.open(ed_filen)
                            for grb_st in ds_st:
                                grb_st_v = grb_st.values
                            for grb_ed in ds_ed:
                                grb_ed_v = grb_ed.values

                            pp = grb_ed_v - grb_st_v
                            pp[pp<0] = 0    
                            #print(pp.min(),pp.max())
                            new_msg = grb_st
                            new_msg.values = pp
                            # print(f'{outpath_i}/{outname}')
                            if not os.path.exists(f'{outpath_i}/{outname_new}'):
                                with open(f'{outpath_i}/{outname_new}','wb') as out:
                                    out.write(new_msg.tostring())
                                pynio_data = xr.open_dataset(f'{outpath_i}/{outname_new}',engine = 'cfgrib',indexpath= '')
                                data_tmp   = dataset_to_grib(pynio_data, {"tp":"tp"}, Grib2KeyDict, Pscale=1.0)
                                #print(data_tmp)
                                xarray_to_grib.to_grib(data_tmp,f'{outpath_i}/{outname}')
                                os.remove(f'{outpath_i}/{outname_new}')
                        except:
                            status = False
                            mess.append(f'KTR2TRG{datei}{hr_i}-{fi}.grb is not exist!!!'+',\n')
                else:
                    print(f'起报时间{datei}{hr_i} || 降水累积尺度{timescale_i}  数据已存在 跳出')                            
    ## 检查数据是否齐全
    ## f'{outpath}/rain{str(timescale_i)}/
    
    
    for _,datei in enumerate(time_list):
        mess_path_i = f'{mess_path}/KT1279/{datei[0:8]}/'
        if not os.path.exists(mess_path_i):
            os.makedirs(mess_path_i)
    
        for hr_i in fcst_hr:
            if hr_i == '00':
                hr_last = '240'
            elif hr_i == '12':
                hr_last = '228'
            outpath_i     = f'{outpath}/rain24/'
            retrynextmess = f'{mess_path}/KT1279/{datei[0:8]}/rain24_KT1279_{datei}{hr_i}.retry'
            successmess   = f'{mess_path}/KT1279/{datei[0:8]}/rain24_KT1279_{datei}{hr_i}.ok'
            check_filen   = f'{outpath_i}/fcst{datei}{hr_i}{hr_last}.grb'
            if os.path.exists(check_filen):
                with open(successmess, "w") as f:
                    pass
                if os.path.exists(retrynextmess):
                    os.remove(retrynextmess)
            else:
                with open(retrynextmess, "w") as f:
                    pass
    return status,mess


if __name__=="__main__":
    """
    KT1279 ---> fcst time ---> 00,12
    """
    conf = cf.pparms("./pathconfig.yaml").param
    status = True

    model_n    = 'KT1279'
    inpath     = conf.kt1279fcstpath + '/' + model_n
    outpath    = conf.kt1279outputpath + '/' + model_n + '/rain/'
    mess_path  = conf.message_rain 
    
    #t_start    = '2025083100'
    #t_end      = '2025091000'
    
    #str_st     = datetime.strptime(t_start,"%Y%m%d%H")
    #str_ed     = datetime.strptime(t_end,"%Y%m%d%H")
    #current    = str_st
     
    #while current <= str_ed:
    #    str1       = current.strftime("%Y%m%d%H")
    #    time_start = str1
    #    time_end   = (current-timedelta(days=1)).strftime("%Y%m%d%H")
    #    status,mess = process_KT_rain_grid(inpath,outpath,time_start[0:8],time_end[0:8],mess_path) 
    #    current+= timedelta(days = 1)

    timenow     = (datetime.now() - timedelta(hours=8)).strftime("%Y%m%d%H")
    time_0      = (datetime.now() - timedelta(hours=104)).strftime("%Y%m%d%H")
    time_start  = time_0[0:8]   
    time_end    = timenow[0:8]    
    status,mess = process_KT_rain_grid(inpath,outpath,time_start,time_end,mess_path)
    print(mess)
