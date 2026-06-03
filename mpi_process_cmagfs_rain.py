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
            filename = f'{outpath_i}/fcst{datei}12240.grb'
        elif timescale_i == 6 or timescale_i == 12:
            filename = f'{outpath_i}/fcst{datei}12240.grb'
        elif timescale_i == 24:
            filename = f'{outpath_i}/fcst{datei}12228.grb'
        
    else:
        if timescale_i == 3:
            filename = f'{outpath_i}/fcst{datei}00240.grb'
        else:
            filename = f'{outpath_i}/fcst{datei}00240.grb'
    
    if os.path.exists(filename):
        indx_f = True
    else:
        indx_f = False
    
    return indx_f


def select_filename_glob(inpath,filen):
    matches = glob.glob(f'{inpath}/**/{filen}')
    for path in matches:
        status = True
    return path


def process_cma_rain_grid(inpath:str,outpath:str,time_start:str,time_end:str,mess_path:str,example_n:str)->tuple:
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
            ff_list = fcst_time_list(timescale_i, 240)
        else:
            ff_list = fcst_time_list(timescale_i, length)
        ## 判断是否执行
        
        
        ## make outputdir
        for hr_i in fcst_hr:                                 ## 00,12
            for _,datei in enumerate(time_list):             ## day by day
                #inpath_i = f'{inpath}'
                #filenma_select = f'Z_NAFP_C_BABJ_{datei}{hr_i}0000_P_CNPC-GRPS-GMFS-ABROAD-{fi}00.grb2'
                #print('输入路径为:',inpath_i)
                outpath_i = f'{outpath}/rain{str(timescale_i).zfill(2)}/'#{datei}{hr_i}'
                print('输出路径为:',outpath_i)
                if not os.path.exists(outpath_i):
                    os.makedirs(outpath_i)
                ## 检查是否已经存在目标文件，若存在，则不执行
                
                indx_f = check_file_exists(outpath_i,datei,timescale_i,hr_i)
                if not indx_f:
                
                    for _,fi in enumerate(ff_list):
                        #inname  = f'fcst{datei}{hr_i}{fi}.grb'
                    
                        if hr_i=='12' and timescale_i==24:
                            ed = int(fi) + 12
                            st = int(fi) - timescale_i + 12
                            outname = f'fcst{datei}{hr_i}{str(int(fi)+int(hr_i)).zfill(3)}.grb'
                        else:
                            ed = int(fi) 
                            st = int(fi) - timescale_i
                            outname = f'fcst{datei}{hr_i}{str(int(fi)).zfill(3)}.grb'
                        print(ed,'***',st)
                        #outname_new = f'{outname}1'
                    ##  
                    ##   

                        precip_msgs = []
                        print('outname is --->',outname)
                         
                        try:
                            
                            st_filen = select_filename_glob(inpath,f'Z_NAFP_C_BABJ_{datei}{hr_i}0000_P_CNPC-GRPS-GMFS-ABROAD-{str(st).zfill(3)}00.grb2')
                            ed_filen = select_filename_glob(inpath,f'Z_NAFP_C_BABJ_{datei}{hr_i}0000_P_CNPC-GRPS-GMFS-ABROAD-{str(ed).zfill(3)}00.grb2')
                            #st_filen = f'{inpath_i}/fcst{datei}{hr_i}{str(st).zfill(3)}.grib'
                            #ed_filen = f'{inpath_i}/fcst{datei}{hr_i}{str(ed).zfill(3)}.grib'
                            print('结束的文件',ed_filen)
                            print('开始的文件',st_filen)
                            ds_st = pygrib.open(st_filen)
                            ds_ed = pygrib.open(ed_filen)
                            
                            grb_st= ds_st[96] 
                            grb_ed= ds_ed[96]
                            
                            
                            grb_st_v = np.array(grb_st.values)
                            grb_ed_v = np.array(grb_ed.values)
                            if ed == timescale:
                                pp = grb_ed_v
                            else:
                                pp = grb_ed_v - grb_st_v
                            pp[pp<0] = 0   
                            
                          
                            with pygrib.open(example_n) as grbs_e:
                                example_grib = grbs_e.select(shortName='prate')[0]
                    # 替换数据值，保留其他元信息
                                new_msg = example_grib
                                new_msg.values = pp

                            if not os.path.exists(f'{outpath_i}/{outname}'):
                                with open(f'{outpath_i}/{outname}','wb') as out:
                                    out.write(new_msg.tostring()) 
                                #pynio_data = xr.open_dataset(f'{outpath_i}/{outname_new}',engine = 'cfgrib',indexpath= '')
                                #data_tmp   = dataset_to_grib(pynio_data, {"tp":"tp"}, Grib2KeyDict, Pscale=1.0)
                                #xarray_to_grib.to_grib(data_tmp,f'{outpath_i}/{outname}')
                                #os.remove(f'{outpath_i}/{outname_new}')
                        except:
                        
                            status = False
                            mess.append(f'CMA-GFS fcst{datei}{hr_i}.{fi} is not exist!!!'+',\n')
                else:
                    print(f'起报时间{datei}{hr_i} || 降水累积尺度{timescale_i}  数据已存在 跳出')   
                             
    for _,datei in enumerate(time_list):
        for hr_i in fcst_hr:
            if hr_i == '00':
                hr_last = '240'
            elif hr_i == '12':
                hr_last = '228'
            outpath_i     = f'{outpath}/rain24/'
            mess_path_i   = f'{mess_path}/CMA_GFS/{datei[0:8]}'
            if not os.path.exists(mess_path_i):
                os.makedirs(mess_path_i)
            retrynextmess = f'{mess_path}/CMA_GFS/{datei[0:8]}/rain24_CMAGFS_{datei}{hr_i}.retry'
            successmess   = f'{mess_path}/CMA_GFS/{datei[0:8]}/rain24_CMAGFS_{datei}{hr_i}.ok'
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
    Auto2.0 ---> fcst time ---> 00,12
    """
    conf = cf.pparms("./pathconfig.yaml").param
    status = True

    model_n    = 'CMA_GFS'
    inpath     = conf.cmagfsfcstpath + '/' + model_n    
    outpath    = conf.cmagfsoutputpath + '/' + model_n + '/rain/'    
    mess_path  = conf.message_rain
    example_n  = conf.cmagfs_example
    
    
    #timest_str = '20250819'
    #timeed_str = '20250911'
    #time_st_t  = datetime.strptime(timest_str,"%Y%m%d")
    #time_ed_t  = datetime.strptime(timeed_str,"%Y%m%d")
    #current    = time_st_t
    
    #while current <= time_ed_t:

        #time_1 = current.strftime("%Y%m%d") 
        #time_0 = (current-timedelta(days=1)).strftime("%Y%m%d")        
    time_1     = (datetime.now() - timedelta(hours=8)).strftime("%Y%m%d%H")
    time_0     = (datetime.now() - timedelta(hours=104)).strftime("%Y%m%d%H")
    time_start = time_0[0:8]  
    time_end   = time_1[0:8]   
    print(time_start,time_end)
    status,mess = process_cma_rain_grid(inpath,outpath,time_start,time_end,mess_path,example_n)
    #print(mess)
    #current += timedelta(days=1) 
