import os
import subprocess
import sys
from datetime import datetime, timedelta
from read_fss import *
from yunyao_met import *
import base64
import re
import json
import datetime
from datetime import timezone
import shutil
import multiprocessing
#此版本codes
#1.定时计算fss、ts、ets，数据结果存储入库
#2.时间是以观测时间为准：即每天计算[前一天,当前时刻]，当前时刻没有验证数据的，就会-999，第二天再算一下，会覆盖前一天的，确保前一日的数据有效
#3.数据结果保
def run_fss_ts(rain_scale,expn,cycl,starttime,endtime,length,obs_o,area,half_size_str,area_id):
    #print('执行run_fss_ts')
    """
    rain_scale：降水累计时间尺度
    expn：模式名称
    cycl：起报时刻
    starttime：开始时间，预报的时间，fcst的起报时间
    endtime：截止时间
    length：时间长度，默认10天
    obs_o：观测数据
    area：区域编码
    half_size_str：半窗尺寸
    """
    # ## 修改grid_file
    if int(area_id)<100:
        latst = area[0][0]
        lated = area[0][1]
        lonst = area[0][2]
        loned = area[0][3]
    else:
        ## area_id ==> 8
        latst = 15 
        lated = 64.5
        lonst = 70.5
        loned = 144
        if int(area_id)==100:
            mask_filen = 'landmask.grib' 
        elif int(area_id)==101:
            mask_filen = 'landmask-hb.grib'
        elif int(area_id)==102:
            mask_filen = 'landmask-hd.grib'
        elif int(area_id)==103:
            mask_filen = 'landmask-db.grib'
        elif int(area_id)==104:
            mask_filen = 'landmask-hz.grib'
        elif int(area_id)==105:
            mask_filen = 'landmask-hn.grib'
        elif int(area_id)==106:
            mask_filen = 'landmask-xn.grib'
        elif int(area_id)==107:
            mask_filen = 'landmask-xb.grib'
        
    print('区域范围参数为=====>>>>>>>>>>>>',lonst,loned,latst,lated)
    with open(f"/vol8/home/kongjun/VERIFY/met/met_backend/config_rain_ds.txt", "r") as f:
        config = json.load(f)
    ## change region to small,use zb gridmask
    testdir1 = config["testdir1"]
    testdir = os.path.join(testdir1, "./run")
    if expn == 'NCEP':
        grid_file = os.path.join(testdir, "ncep_china.txt")
    elif expn=='CMAGFS':
        grid_file = os.path.join(testdir, "cmagfs_china.txt")
    elif expn == 'AUTO':
        grid_file = os.path.join(testdir, "auto_china.txt")
    elif expn == 'KT1279':
        grid_file = os.path.join(testdir, "kt1279_china.txt")
    if expn == 'EC' or expn == 'ECMWF':
        grid_file = os.path.join(testdir, "ecmwf_china.txt")
    if expn == 'AWS':
        grid_file = os.path.join(testdir, "ecmwf_china.txt")
    #if expn == 'WRF':
    #    grid_file = os.path.join(testdir, "wrf.txt")
   


    outputdir = os.path.join(testdir, "../output")  # Place where vsdb database is saved
    tmpdir    = os.path.join(testdir, "tmp")  # Temporary directory to run jobs
    pydir     = os.path.join(testdir, "../python")
    ndate     = os.path.join(testdir, "ndate")

    # Activate conda environment
    conda_path_ = config["conda_path"]
    subprocess.run(f"source {conda_path_}", shell=True, executable="/bin/bash")
    
    # Observation data paths
    obs_path = config["obs_path"]
    obs_ii = f'{obs_path}/{obs_o}/rain{str(int(rain_scale)).zfill(2)}/'
    ## clear old files
    if not os.path.exists(f'{testdir}/OBS/{obs_o}_{expn}_{area_id}_his/'):       #os.path.join(testdir, "OBS", obs_o)):
        os.makedirs(f'{testdir}/OBS/{obs_o}_{expn}_{area_id}_his/')             #os.path.join(testdir, "OBS", obs_o))

    obsroot_ii = os.path.join(testdir, f"OBS/{obs_o}_{expn}_{area_id}_his/obs{rain_scale}.")
    FCST_path  = os.path.join(testdir, f"FCST/{rain_scale}_{expn}_{area_id}_his")
    if not os.path.exists(FCST_path):
        os.makedirs(FCST_path)
    # Clean and create working directory
    gridrain_dir = os.path.join(tmpdir, "gridrain")
    os.makedirs(gridrain_dir, exist_ok=True)
    os.chdir(gridrain_dir)

    # Process landmask
    if os.path.exists(os.path.join(testdir, f"mask_region_{expn}_{int(area_id)}_his.grib")):
        os.remove(os.path.join(testdir, f"mask_region_{expn}_{int(area_id)}_his.grib"))
    cdo_path    = config["cdo"]
    input_grib  = os.path.join(testdir, mask_filen)
    output_grib = os.path.join(testdir, f"mask_region_{expn}_{int(area_id)}_his.grib")
    cmd0 = f"./cdo remapbil,{grid_file} {input_grib} {output_grib}"
    os.chdir(cdo_path)
    os.system(cmd0)

    maskroot     = os.path.join(testdir, f"mask_region_{expn}_{int(area_id)}_his.grib")
    current_date = datetime.datetime.strptime(f'{starttime}{cycl}', "%Y%m%d%H")  ##开始时间，当前日期
    end_date     = datetime.datetime.strptime(f'{endtime}{cycl}', "%Y%m%d%H")    ##截止时间，当前日期
    end_date_obs = datetime.datetime.strptime(f'{endtime}23', "%Y%m%d%H")    ##截止时间，当前日期
    ## 计算fss和ts评分前，需要将obs重采样到fcst，借助cdo实现
    ## obs数据存储格式rain/era5/rain03/yyyymm/obs.yyyymmddhh.grb1
    ## 处理观测数据，进行插值，end_date_obs = yyyymmdd23
    hours_to_add = int(rain_scale)

    ##
    if hours_to_add == 24:
        start_hour = "00"
    elif hours_to_add == 12 and int(cycl) in [6, 18]:
        start_hour = "00"
    elif hours_to_add == 12 and int(cycl) % 12 == 0:
        start_hour = cycl
    else:
        start_hour = cycl

    current_date = datetime.datetime.strptime(f'{starttime}{start_hour}', "%Y%m%d%H")

    while current_date <= end_date_obs:
        yymon = current_date.strftime("%Y%m")
        obs_file = os.path.join(obs_ii, yymon, f"obs.{current_date.strftime('%Y%m%d%H')}.grb1")
        output_file = os.path.join(testdir, f"OBS/{obs_o}_{expn}_{area_id}_his/obs{rain_scale}.{current_date.strftime('%Y%m%d%H')}.grib")

        os.chdir(cdo_path)
        cmd1 = f"./cdo remapbil,{grid_file} {obs_file} {output_file}"
        os.system(cmd1)
        current_date += datetime.timedelta(hours=hours_to_add)

    experiments = expn.split()

    for exp in experiments:
        if exp == 'EC' or exp == 'ECMWF':
            expn_ = 'ECMWF'
        else:
            expn_ = exp
        fcstroot = os.path.join(testdir, "../fcst", expn_)
        outputrootfss_ii_ = f'{outputdir}/gridrain/fss/data/rain{rain_scale}/{expn}_{obs_o}_region{area_id}_{cycl}'  ## fss结果的输出路径
        outputrootts_ii_  = f'{outputdir}/gridrain/ts/data/rain{rain_scale}/{expn}_{obs_o}_region{area_id}_{cycl}'   ## ts评分结果的输出路径

        if not os.path.exists(outputrootfss_ii_):
            os.makedirs(outputrootfss_ii_)
        if not os.path.exists(outputrootts_ii_):
            os.makedirs(outputrootts_ii_)

        outputrootfss_ii = os.path.join(outputrootfss_ii_, "fss")
        outputrootts_ii  = os.path.join(outputrootts_ii_, "tslist")

        # os.makedirs(os.path.join(outputdir, "gridrain", exp, f"rain{rain_scale}"), exist_ok=True)

        # Parse dates
        sy = starttime[:4]
        sm = int(starttime[4:6])
        sd = int(starttime[6:8])

        ey = endtime[:4]
        em = int(endtime[4:6])
        ed = int(endtime[6:8])

        fcstroot_in = f'{fcstroot}/rain/rain{rain_scale}/'
        rain_scale = int(rain_scale)
        if rain_scale == 24:
            cmd_1 = f'python {pydir}/gridrain/rain24.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss24.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_2)
        elif rain_scale == 12:
            cmd_1 = f'python {pydir}/gridrain/rain12.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss12.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_2)
        elif rain_scale == 6:
            cmd_1 = f'python {pydir}/gridrain/rain06.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss06.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_2)
        elif rain_scale == 3:
            cmd_1 = f'python {pydir}/gridrain/rain03.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss03.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {starttime} {endtime} {lonst} {loned} {latst} {lated} {half_size_str} {FCST_path} {grid_file} {cdo_path}'
            os.system(cmd_2)



def Data_Preparation(rain_scale, expn, cycl, stime, etime, length, ref, area, half_size_str='1,3,5,10,15'):
    """
    rain_scale：降水累计时间尺度
    expn：模式名称
    cycl：起报时间（小时）
    stime：开始时间YYYYMMDD
    etime：截止时间YYYYMMDD
    length：时间长度（天数）
    ref：观测数据
    area_：区域编号
    half_size_str：半窗尺寸
    """
    ## 开始时间，当前日-1
    ## 截止时间，当前日
    # etime_ori = etime
    # print(etime)
    # etime = datetime.datetime(int(etime[0:4]), int(etime[4:6]), int(etime[6:8]))
    # etime = (etime + timedelta(days=10)).strftime("%Y%m%d")
    # print(etime_ori, etime)

    half_size = list(map(int, half_size_str.split(',')))
    length = int(length) * 24
    if int(area)<=9:
        area_ = getregion(area)
    else:
        area_ = [[15,64.5,70.5,144]]
    print('区域参数-->>>>',area_)

    run_fss_ts(rain_scale, expn, cycl, stime, etime, length, ref, area_, half_size_str,area)

    starttime_ = stime + cycl
    endtime_   = etime + cycl

    if expn == 'KT1279':
        res = 25
    elif expn == 'NCEP':
        res = 50
    elif expn == 'AUTO':
        res = 25
    elif expn == 'CMAGFS':
        res = 100
    elif (expn == 'EC') or (expn == 'ECMWF'):
        res = 12.5
    if int(rain_scale) == 3:
        level_list = [0.1, 3, 10, 20, 25, 30]
        distance_list = np.array(half_size) * res
    elif int(rain_scale) == 6:
        level_list = [0.1, 4, 12.5, 25, 40, 50]
        distance_list = np.array(half_size) * res
    elif int(rain_scale) == 12:
        level_list = [0.1, 5, 15, 30, 70, 140]
        distance_list = np.array(half_size) * res
    elif int(rain_scale) == 24:
        level_list = [0.1, 10, 25, 50, 100, 250]
        distance_list = np.array(half_size) * res


if __name__=="__main__":
    #da_01 = int(sys.argv[1])
    #da_02 = int(sys.argv[2])
    expn_list = ['NCEP','KT1279','ECMWF','AUTO','CMAGFS'] #= sys.argv[1]
    obs_n_list  = ['CLDAS']#,'CMPAS','GPM','ERA5','AWS']
    region_n_list = ['100','101','102','103','104','105','106','107']#[1,2,3,4,5,6]## 100,101,102,103,104,105,106,107
    rainscale_list = [24]
    ## 获取系统当前的时间
    #for da in range(da_01,da_02+1):
    if True:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H")
        hour_now     = current_time[8:10]
        if int(hour_now)<12:
            hour_in = 0
        else:
            hour_in = 12

        formatted_time  = f'{current_time[0:8]}{str(hour_in).zfill(2)}' ## '2025050600'
        length_fcst     = 10                                               ## 预报时间长度240hours

        starttime_type1 = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")-datetime.timedelta(days=1)
        endtime_type1   = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")
        
        starttime_str   = starttime_type1.strftime("%Y%m%d%H")
        endtime_str     = endtime_type1.strftime("%Y%m%d%H")

        etime = endtime_str[0:8]   #datetime.datetime(int(formatted_time[0:4]), int(formatted_time[4:6]), int(formatted_time[6:8]))
        stime = starttime_str[0:8] #(etime - timedelta(days=1)).strftime("%Y%m%d")
    
        fcstst_hr = ['00','12']
        for _,expn in enumerate(expn_list):
            for _,ref in enumerate(obs_n_list):
                for _,cycl in enumerate(fcstst_hr):
                    for _,rain_scale in enumerate(rainscale_list):
                        print('当前参数如下','==>> fcst=',expn,'||  ref=',ref,'||  cycl=',cycl,'||  rain_scale=',rain_scale)
                        tasks = [
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '100', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '101', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '102', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '103', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '104', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '105', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '106', '1,3,5,10,15'),
                            (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '107', '1,3,5,10,15'),
                        ]
                        with multiprocessing.Pool(processes=8) as pool:
                            results = pool.starmap(Data_Preparation, tasks)  # starmap 用于传递多个参数
             
