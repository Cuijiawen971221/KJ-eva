import numpy as np
import subprocess
import xarray as xr
import os
import sys
import datetime 
#from gts_decoder_py import gts_decoder
import glob
import re
import shutil
import copy
from humidity_calc import calc_q, hum
from typeguard import typechecked
import config as cf
import pandas as pd
from clickhouse_util import clickclient

needID = ["AAXX","BBXX","OOXX","TTAA","UUAA","XXAA","IIAA"]

def mb_model():
    mb = {100000:[-999,-999,-999,-999,-999],
          92500:[-999,-999,-999,-999,-999],
          85000:[-999,-999,-999,-999,-999],
          70000:[-999,-999,-999,-999,-999],
          50000:[-999,-999,-999,-999,-999],
          40000:[-999,-999,-999,-999,-999],
          30000:[-999,-999,-999,-999,-999],
          25000:[-999,-999,-999,-999,-999],
          20000:[-999,-999,-999,-999,-999],
          15000:[-999,-999,-999,-999,-999],
          10000:[-999,-999,-999,-999,-999],
          7000:[-999,-999,-999,-999,-999],
          5000:[-999,-999,-999,-999,-999],
          1000:[-999,-999,-999,-999,-999]
            }
    return mb
    
def fill_fm35(data,dtime,mb,f,resdf):

    sid = str(data[0].split()[0])
    lon,lat = np.array(data[0].split()[1:3],dtype=np.float32)
    for d in data:
        tmp = np.array(d.split(),dtype=np.float32)
        if int(tmp[3]) in mb.keys():
            mb[int(tmp[3])]=[-999 if k==-888888 or k==-999999 else k for k in tmp[[7,9,5,11,13]]]
    outform = []
    for k in mb.keys():
        t = mb[k][0]
        td= mb[k][1]
        z = mb[k][2]
        ws= mb[k][3]
        wd= mb[k][4]
        q = calc_q(t,td,k,True)
        rh  = hum(float(t),float(td),float(k),True)
        if not all(v==-999 for v in [t,td,z,ws,wd,q,rh]):
            print(type(dtime))
            resdf.loc[len(resdf)] = {
                "longitude":lon, "latitude":lat,"observation_time":dtime,"message_type":"GTS","height":str(k//100),"temperature":t,\
                "humidity":rh,"wind_speed":ws,"wind_direction":wd,"geo_height":z,"dew_point_temperature":td,"observation_timestamp":dtime,\
                "station_code":str(sid)
            }
            outform= "{:s} ".format(sid)+"".join(["{:10.2f}" for i in range(8)]).format(lon,lat,k,\
                    t,q,z,ws,wd)
            f.write(outform)
            f.write("\n")
    return resdf


def trans_fm12(data):

    if len(data)==2:
        _v,_qc = float(data[0]),float(data[1])
        if _v == -888888:
            return -999,0
        else:
            return _v,_qc
    else:
        _v  = float(data)
        if _v == -888888:
            return -999
        else:
            return _v
def fill_fm12(data,dtime,f,resdf):
    time = data[0][330:340]
    if ">>>" in data[0]:
       callId = data[0].split(">>>")[1].split("FM")[0].strip()
    mslp,_qc = trans_fm12(data[0][344:364].split()) #海平面气压
    refp,_qc = trans_fm12(data[0][364:384].split()) #
    tsuf,_qc = trans_fm12(data[0][384:404].split()) #2m气温
    seat,_qc = trans_fm12(data[0][404:424].split()) #海平面气压
    surp,_qc = trans_fm12(data[0][424:444].split()) #场压
    rain,_qc = trans_fm12(data[0][444:464].split()) #降水量
    Tmax,_qc = trans_fm12(data[0][464:484].split()) #日最高温
    Tmin,_qc = trans_fm12(data[0][484:504].split()) #日最低温
    Tmin_night,_qc =trans_fm12(data[0][504:524].split()) #夜间最低温
    P3h ,_qc = trans_fm12(data[0][524:544].split()) #3小时变压
    P24h,_qc = trans_fm12(data[0][544:564].split()) #24小时变压
    ctot,_qc = trans_fm12(data[0][564:584].split()) #总运量
    hlow,_qc = trans_fm12(data[0][584:604].split()) #低云高

#    _data = data[1].split()
    sid  = data[1][:10].strip()
    lon  = trans_fm12(data[1][10:20])
    lat  = trans_fm12(data[1][20:30])
    mslp,_qc = trans_fm12(data[1][30:50].split())
    heig,_qc = trans_fm12(data[1][50:70].split())
    t2m,_qc  = trans_fm12(data[1][70:90].split())
    tdew,_qc = trans_fm12(data[1][90:110].split())
    w10m,_qc = trans_fm12(data[1][110:130].split())
    wd10m,_qc= trans_fm12(data[1][130:150].split())
 
    rh2  = hum(float(t2m),float(tdew),float(mslp)*100,True)
#    rh2,_qc = trans_fm12(data[1][190:210].split())
    wea_0 = -999
    vis = -999
    t_body = -999
    snow = -999
# unit trans
    mslp =mslp/100 if mslp!=-999 else -999 # hPa


# simple qc
    if sid[0] == "-":
        heig = 0.0
        sid = callId
    if lon >360 or lon< -180:
        lon = -999
    if lat >90 or lat < -90:
        lat = -999
    time = dtime.strftime("%Y%m%d%H")

    if not all(v==-999 for v in [t2m,tdew,mslp]):
        resdf.loc[len(resdf)] = {
            "longitude":lon, "latitude":lat,"observation_time":dtime,"message_type":"GTS","temperature":t2m,"dew_point_temperature":tdew,\
            "humidity":rh2,"wind_speed":w10m,"wind_direction":wd10m,"precipitation_24":-999,"precipitation":rain,"pressure":surp,"sea_level_pressure":mslp,\
            "radiation":-999,"visibility":vis,"total_cloud_cover":ctot,"low_cloud_cover":-999,"cloud_height":hlow,"observation_timestamp":dtime,\
            "station_code":f"{sid:<8}"
        }
        outform = f"{sid:<8} {time} {lon:.2f} {lat:.2f} {heig:.2f} {t2m:.2f} {rh2:.2f} {tdew:.2f} {wd10m:.2f} {w10m:.2f} {mslp:.2f} {wea_0:.2f} {vis:.2f} {ctot:.2f} {t_body:.2f} {rain:.2f} {snow:.2f}"
        f.write(outform+"\n")
    return resdf

#    print(data[1].split())
# this function decoder last hourly data GTS 
@typechecked
def GTS_decoder_allInOne(inpath:str,start_time:datetime.datetime,tmppath:str,binpath:str):

    tmppath = tmppath+"/"+start_time.strftime("%Y%m%d")
    filt = tmppath+ "/filter/"
    temp = tmppath+ "/decoder/TEMP/"
    synop = tmppath + "/decoder/SYNOP/"
    if not os.path.exists(tmppath):
        os.makedirs(filt)
        os.makedirs(temp)
        os.makedirs(synop)

    flist = []
    for t in np.linspace(0,0,1):
        pattern = (start_time-datetime.timedelta(hours=t)).strftime("%Y%m%d/*%d%H*.abj")
        if len(flist) == 0:
            flist = np.array(glob.glob(inpath+"/"+pattern))
        else:
            flist = np.concatenate((flist,np.array(glob.glob(inpath+"/"+pattern))) )

    outstr = start_time.strftime("%Y%m%d%H")
    outpath = outstr
    result = []

    fout = open(filt+outstr+".txt","w")

    for fl in flist:
        with open(fl,"r",errors="ignore") as f:
            data = f.read()
            match = re.search(r"ZCZC(.*?)NNNN",data,re.DOTALL)
            if match:
                result.append(match.group(0))
    for res in result:
        if any(sub in res for sub in needID):
            fout.write(res+"\n")
            
    fout.close()
    # print("{:s}/gts_decoder {:s} {:s} {:s}  > std_out 2>/dev/null".format(binpath,filt+outstr+".txt",outstr,str(600)))
    # 600 表示时间左右10分钟
    subprocess.call("{:s}/gts_decoder {:s} {:s} {:s}  > std_out 2>/dev/null".format(binpath,filt+outstr+".txt",outstr,str(600)),shell=True)
# move and delete file
    for file in glob.glob("{:s}/GTS{:s}.73[5678]".format(binpath,outpath)):
        shutil.copy(file,temp)
    for file in glob.glob("{:s}/GTS{:s}.71[234]".format(binpath,outpath)):
        shutil.copy(file,synop)
    for file in glob.glob("{:s}/GTS{:s}*".format(binpath,outpath)):
        os.remove(file)

@typechecked
def decoder_main(time:datetime.datetime)->tuple:#,path:str,tmppath:str,outpath:str):
    status = True
    mess = ""
    try:
        globalConf = cf.pparms("./pathconfig.yaml")
        path = globalConf.gtsorigpath
        tmppath = globalConf.gtstmppath
        outpath = globalConf.gtsoutputpath
        binpath = globalConf.gtsbinpath

        current_dir = os.getcwd()
        os.chdir(globalConf.gtsbinpath)
        GTS_decoder_allInOne(path,time,tmppath,binpath)
        os.chdir(current_dir)

        YYMMDDHH = time.strftime("%Y%m%d%H")
        YYMMDD = YYMMDDHH[:8]
        YY = YYMMDDHH[:4]

        bufr_path = outpath+f"/gtsbufr/{YY}/"
        if not os.path.exists(bufr_path):
            os.makedirs(bufr_path)
        synop_path = outpath+f"/gtssynop/{YY}/"
        if not os.path.exists(synop_path):
            os.makedirs(synop_path)

        fout_bufr = open(bufr_path+f"gtsbufr{YYMMDDHH}.txt","w")
        fout_synop = open(synop_path+f"gtssynop{YYMMDDHH}.txt","w")
        fout_synop.write("std_id  obstime  lon  lat  elv  t2  rh2  td2  dir  spd  psfc  wea-0  vis  tcld  t_body  rain  snow\n")

        tmpdf= {"longitude":[], "latitude":[],"observation_time":[],"message_type":[],"temperature":[],"dew_point_temperature":[],\
            "humidity":[],"wind_speed":[],"wind_direction":[],"precipitation_24":[],"precipitation":[],"pressure":[],"sea_level_pressure":[],\
            "radiation":[],"visibility":[],"total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"observation_timestamp":[],\
            "station_code":[]}
        resdfFm12= pd.DataFrame(tmpdf)

        tmpdf= {"longitude":[], "latitude":[],"observation_time":[],"message_type":[],"height":[],"temperature":[],\
            "humidity":[],"wind_speed":[],"wind_direction":[],"geo_height":[],"dew_point_temperature":[],"observation_timestamp":[],\
            "station_code":[]}
        resdfFm35= pd.DataFrame(tmpdf)
        with open(tmppath+"/{:s}/decoder/TEMP/GTS{:s}.735".format(YYMMDD,YYMMDDHH),errors="ignore") as f:
            data = f.read().split("YUNYAO")
            for tmp in data[1:]:
                tt = tmp.split("\n")
                # get good station 
                if np.array(tt[-3].split(),dtype=np.float32)[4]>1:
                    resdfFm35 = fill_fm35(tt[1:-3],time,mb_model(),fout_bufr,resdfFm35)

        with open(tmppath+"/{:s}/decoder/SYNOP/GTS{:s}.712".format(YYMMDD,YYMMDDHH),errors="ignore") as f:
            data = f.read().split("YUNYAO")
            for tmp in data[1:]:
                tt = tmp.split("\n")
                resdfFm12 = fill_fm12(tt,time,fout_synop,resdfFm12)

        with open(tmppath+"/{:s}/decoder/SYNOP/GTS{:s}.713".format(YYMMDD,YYMMDDHH),errors="ignore") as f:
            data = f.read().split("YUNYAO")
            for tmp in data[1:]:
                tt = tmp.split("\n")
                resdfFm12 = fill_fm12(tt,time,fout_synop,resdfFm12)

        fout_bufr.close()
        fout_synop.close()

        t1 = datetime.datetime.now()
        print(resdfFm12)
        batch_size = 100
        for i in range(0, len(resdfFm12), batch_size):
            batch = resdfFm12.iloc[i:i + batch_size]
            clickclient.insert_df("surface_observation_data", batch)
        print(datetime.datetime.now() - t1)

        t1 = datetime.datetime.now()
        print(resdfFm35)
        batch_size = 100
        for i in range(0, len(resdfFm35), batch_size):
            batch = resdfFm35.iloc[i:i + batch_size]
            clickclient.insert_df("upper_observation_data", batch)
        print(datetime.datetime.now() - t1)

    except Exception as e:
        status = False
        mess = str(e)
    return status,mess


if __name__ == "__main__":
    time = datetime.datetime.strptime("2025041700","%Y%m%d%H")

    decoder_main(time,"/home/devopler/workshop/met_backend/orig/GTS","./tmp/data","/home/devopler/workshop/met_backend/obs")

#    GTS_decoder_allInOne("/home/yunyao/workshop/met/yunyao/orig/GTS",time,"./tmp/data")
##    time = dt.datetime.strptime("2025041612","%Y%m%d%H")
##    GTS_decoder_allInOne("/home/yunyao/workshop/met/yunyao/orig/GTS",time,"./tmp/data")
#
#    with open("./tmp/data/20250416/decoder/TEMP/GTS2025041612.735",errors="ignore") as f:
#        data = f.read().split("YUNYAO")
#        for tmp in data[1:]:
#            tt = tmp.split("\n")
#            # get good station 
#            if np.array(tt[-3].split(),dtype=np.float32)[4]>1:
#                fill_fm35(tt[1:-3],mb_model())
#    with open("./tmp/data/20250416/decoder/SYNOP/GTS2025041612.712",errors="ignore") as f:
#        data = f.read().split("YUNYAO")
#        for tmp in data[1:]:
#            tt = tmp.split("\n")
#            fm12_res = fill_fm12(tt)
#            print(fm12_res)
