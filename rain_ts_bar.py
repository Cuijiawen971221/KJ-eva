import numpy as np 
import os
import sys 
from datetime import datetime,timedelta
import json
import re


def parse_txt(file_path):
    print(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines[1:]:  # 跳过表头
        parts_tmp = line.strip().split()
        if len(parts_tmp) < 6:
            if len(parts_tmp)==4:
                parts = []
                parts.append(parts_tmp[0])
                parts.append(parts_tmp[1])
                parts.append(parts_tmp[2])
                parts.append(parts_tmp[3][:-14])
                parts.append(parts_tmp[3][-14:-7])
                parts.append(parts_tmp[3][-7:])
            elif len(parts_tmp)==5:
                parts = []
                parts.append(parts_tmp[0])
                parts.append(parts_tmp[1])
                parts.append(parts_tmp[2])
                parts.append(parts_tmp[3])
                parts.append(parts_tmp[4][:-7])
                parts.append(parts_tmp[4][-7:])
      
        else:
            
            parts = parts_tmp
        #print(line)
        #print(parts)
        threshold = parts[0].split()[0]  # 提取降水阈值（如 '0.1'）
        aa = int(parts[2])
        bb = int(parts[3])
        cc = int(parts[4])
        dd = int(parts[5])
        if len(parts)>=7:
            bias= float(parts[6])/1000
        else:
            bias = 0
        data.append({
          'threshold': threshold,
          'aa': aa,
          'bb': bb,
          'cc': cc,
          'dd': dd,
          'bias':bias
    })
    return data

def calculate_ts(aa, bb, cc):
  #"""计算 Threat Score (TS)"""
    if aa + bb + cc == 0:
        return 0.0
    return aa / (aa + bb + cc)

def calculate_false_alarm_rate(aa,bb):
    if aa+bb==0:
        return 0.0
    return bb/(aa+bb)
    
def calculate_ets(aa, bb, cc, dd):
  #"""计算 Equitable Threat Score (ETS)"""
    total = aa + bb + cc + dd
    if total == 0:
        return 0.0
    numerator = aa - ( (aa + bb) * (aa + cc) ) / total
    denominator = (aa + bb + cc) - ( (aa + bb) * (aa + cc) ) / total
    if denominator == 0:
        return 0.0
    return numerator / denominator

def calculate_pod(aa, cc):
  #"""计算 Probability of Detection (POD)"""
    if aa + cc == 0:
        return 0.0
    return cc / (aa + cc)

def calculate_hitrate(aa,bb,cc,dd):
    return (aa+dd)/(aa+bb+cc+dd)


def choose_file(tspath,fcst_list1,starttime,endtime,cycl,areaid,ref,metric):
   # """
    #path
    #mode name
    #yyyymmdd
   # yyyymmdd
   # 00,12
   # 5,6,7,...
   # ERA5,CMORPH,...
   # ts
   # """
   # print(fcst_list1)
    fcst_list = list(map(str, fcst_list1.split(',')))
   # print(fcst_list)
    if cycl == '00':
        lead_times = list(range(24, 240+1, 24))
    elif cycl == '12':
        lead_times = list(range(36, 240+1, 24))

    if starttime == endtime:
        filen_list = []
        step_list  = []
        fcsti_list = []
        sttime_list= []
        
        for _,fcst in enumerate(fcst_list):
            for _,fcstperiod in enumerate(lead_times):
                start_time  = starttime + cycl
                sttime_str  = datetime.strptime(start_time, "%Y%m%d%H")
                obstime_str = (sttime_str + timedelta(hours=int(fcstperiod))).strftime("%Y%m%d%H")
                step_list.append(fcstperiod)
                fcsti_list.append(fcst)
                sttime_list.append(sttime_str.strftime("%Y%m%d%H"))
                filen = f'{tspath}/rain24/{fcst}_{ref}_region{areaid}_{cycl}/tslist{str(int(fcstperiod)).zfill(3)}.{obstime_str}'
                filen_list.append(filen)
                
    else:
        sttime_str = datetime.strptime(f'{starttime}{cycl}', "%Y%m%d%H")
        edtime_str = datetime.strptime(f'{endtime}{cycl}', "%Y%m%d%H")
        filen_list = []
        step_list  = []
        fcsti_list = []
        sttime_list= []
        current = sttime_str
        while current <= edtime_str:
            for _,fcst in enumerate(fcst_list):
                for _,fcstperiod in enumerate(lead_times):
                    step_list.append(fcstperiod)
                    fcsti_list.append(fcst)
                    sttime_list.append(current.strftime("%Y%m%d%H"))
                    obstime_str = (current + timedelta(hours=int(fcstperiod)))
                    filen_list.append(f'{tspath}/rain24/{fcst}_{ref}_region{areaid}_{cycl}/tslist{str(int(fcstperiod)).zfill(3)}.{obstime_str.strftime("%Y%m%d%H")}')
            current += timedelta(days=1)

    return filen_list, step_list, fcsti_list, sttime_list

def process_ts2json(filen_list, step_list, fcsti_list, sttime_list, metric):
    results = []

    for ii,fileni in enumerate(filen_list):
        if os.path.exists(fileni):
            start_time = sttime_list[ii]
            mode_type  = fcsti_list[ii]
            step       = step_list[ii]
            data       = parse_txt(fileni)

# 计算指标

            for entry in data:
                threshold = entry['threshold']
                aa = entry['aa']
                bb = entry['bb']
                cc = entry['cc']
                dd = entry['dd']
                bias = entry['bias']
                if metric == 'ts':
                    value = calculate_ts(aa, bb, cc)
                elif metric == 'ets':
                    value = calculate_ets(aa, bb, cc, dd)
                elif metric == 'mar':
                    value = calculate_pod(aa, cc)
                elif metric == 'far':
                    value = calculate_false_alarm_rate(aa,bb)
                elif metric == 'hitrate':
                    value = calculate_hitrate(aa,bb,cc,dd)
                elif metric == 'bias':
                    value = bias
                else:
                    raise ValueError(f"未知的指标: {metric}")

                if metric == 'hitrate':
                    if threshold == '0.1' and int(step)<=120:

                        results.append({
                            'starttime': start_time,
                            'modeType': mode_type,
                            'step': ' ',
                            'threshold':step,# threshold,
                            'value': round(value,2)
                        })
                elif metric == 'bias':
                    if threshold == '0.1' and int(step)<=120 and np.mean(bias)>0:

                        results.append({
                            'starttime': start_time,
                            'modeType': mode_type,
                            'step': ' ',
                            'threshold':step,# threshold,
                            'value': round(np.mean(bias),2)
                        })

                else:
                    results.append({
                            'starttime': start_time,
                            'modeType': mode_type,
                            'step': step,
                            'threshold': threshold,
                            'value': round(value,2)
                        })


  # 构建JSON
    # json_data = {
    #          "status": True,
    #          "mess": "success",
    #          "data": results
    #     }
    status = True
    mess = []
    # return status,mess,json.dumps(json_data, indent=4)
    return status,mess,results

def run_main_rain_bar(fcst_list,starttime,endtime,cycl,areaid,ref,metric):
    if ref == 'GPM':
        ref = 'CMORPH'
    tspath    = '/home/user/workshop/met/met_backend/output/gridrain/ts/data/'
    filen_list, step_list, fcsti_list, sttime_list = choose_file(tspath,fcst_list,starttime,endtime,cycl,areaid,ref,metric)
    status,mess,json_result = process_ts2json(filen_list, step_list, fcsti_list, sttime_list,metric)
    return status,mess,json_result

if __name__=="__main__":
    fcst_list = 'ECMWF'#sys.argv[1]   # 'ECMWF,ECMWF'#
    starttime = '20250509'#sys.argv[2]   # '20250516'#
    endtime   = '20250509'#sys.argv[3]   # '20250516'#
    cycl      = '00'#sys.argv[4]   # '00'##
    areaid    = '100'#sys.argv[5]   # '6'#
    ref       = 'CLDAS'#sys.argv[6]   # 'CMORPH'#
    metric    = 'bias'#sys.argv[7]   # 'ts','ets'   
    status,mess,json_result = run_main_rain_bar(fcst_list,starttime,endtime,cycl,areaid,ref,metric)
    print(json_result)



