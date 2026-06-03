import pygrib
import os
import numpy as np
import glob
from datetime import datetime, timedelta
import logging
import xarray as xr
# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='strict_cmpas_process.log'
)
logger = logging.getLogger()

def find_files_recursive(root_path, pattern):
    """
    递归查找 root_path 下所有文件名包含 pattern 的文件
    :param root_path: 要搜索的根目录
    :param pattern: 要匹配的文件名片段
    :return: 包含所有匹配文件完整路径的列表
    """
    search_pattern = os.path.join(root_path, "**", f"*{pattern}*")
    matched_files = glob.glob(search_pattern, recursive=True)
    return matched_files

def choose_filen(inpath, intime):
    """
    筛选符合条件的文件
    :return: 完整文件路径或None(如果文件不存在)
    """
    indir = os.path.join(inpath, intime[0:8])
    fn_info = f'Z_NAFP_C_BABJ_{intime}*_P_HRCLDAS_RT_CHN_0P01_HOR-PRE-*.nc'
    matching_files = glob.glob(os.path.join(indir, fn_info))
    return matching_files[0] if matching_files else None

def generate_time_series(start_date, end_date):
    """
    生成UTC和北京时间(UTC+8)的时间序列
    """
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d') + timedelta(days=1)
    
    utc_times = []
    beijing_times = []
    
    current_dt = start_dt
    while current_dt < end_dt:
        for hour in range(24):
            utc_time = current_dt + timedelta(hours=hour)
            utc_str = utc_time.strftime('%Y%m%d%H')
            utc_times.append(utc_str)
            
            beijing_time = utc_time + timedelta(hours=8)
            beijing_str = beijing_time.strftime('%Y%m%d%H')
            beijing_times.append(beijing_str)
        
        current_dt += timedelta(days=1)
    
    return utc_times, beijing_times

def calculate_strict_accumulation(example_n, inpath, outpath, time_list, accumulation_hours):
    """
    严格按小时数累计降水量(必须所有时刻数据都存在才计算)
    
    :param inpath: 输入数据路径
    :param outpath: 输出路径
    :param time_list: 时间列表
    :param accumulation_hours: 累计小时数(3,6,12,24)
    :param grb_template: GRIB消息模板
    :return: 成功处理的数量
    """
    # 创建输出目录
    

    # 根据累计小时数确定处理的时间点
    if accumulation_hours == 3:
        target_hours = ['11', '14', '17', '20', '23','02', '05', '08']
    elif accumulation_hours == 6:
        target_hours = ['14', '20', '02', '08']
    elif accumulation_hours == 12:
        target_hours = ['08','20']
    elif accumulation_hours == 24:
        target_hours = ['08']
    else:
        raise ValueError(f"不支持的累计小时数: {accumulation_hours}")
    
    success_count = 0
    missing_count = 0
    ##
    grbs = pygrib.open(example_n)
    grb_template = grbs.select(shortName='tp')[0]
    ##
    for i, timei in enumerate(time_list):       
        if ((timei[8:10] in target_hours) and (i >= accumulation_hours-1)):
            fn_list = time_list[i-accumulation_hours+1:i+1]
            all_files_exist = True
            file_paths = []
            ## check file is all
            nn = len(fn_list)
            cc = 0
            for file_info in fn_list:
                #print('find data:',inpath, file_info)
                file_path = choose_filen(inpath, file_info)
                if file_path is None:
                    all_files_exist = False
                    logger.warning(f"file is empty: {file_info},skip {timei}-{accumulation_hours}hours")
                    # break
                else:
                    file_paths.append(file_path)
                    cc += 1
            #print('rain accumlate====>>>',accumulation_hours)
            #print(nn-cc,nn,cc)
            if nn-cc>2:
            # if not all_files_exist:
                missing_count += 1
                continue
            # all file is exists,start calculating accumlate rain
            lon_new = np.arange(70,140.25,0.25)
            lat_new = np.arange(15,60.25,0.25)

            total = np.zeros((181,281),dtype = np.float32)

            try:
                for kk,file_path_i in enumerate(file_paths):
                    ds_orig = xr.open_dataset(file_path_i)
                    ds_new  = ds_orig.interp(LAT=lat_new,LON=lon_new,method='linear')
                    tp_i = np.array(ds_new['PREC'][:])
                    tp_i[np.isnan(tp_i)] = 0
                    tp_i[np.where(tp_i<0.000001)]  = 0
                    tp_i[np.where(tp_i>1000)] = 0 
                    total += tp_i

                ## 
                total_global = np.zeros((721,1441),dtype=np.float32)
                total_global[120:301,280:561] = np.flipud(total)
                ## BJS ---> UTC
                timeiout  = datetime.strptime(timei, '%Y%m%d%H') - timedelta(hours=8)
                timeiout_ = timeiout.strftime('%Y%m%d%H')
                ##
                output_dir = os.path.join(outpath, f'rain{accumulation_hours:02d}/{timeiout_[0:6]}/')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                print('//////////////////',output_dir)
                outname_i = f'obs.{timeiout_}.grb1'
                grb_new = grb_template
                grb_new.values = total_global
                with open(os.path.join(output_dir, outname_i), 'wb') as out:
                    out.write(grb_new.tostring())
                ## 数据格式转换

                ##
                success_count += 1
                logger.info(f"process success {accumulation_hours}h accumlate rain: {outname_i}")
                
            except Exception as e:
                logger.error(f"process {timei}-{accumulation_hours}h accumlate happen error: {str(e)}")
                missing_count += 1
    
    logger.info(f"{accumulation_hours}h accumlate rain - success: {success_count}, skip: {missing_count}")
    return success_count

def main(inpath,outpath,time_start,time_end,example_n):
    #inpath     = '/vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/orig/CLDAS/'
    #outpath    = '/vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/obs/rain/CLDAS/'
    #time_start = '20250531'
    #time_end   = '20250831'
    #example_n  = '/vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/run/grb_example/rain_cldas.grb'
    
    logger.info("start processing HRCLDAS-rain")
    logger.info(f"The range of time is from: {time_start} to {time_end}")
    #print(time_start,time_end)    
    utc_list, bjs_list = generate_time_series(time_start, time_end)
    
    results = {}
    try:
        #print('***************************',example_n, inpath, outpath, bjs_list)
        results['3h']  = calculate_strict_accumulation(example_n, inpath, outpath, bjs_list, 3)
        results['6h']  = calculate_strict_accumulation(example_n, inpath, outpath, bjs_list, 6)
        results['12h'] = calculate_strict_accumulation(example_n, inpath, outpath, bjs_list, 12)
        results['24h'] = calculate_strict_accumulation(example_n, inpath, outpath, bjs_list, 24)
    except Exception as e:
        logger.error(f"processing the accumlate rain error is: {str(e)}")
    
    logger.info("the result is:")
    for duration, count in results.items():
        logger.info(f"{duration}accumlate rain : success {count} files")
    
    logger.info("HRCLDAS rain process successfully")

if __name__ == "__main__":
    time_now    = datetime.now()
    time_bef    = time_now - timedelta(days = 1)
    inpath      = '/vol8/home/kongjun/VERIFY/met/met_backend/orig/CLDAS/'
    outpath     = '/vol8/home/kongjun/VERIFY/met/met_backend/obs/rain/CLDAS/'
    example_n   = '/vol8/home/kongjun/VERIFY/met/met_backend/run/grb_example/rain_cldas.grb'
    main(inpath,outpath,time_bef.strftime("%Y%m%d%H")[0:8],time_now.strftime("%Y%m%d%H")[0:8],example_n)
