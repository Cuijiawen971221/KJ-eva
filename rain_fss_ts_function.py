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


## cuijiawen modify 20250724###################################
def get_filename(fig_path):
    filenlist = []
    for root,dirs,files in os.walk(fig_path):
        for file in files:
            if os.path.splitext(file)[-1].lower() == '.jpg':
                filenlist.append(file)
    return filenlist
    
def run_fss_ts(rain_scale,expn,cycl,starttime,endtime,length,obs_o,area,half_size_str):
    # ## 修改grid_file
    latst = area[0][0]
    lated = area[0][1]
    lonst = area[0][2]
    loned = area[0][3]
    path_now = os.getcwd()
    with open(f"/home/user/workshop/met/met_backend/config_rain.txt", "r") as f:
        config = json.load(f)
    # config = json.dumps(loaded_config, indent=4)
    # print(config)
    # Directory setup
    testdir1 = config["testdir1"]
    testdir = os.path.join(testdir1, "./run")
    if expn == 'NCEP':#### expn=='EC' or expn=='ECMWF':
        grid_file   = os.path.join(testdir, "ncep.txt")
    elif expn == 'KT1279':
        grid_file = os.path.join(testdir, "kt1279.txt")
    if expn == 'EC' or expn == 'ECMWF':
        grid_file = os.path.join(testdir, "ecmwf.txt")
    outputdir = os.path.join(testdir, "../output")       # Place where vsdb database is saved
    tmpdir = os.path.join(testdir, "tmp")                # Temporary directory to run jobs
    pydir = os.path.join(testdir, "../python")
    ndate = os.path.join(testdir, "ndate")

    # Activate conda environment
    conda_path_ = config["conda_path"]
    subprocess.run(f"source {conda_path_}", shell=True, executable="/bin/bash")

    # Observation data paths
    obs_path = config["obs_path"]
    obs_ii = f'{obs_path}/{obs_o}/rain{str(int(rain_scale)).zfill(2)}/'
    obsroot_ii = os.path.join(testdir, f"OBS/obs{rain_scale}.")

    # Clean and create working directory
    gridrain_dir = os.path.join(tmpdir, "gridrain")
    os.makedirs(gridrain_dir, exist_ok=True)
    os.chdir(gridrain_dir)

    # Process landmask
    cdo_path = config["cdo"]
    input_grib  = os.path.join(testdir, "landmask-sample.grib")
    output_grib = os.path.join(testdir, "landmask.grib")
    cmd0 = f"./cdo remapbil,{grid_file} {input_grib} {output_grib}"
    os.chdir(cdo_path)
    os.system(cmd0)

    maskroot = os.path.join(testdir, "landmask.grib")
    current_date = datetime.datetime.strptime(f'{starttime}{cycl}', "%Y%m%d%H")
    end_date = datetime.datetime.strptime(f'{endtime}{cycl}', "%Y%m%d%H")
    while current_date <= end_date:
        yymon = current_date.strftime("%Y%m")
        obs_file = os.path.join(obs_ii, yymon ,f"obs.{current_date.strftime('%Y%m%d%H')}.grb1")
        output_file = os.path.join(testdir, f"OBS/obs{rain_scale}.{current_date.strftime('%Y%m%d%H')}.grib")
        os.chdir(cdo_path)
        cmd1 = f"./cdo remapbil,{grid_file} {obs_file} {output_file}"
        os.system(cmd1)
        # Increment by rain_scale hours
        hours_to_add = int(rain_scale)
        current_date += timedelta(hours=hours_to_add)

    print('<<<<<<====================================>>>>>>')

    # Process forecast data
    end1 = datetime.datetime.strptime(endtime + cycl, "%Y%m%d%H") + timedelta(hours=264)
    experiments = expn.split()
    
    for exp in experiments:
        if exp=='EC' or exp=='ECMWF':
            expn_ = 'ECMWF'
        else:
            expn_ = exp
        fcstroot = os.path.join(testdir, "../fcst", expn_)
        # fcstroot = os.path.join(testdir, "../fcst", exp, "/rain")
        outputrootfss_ii_ = f'{outputdir}/gridrain/fss/data/rain{rain_scale}/{expn}_{obs_o}/{cycl}'
        outputrootts_ii_  = f'{outputdir}/gridrain/ts/data/rain{rain_scale}/{expn}_{obs_o}/{cycl}'



        if not os.path.exists(outputrootfss_ii_):
            os.makedirs(outputrootfss_ii_)
        if not os.path.exists(outputrootts_ii_):
            os.makedirs(outputrootts_ii_)

        outputrootfss_ii = os.path.join(outputrootfss_ii_, "fss")
        outputrootts_ii = os.path.join(outputrootts_ii_, "tslist")
            
        #os.makedirs(os.path.join(outputdir, "gridrain", exp, f"rain{rain_scale}"), exist_ok=True)

        # Parse dates
        sy = starttime[:4]
        sm = int(starttime[4:6])
        sd = int(starttime[6:8])
        ey = endtime[:4]
        em = int(endtime[4:6])
        ed = int(endtime[6:8])

        fcstroot_in = f'{fcstroot}/rain/rain{rain_scale}/'

        # Run appropriate Python scripts based on rain_scale
        rain_scale = int(rain_scale)
        if rain_scale == 24:
            cmd_1 = f'python {pydir}/gridrain/rain24.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            #os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss24.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            os.system(cmd_2)
        elif rain_scale == 12:
            cmd_1 = f'python {pydir}/gridrain/rain12.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            #os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss12.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            os.system(cmd_2)
        elif rain_scale == 6:
            cmd_1 = f'python {pydir}/gridrain/rain06.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            #os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss06.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str} {expn}'
            os.system(cmd_2)
        elif rain_scale == 3:
            cmd_1 = f'python {pydir}/gridrain/rain03.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootts_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str}'
            # os.system(cmd_1)
            cmd_2 = f'python {pydir}/gridrain/fss03.py {cycl} {fcstroot_in} {obsroot_ii} {maskroot} {outputrootfss_ii} {sy} {str(sm)} {str(sd)} {ey} {str(em)} {str(ed)} {lonst} {loned} {latst} {lated} {half_size_str}'
            os.system(cmd_2)
    return outputrootfss_ii_,outputdir

def run_main_fss_(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size_str):
    #if ref == 'CMORPH':
    #    ref = 'GPM'
    """
    更新后的code --> fss和ts结果已经预先处理完成
    此代码负责:(1)从前端传入参数，并筛选出数据   (2)结果可视化
    rain_scale      降水的累积时长
    expn            模式名称
    cycl            起报时间：00/12
    stime           评估时间：模式的起报时间 <-- 开始
    etime           评估时间：模式的起报时间 <-- 截止
    length          评估时长：预报时长，y轴的高度
    ref             参考数据：
    area            区域
    half_size_str   半窗尺寸
    """
    half_size = list(map(int, half_size_str.split(',')))
    status    = True
    mess      = []
    length    = int(length)*24
    
    ## 结果存储路径 --> /home/user/workshop/met/met_backend/output/gridrain/fss/data/
    result_fss = {}
    with open(f"/home/user/workshop/met/met_backend/config_rain.txt", "r") as f:
        config = json.load(f)
    outpath_fss_fig  = config["outpath_fss_fig"]
    outpath_fss_data = config["outpath_fss_data"]
    # print(area)
    fig_path = f'{outpath_fss_fig}/rain{rain_scale}/{expn}_{ref}/{cycl}/region{area[0]}/'#{stime}to{etime_ori}_{length}'
    # print(fig_path)
    if not os.path.exists(fig_path):
        os.makedirs(fig_path)

    fss_outpath = f'{outpath_fss_data}/rain{rain_scale}/{expn}_{ref}/region{area[0]}/{cycl}/'
    ## 生成时间序列，fss{iii}.{yyyymmddhh}  -->  iii是预报时效，yyyymmddhh是观测的时间
    starttime_ = stime + cycl
    endtime_   = etime + cycl
    ## set reslution
    if expn == 'KT1279':
        res = 25
    elif expn == 'NCEP':
        res = 50
    elif (expn == 'EC') or (expn == 'ECMWF'):
        res = 12.5
    elif expn == 'CMAGFS':
        res = 100
    if int(rain_scale)==3:
        level_list = [0.1, 3,   10, 20, 25, 30]
    elif int(rain_scale)==6:
        level_list = [0.1, 4, 12.5, 25, 40, 50]
    elif int(rain_scale)==12:
        level_list = [0.1, 5, 15,   30, 70, 140]
    elif int(rain_scale)==24:
        level_list = [0.1,10, 25,   50,100, 250]

    distance_list   = np.array(half_size)*res
    starttime_ = f'{stime}{cycl}'
    endtime_   = f'{etime}{cycl}'

    for ii,level in enumerate(level_list):               ## rain level
        for jj,distance in enumerate(distance_list):     ## distance(windows size)
            print(fss_outpath)
            print('抽取数据','rain>',level,'mm   windows size=',distance)           ## 
            result, initial_times_part = process_files(fss_outpath, starttime_, endtime_, level, distance, int(rain_scale), int(length))
            tlength = result.shape[1]
            # print(result)
            # print(initial_times_part)


            result[np.where(result<-99)] = np.nan
            outname = f'{fig_path}/FSS_pre{ii+1}_res{jj+1}-{starttime_}to{endtime_}.jpg'
            pcolor_fss(result, initial_times_part, outname, rain_scale, level ,distance/res)
            with open(outname, "rb") as image_file:
                result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")
    return status,mess,result_fss






def run_main_fss_backend(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size_str):
    if ref == 'AWS':
        ref = 'CLDAS'
    etime_ori = etime
    print(etime)
    etime = datetime.datetime(int(etime[0:4]),int(etime[4:6]),int(etime[6:8]))
    etime = (etime + timedelta(days=10)).strftime("%Y%m%d")
    print(etime_ori,etime)
    # print('半窗尺寸::::::::::>>>>>>>>>',half_size)
    # half_size = np.array(half_size)
    # half_size_str = ','.join(map(str, arr))
    half_size = list(map(int, half_size_str.split(',')))
    status = True
    mess = []
    length = int(length)*24
    area_ = getregion(area)
    result_fss = {}
    with open(f"/home/user/workshop/met/met_backend/config_rain.txt", "r") as f:
        config = json.load(f)
    outpath_fss_fig = config["outpath_fss_fig"]
    fig_path = f'{outpath_fss_fig}/rain{rain_scale}/{expn}_{ref}/{cycl}/{stime}to{etime_ori}_{length}'
    print(fig_path)

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
        print('&&&&&&&&&&& path is not exists')
        os.makedirs(fig_path)
        outputrootfss_ii_, outputdir = run_fss_ts(rain_scale, expn, cycl, stime, etime, length, ref, area_, half_size_str)
        starttime_ = stime + cycl
        endtime_ = etime + cycl
        # status, mess, result_fss = run_main_(rain_scale, area_, starttime_, endtime_, outputrootfss_ii, outputdir)
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
            level_list = [0.1,10, 25,   50,100, 250]
            distance_list   = np.array(half_size)*res
        #result_fss = {}
        for _,level in enumerate(level_list):
            for _,distance in enumerate(distance_list):
                #print('抽取数据',level,distance)
                result_part, initial_times_part = process_files(outputrootfss_ii_, starttime_, endtime_, level, distance, int(rain_scale), int(length))
                tlength = result_part.shape[1]
                if expn=='KT1279' and int(rain_scale)<12:
                    result = result_part[:,0:tlength-10*int(24/12)]
                    initial_times = initial_times_part[0:tlength-10*int(24/12)]
                else:
                    result = result_part[:,0:tlength-10*int(24/int(rain_scale))]
                    initial_times = initial_times_part[0:tlength-10*int(24/int(rain_scale))]

                result[np.where(result<-99)] = np.nan
                outname = f'{fig_path}/FSS_pre{level}_res{distance}.jpg'
                pcolor_fss(result, initial_times, outname, rain_scale, level ,distance/res)
                with open(outname, "rb") as image_file:
                    result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")

    return status,mess,result_fss



def run_main_fss_all(rain_scale, expn, cycl, stime, etime, length, ref, area, half_size_str):

    etime_ori = etime
    etime = datetime.datetime(int(etime[0:4]),int(etime[4:6]),int(etime[6:8]))
    etime = (etime + timedelta(days=10)).strftime("%Y%m%d")

    half_size = list(map(int, half_size_str.split(',')))
    status = True
    mess = []
    length = int(length) * 24
    area_ = getregion(area)
    with open(f"/home/user/workshop/met/met_backend/config_rain.txt", "r") as f:
        config = json.load(f)
    outpath_fssall_fig = config["outpath_fssall_fig"]
    fig_path = f'{outpath_fssall_fig}/rain{rain_scale}/{expn}_{ref}/{cycl}/{stime}to{etime_ori}_{length}'

    result_fss = {}
    if os.path.exists(fig_path):
        outname_list = get_filename(fig_path)
        nn = len(outname_list)

    if ((os.path.exists(fig_path)) and (nn>0)):
        filelist = get_filename(fig_path)
        outname = f'{fig_path}/{filelist[0]}'
        with open(outname, "rb") as image_file:
            result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")

    elif not os.path.exists(fig_path):
        os.makedirs(fig_path)
        outputrootfss_ii_, outputdir = run_fss_ts(rain_scale, expn, cycl, stime, etime, length, ref, area_, half_size_str)
        starttime_ = stime + cycl
        endtime_ = etime + cycl
        # status, mess, result_fss = run_main_(rain_scale, area_, starttime_, endtime_, outputrootfss_ii, outputdir)
        if expn == 'KT1279':
            res = 25
        elif expn == 'NCEP':
            res = 50
        elif expn=='EC' or expn == 'ECMWF':
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
            level_list = [0.1, 10, 25, 50, 70, 100]
            distance_list = np.array(half_size) * res

        
        result = np.zeros((len(distance_list),len(level_list)),dtype=np.float32)

        for ii, level in enumerate(level_list):
            for jj, distance in enumerate(distance_list):
                result_part, initial_times_part = process_files(outputrootfss_ii_, starttime_, endtime_, level, distance, int(rain_scale), int(length))
                
                tlength = result_part.shape[1]
                result_ = result_part[:,0:tlength-10*int(24/int(rain_scale))]
                 
                result_[np.where(result_ < -99)] = np.nan
                result[jj,ii] = np.nanmean(result_)


        outname = f'{fig_path}/{starttime_}to{endtime_}_FSS.jpg'
        pcolor_fss_all(result, expn, outname, level_list, np.array(half_size))###(result, initial_times, outname, rain_scale)
        with open(outname, "rb") as image_file:
            result_fss[outname] = base64.b64encode(image_file.read()).decode("utf-8")
    
    return status, mess, result_fss

if __name__=="__main__":
    rain_scale    = 24
    expn          = 'NCEP'
    cycl          = '12'
    stime         = '20250501'  
    etime         = '20250502'
    length        = 10
    ref           = 'CMORPH'
    area          = '6'
    half_size_str = '1,3,5,10,15'  

    run_main_fss_(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size_str)
