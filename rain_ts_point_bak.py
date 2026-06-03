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
def run_fss_ts(rain_scale,expn,cycl,starttime,endtime,length,obs_o,area,area_id):
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


    #mask_filen = 'mask_merge.grib'
    print('区域范围参数为=====>>>>>>>>>>>>',lonst,loned,latst,lated)
    with open(f"/vol8/home/kongjun/VERIFY/met/met_backend/config_rain_ds.txt", "r") as f:
        config = json.load(f)
    ## change region to small,use zb gridmask
    testdir1 = config["testdir1"]
    testdir = os.path.join(testdir1, "./run")
    if expn == 'NCEP' or expn=='CMA_GFS':
        grid_file = os.path.join(testdir, "ncep_china.txt")
    elif expn == 'AUTO':
        grid_file = os.path.join(testdir, "auto_china.txt")
    elif expn == 'KT1279':
        grid_file = os.path.join(testdir, "kt1279_china.txt")
    if expn == 'EC' or expn == 'ECMWF':
        grid_file = os.path.join(testdir, "ecmwf_china.txt")



    outputdir = os.path.join(testdir, "../output")  # Place where vsdb database is saved
    tmpdir    = os.path.join(testdir, "tmp")  # Temporary directory to run jobs
    pydir     = os.path.join(testdir, "../python")
    ndate     = os.path.join(testdir, "ndate")

    # Activate conda environment
    #conda_path_ = config["conda_path"]
    #subprocess.run(f"source {conda_path_}", shell=True, executable="/bin/bash")

    # FCST path <-- cdo rempil(CHINA)
    FCST_path  = os.path.join(testdir, f"FCST/{rain_scale}_{expn}")
    if not os.path.exists(FCST_path):
        os.makedirs(FCST_path)

    # Clean and create working directory
    gridrain_dir = os.path.join(tmpdir, "gridrain")
    os.makedirs(gridrain_dir, exist_ok=True)
    os.chdir(gridrain_dir)

    # Process landmask
    #if os.path.exists(os.path.join(testdir, 'mask_region.grib')):
    #    os.remove(os.path.join(testdir, 'mask_region.grib'))
    cdo_path    = config["cdo"]
    #input_grib  = os.path.join(testdir, mask_filen)
    #output_grib = os.path.join(testdir, 'mask_region.grib')
    #cmd0 = f"./cdo remapbil,{grid_file} {input_grib} {output_grib}"
    #os.chdir(cdo_path)
    #os.system(cmd0)

    #maskroot     = os.path.join(testdir, "mask_region.grib")
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

    experiments = expn.split()
    for exp in experiments:
        if exp == 'EC' or exp == 'ECMWF':
            expn_ = 'ECMWF'
        else:
            expn_ = exp
        fcstroot = os.path.join(testdir, "../fcst", expn_)
        outputrootts_ii_  = f'{outputdir}/gridrain/ts/data/rain{rain_scale}/{expn}_{obs_o}'   ## ts评分结果的输出路径
        if not os.path.exists(outputrootts_ii_):
            os.makedirs(outputrootts_ii_)
        #outputrootts_ii  = os.path.join(outputrootts_ii_, "tslist")

        # os.makedirs(os.path.join(outputdir, "gridrain", exp, f"rain{rain_scale}"), exist_ok=True)

        # Parse dates
        fcstroot_in = f'{fcstroot}/rain/rain{rain_scale}/'
        rain_scale = int(rain_scale)
        os.chdir('/vol8/home/kongjun/VERIFY/met/met_backend/python/gridrain/')

        if rain_scale == 24:
            cmd_3 = f'python {pydir}/gridrain/rain_point24.py {cycl} {fcstroot_in} {outputrootts_ii_} {starttime} {endtime}'
            print(cmd_3)
            os.system(cmd_3)
def Data_Preparation(rain_scale, expn, cycl, stime, etime, length, ref, area):
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

    #half_size = list(map(int, half_size_str.split(',')))
    length = int(length) * 24
    if int(area)<=9:
        area_ = getregion(area)
    else:
        area_ = [[15,64.5,70.5,144]]
    print('区域参数-->>>>',area_)

    run_fss_ts(rain_scale, expn, cycl, stime, etime, length, ref, area_, area)

    starttime_ = stime + cycl
    endtime_   = etime + cycl

    
if __name__=="__main__":
    ## 10 zg ,11 hb, 12 hd, 13 db, 14 hz, 15 hn, 16 xn, 17 xb 
    fcst_n_list = ['NCEP','KT1279','ECMWF','AUTO','CMAGFS']
    obs_n_list  = ['AWS']#,'CMPAS','GPM','ERA5','AWS']
    region_n_list = ['100','101','102','103','104','105','106','107']###,'101','102','103','104','105','106','107']#[1,2,3,4,5,6]##
    rainscale_list = [24]
    ## 获取系统当前的时间
    #current_time = datetime.now()
    #formatted_time = current_time.strftime("%Y%m%d%H")
    #da_01 = int(sys.argv[1])
    #da_02 = int(sys.argv[2])
    #
    #for da in range(da_01,da_02):
    if True:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H")             #f'202508{str(da).zfill(2)}12'
        hour_now     = current_time[8:10]
        if int(hour_now)<12:
            hour_in = 0
        else:
            hour_in = 12

        formatted_time = f'{current_time[0:8]}{str(hour_in).zfill(2)}' ## '2025050600'
        length_fcst = 10                                               ## 预报时间长度240hours
        ## print(formatted_time)
        ## 此处的开始和结束是时间都是 当前时刻（obs）
        starttime_type1 = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")-datetime.timedelta(days=1)
        endtime_type1   = datetime.datetime.strptime(formatted_time,"%Y%m%d%H")
        
        starttime_str   = starttime_type1.strftime("%Y%m%d%H")
        endtime_str     = endtime_type1.strftime("%Y%m%d%H")


        etime = endtime_str[0:8]   #datetime.datetime(int(formatted_time[0:4]), int(formatted_time[4:6]), int(formatted_time[6:8]))
        stime = starttime_str[0:8] #(etime - timedelta(days=1)).strftime("%Y%m%d")
    ## 开始配置选项
        fcstst_hr = ['00','12']
        for _,expn in enumerate(fcst_n_list):
            for _,ref in enumerate(obs_n_list):
                #for _,area in enumerate(region_n_list):
                for _,cycl in enumerate(fcstst_hr):
                    for _,rain_scale in enumerate(rainscale_list):
                        print('当前参数如下','==>> fcst=',expn,'||  ref=',ref,'||  cycl=',cycl,'||  rain_scale=',rain_scale)
                        #Data_Preparation(rain_scale, expn, cycl, stime, etime, length_fcst, ref, area)    
                        tasks = [
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '100'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '101'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '102'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '103'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '104'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '105'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '106'),
                                (rain_scale, expn, cycl, stime, etime, length_fcst, ref, '107'),
                            ]
                        with multiprocessing.Pool(processes=8) as pool:
                            results = pool.starmap(Data_Preparation, tasks)  # starmap 用于传递多个参数
             
