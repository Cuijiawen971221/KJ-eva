import numpy as np
import os
import sys
import pygrib
import xarray as xr


def 



if __name__=="__main__":
    fcst_n_list    = ['NCEP','KT1279','ECMWF','CMAGFS','AUTO']
    region_n_list  = np.arange(100,108).astype('str').tolist()
    rainscale_list = [12,24]
    # current_time = datetime.now()
    # formatted_time = current_time.strftime("%Y%m%d%H")
    da_01 = int(sys.argv[1])
    da_02 = int(sys.argv[2])
    for da in range(da_01,da_02):
        current_time = f'202505{str(da).zfill(2)}12'
        hour_now     = current_time[8:10]
        if int(hour_now)<12:
            hour_in = 0
        else:
            hour_in = 12

        formatted_time = f'{current_time[0:8]}{str(hour_in).zfill(2)}' ## '2025050600'
        length_fcst = 10                                               ## 预报时间长度240hours
        #print(formatted_time)
    ## 此处的开始和结束是时间都是 当前时刻（obs）
        starttime_type1 = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")-datetime.timedelta(days=1)
        endtime_type1   = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")
        
        starttime_str   = starttime_type1.strftime("%Y%m%d%H")
        endtime_str     = endtime_type1.strftime("%Y%m%d%H")


        etime = endtime_str[0:8]   #datetime.datetime(int(formatted_time[0:4]), int(formatted_time[4:6]), int(formatted_time[6:8]))
        stime = starttime_str[0:8] #(etime - timedelta(days=1)).strftime("%Y%m%d")
    #etime = etime.strftime("%Y%m%d")
    ## 开始配置选项
        for _,expn in enumerate(fcst_n_list):
            for _,ref in enumerate(obs_n_list):
                for _,area in enumerate(region_n_list):
                    if ((expn == 'KT1279') or (expn == 'AUTO') or (expn == 'ECMWF') or (expn == 'CMA_GFS') or (expn == 'WRF')):
                        fcstst_hr = ['00','12']
                    elif expn == 'NCEP':
                        fcstst_hr = ['00','12']  
                    #print(expn)
                    #print(fcstst_hr) 
                    for _,cycl in enumerate(fcstst_hr):
                        for _,rain_scale in enumerate(rainscale_list):
                            print('当前参数如下','==>> fcst=',expn,'||  ref=',ref,'||  area=',area,'||  cycl=',cycl,'||  rain_scale=',rain_scale)
                            Data_Preparation(rain_scale, expn, cycl, stime, etime, length_fcst, ref, area, '1,3,5,10,15')   


