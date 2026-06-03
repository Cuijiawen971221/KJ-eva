############### THE STATS FOR PLEV Vars ########################
##### #######################
##### ###################################
################################################################
# 20250814 modify

import eccodes
import numpy as np
from nwpc_data.grib.eccodes import load_message_from_file
from scipy.ndimage.filters import uniform_filter
from sklearn import metrics
import datetime
from datetime import timezone
import os
import sys
import math
from typeguard import typechecked
from typing import Tuple,Union
import xesmf as xe
import xarray as xr
import config as cf
import glob
import clickhouse_connect
from grid_proc import getAWSindex
import pandas as pd 
import pickle 
from py2java import *
import warnings
from grid_proc import point_ncep,point_kt1279,point_ecmwf,point_allInone
import utils
from clickhouse_util import clickclient
import grib2io
import grib_dict
import time


warnings.filterwarnings("ignore",category=RuntimeWarning)

globalConf = cf.pparms("./pathconfig.yaml").param


def queryregion():
    sql = f"""
    SELECT id, region_name, region_code, left_top_lon, left_top_lat, right_bottom_lon, right_bottom_lat FROM szybjydb.sys_region_config
    """
    region_list = clickclient.query_df(sql)
    name = ",".join([re for re in region_list["id"]])

    return name      
    
# 获取区域位置信息
# 从数据库获取
def getregion(name):
    sql = f"""
        SELECT id, region_name, region_code, left_top_lon, left_top_lat, right_bottom_lon, right_bottom_lat FROM szybjydb.sys_region_config
        """
    region_list = clickclient.query_df(sql)
    print(region_list)    
    result = []
    for n in name:
        line = region_list[region_list["id"]==n]
        region_list[["left_top_lon","right_bottom_lon"]].iloc[0].astype(np.float32).to_list()
        result.append(line[["right_bottom_lat","left_top_lat","left_top_lon","right_bottom_lon"]].iloc[0].astype(np.float32).to_list())
    return result

# 获取检验路径信息
def plev_config(fcst,ref,mode):
    cmeanroot = globalConf.plevcmeanroot
    fcstroot = globalConf.plevfcstroot+"/{:s}/".format(fcst)
    if ref == "ERA5":
        outputroot = globalConf.plevoutputroot+"/plev/{:s}/{:s}/{:s}".format(fcst,ref,mode)
        analroot= globalConf.plevfcstroot+"/{:s}/".format(ref)
        obsroot = ""
    elif ref == "SELF":
        outputroot = globalConf.plevoutputroot+"/plev/{:s}/{:s}/{:s}".format(fcst,ref,mode)
        analroot = globalConf.plevfcstroot+"/{:s}/".format(fcst)
        obsroot = ""
    elif ref == "BUFR":
        outputroot = globalConf.plevoutputroot+"/plev/{:s}/{:s}/{:s}".format(fcst,ref,mode)
        analroot = ""
        obsroot = globalConf.plevobsroot

    return fcstroot,analroot,outputroot,cmeanroot,obsroot

def surf_config(fcst,ref):
    fcstroot = globalConf.surffcstroot+"/{:s}/".format(fcst)
    if ref == "CLDAS":
        #outputroot = globalConf.plevoutputroot+"/plev/{:s}/{:s}/{:s}".format(fcst,ref,mode)
        analroot= globalConf.surfobsroot+"/{:s}/".format(ref)
    elif ref == "ERA5":
        analroot= globalConf.surfobsroot+"/{:s}/".format(ref)

    return fcstroot,analroot

def modify_date(ifcst,cdate,dd):
    if ifcst=="KT1279":
        if dd<12:
            cdate = cdate -datetime.timedelta(hours=dd)
        else:
            cdate = cdate - datetime.timedelta(hours=dd-12)
            dd = dd -12
    elif ifcst=="NCEP":
        if dd<12:
            cdate = cdate - datetime.timedelta(hours=dd)
        else:
            cdate = cdate - datetime.timedelta(hours=dd-12)
            dd = dd -12
    elif ifcst=="ECMWF":
        if dd<12:
            cdate = cdate -datetime.timedelta(hours=dd)
        else:
            cdate = cdate - datetime.timedelta(hours=dd-12)
            dd = dd -12
    else:
        if dd<12:
            cdate = cdate -datetime.timedelta(hours=dd)
        else:
            cdate = cdate - datetime.timedelta(hours=dd-12)
            dd = dd -12
    return cdate,dd

def point_config(fcst,ref,mode):
    if fcst == "KT1279":
        fcstroot = globalConf.kt1279awspoint
        outputroot = globalConf.kt1279metpath
        obsroot = globalConf.kt1279obspath
    elif fcst == "NCEP":
        fcstroot = globalConf.ncepawspoint
        outputroot = globalConf.ncepmetpath+"/pointsrf/NCEP/"
        obsroot = globalConf.ncepobspath
    elif fcst == "ECMWF":
        fcstroot = globalConf.ecmwfawspoint
        outputroot = globalConf.ecmwfmetpath
        obsroot = globalConf.ecmwfobspath
    elif fcst=="CMA_GFS":
        fcstroot = globalConf.cmagfsawspoint
        outputroot = globalConf.cmagfsmetpath
        obsroot = globalConf.cmagfsmetpath
    elif fcst == "KT1279_CLOUD":
        fcstroot = globalConf.kt1279cloudawspoint
        outputroot = globalConf.kt1279cloudmetpath
        obsroot = globalConf.kt1279cloudmetpath
    elif fcst == "AUTO":
        fcstroot = globalConf.autoawspoint
        outputroot = globalConf.autometpath
        obsroot = globalConf.autometpath
    elif fcst == "VISFCST":
        fcstroot = globalConf.visfcstawspoint
        outputroot = globalConf.visfcstmetpath
        obsroot = globalConf.visfcstmetpath
    elif fcst == "REGION":
        fcstroot = globalConf.regionawspoint
        outputroot = globalConf.regionmetpath
        obsroot = globalConf.regionmetpath
    elif fcst == "KJRH":
        fcstroot = globalConf.kjrhawspoint
        outputroot = globalConf.kjrhmetpath
        obsroot = globalConf.kjrhmetpath
    return fcstroot,outputroot,obsroot
    
def check_file_exist(file):
    if not os.path.exists(file):
        print(f"{file} not exists")
        return True
    else:
        return False

def getfcstroot(fcst):
    if fcst == "KT1279":
        fcstroot = globalConf.kt1279fcstpath
    else:
        pass
    return fcstroot

def insert_orig_fcst(data):
    columns=["forecast_date","forecast_hour","mode_type","forecast_interval","height","meteorological_element_type",
    "unit","file_path"]
    clickclient.insert('szybjydb.forecast_metadata_info',data,column_names=columns)


# 预报数据齐套性检验
@typechecked
def yunyao_check_fcst_orig(starttime:datetime.datetime,ifcst:str):
    #now = datetime.datetime.now()+datetime.timedelta(hours=-8)
#   now = datetime.datetime.strptime("2025050512","%Y%m%d%H")
    YYYYMMDDHH = starttime.strftime("%Y%m%d%H")
    YYYY_MM_DD = starttime.strftime("%Y-%m-%d")
    YYYYMMDD = YYYYMMDDHH[:8]
    YYYY = YYYYMMDDHH[:4]
    HH = YYYYMMDDHH[8:]

    utc_starttime = starttime-datetime.timedelta(hours=0)
    UTCYYYYMMDDHH = utc_starttime.strftime("%Y%m%d%H")
    UTCYYYYMMDD = UTCYYYYMMDDHH[:8]
    UTCYYYY = UTCYYYYMMDDHH[:4]
    UTCHH = UTCYYYYMMDDHH[8:]
    
    filelist =[]
    flag = False
    conf = globalConf
    #rint(now,starttime - datetime.timedelta(hours=3))
    if True: # now > starttime - datetime.timedelta(hours=3):
        if ifcst == "KT1279":
            minfile = 999
            need_count = {"HH":0,"UU":0,"VV":0,"TT":0,"T2":0,"RH":0,"UT":0,"VT":0}
            for pp in need_count.keys():
                fcstroot = conf.kt1279fcstpath+"/KT1279/{:s}/*{:s}G*.grb".format(YYYYMMDDHH,pp)
                filelist = glob.glob(fcstroot)
                need_count[pp] = len(filelist)
                if minfile >  need_count[pp]:
                    minfile = need_count[pp]  
            print(need_count)      
            print(minfile)
            if minfile < conf.kt1279th:###### TODO#######
                pass
            else:
                flag = True
        if ifcst == "ECMWF":
            fcstroot = conf.ecmwffcstpath+ "/ECMWF/{:s}/W_NAFP_C_ECMF_{:s}*001".format(YYYYMMDDHH,YYYYMMDD)
            print(fcstroot)
            filelist = glob.glob(fcstroot)   
            print(filelist)
            if len(filelist)<conf.ecmwfth:
                pass
            else:
                for fl in filelist:
                    pass
                flag = True
        if ifcst == "NCEP":
            fcstroot = conf.ncepfcstpath+ "/NCEP/{:s}/W_NAFP_C_KWBC_{:s}*t{:s}z.*bin".format(YYYYMMDD,YYYYMMDD,HH)
            filelist = glob.glob(fcstroot)
            if len(filelist)<conf.ncepth:
                pass
            else:
                pass
                flag=True               
        if ifcst == "CLDAS":
            fcstroot = conf.ncepfcstpath+ "/CLDAS/{:s}/Z_NAFP_C_BABJ_{:s}*HOR-*.nc".format(UTCYYYYMMDD,UTCYYYYMMDDHH)
            filelist = glob.glob(fcstroot)
            print(filelist)
            if len(filelist)<conf.cldasth:
                pass
            else:
                pass
                flag=True               

        if ifcst == "AUTO":
            minfile = 999
            need_count = {"CBH":0,"D2":0,"HH":0,"LC":0,"PS":0,"RH":0,"TT":0,"UU":0}
            for pp in need_count.keys():
                fcstroot = conf.autofcstpath+"/AUTO/{:s}/KT{:s}*{:s}.*".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp] = len(filelist)
                if minfile >  need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            if minfile < conf.autoth:###### TODO#######
                pass
            else:
                pass
                flag = True
        if ifcst == "KT1279_CLOUD":
            minfile = 999
            need_count = {"CB":0,"TF":0,"LC":0}
            for pp in need_count.keys():
                fcstroot = conf.autofcstpath+"/KT1279_CLOUD/{:s}/KCR1{:s}*{:s}*".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp] = len(filelist)
                if minfile >  need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            if minfile < conf.kt1279cloudth:###### TODO#######
                pass
            else:
                pass
                flag = True
        if ifcst == "CLIMATE":
            fcstroot = conf.climatefcstpath+ "/CLIMATE/{:s}/F1.4-{:s}.famil.daily-ensmean.*".format(YYYY_MM_DD,YYYYMMDD)
            filelist = glob.glob(fcstroot)
            print("asdfasdf",fcstroot)
            print(conf.climateth)
            print(filelist)
            if len(filelist)<conf.climateth:
                pass
            else:
                pass
                flag=True
        if ifcst == "ERA5":
            fcstroot = conf.era5fcstpath+"/ERA5/*/{:s}/ERA5*{:s}*".format(YYYYMMDD,YYYYMMDDHH)
            print(fcstroot)
            filelist = glob.glob(fcstroot)
            print(filelist)
            if len(filelist)<conf.era5th:
                pass
            else:
               flag = True 
        if ifcst == "VISFCST":
            minfile = 999
            need_count = {"VS":0}
            for pp in need_count.keys():
                # fcstroot = conf.autofcstpath+"/VIS/{:s}/KT{:s}*{:s}.*".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                fcstroot = conf.autofcstpath+"/VISFCST/{:s}/KV{:s}{:s}*".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp] = len(filelist)
                if minfile >  need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            # if minfile < conf.autoth:###### TODO#######
            if minfile < 48:###### TODO#######
                pass
            else:
                pass
                flag = True
        if ifcst == "REGION":
            minfile = 999
            # ["VS","UT","VT","TS","PS","LC","D2"]
            need_count = {"VS":0,"UT":0,"VT":0,"TS":0,"PS":0,"LC":0,"D2":0}
            for pp in need_count.keys():
                fcstroot = conf.regionfcstpath+"/REGION/{:s}/KW{:s}{:s}999*.grb".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp]=len(filelist)
                if minfile > need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            if minfile < conf.regionth:###### TODO#######
                pass
            else:
                pass
                flag = True
        
        if ifcst == "KJRH":
            minfile = 999
            need_count = {"CBH":0,"CLD":0,"D10":0,"GPH":0,"RH2":0,"RHU":0,"T2M":0,"TD2":0,"TEM":0,"UWND":0,"VWND":0,"VIS":0,"W10":0}
            for pp in need_count.keys():
                fcstroot = conf.kjrhfcstpath+f"/KJRH/{YYYYMMDDHH}/NAFP_KDSZ_KHMA_{YYYYMMDDHH}0000-{pp}-EAI-*.NC"
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp]=len(filelist)
                if minfile > need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            
            if minfile < 70:
                pass
            else:
                pass
                flag = True
        
        
        if ifcst == "CMA_GFS":
               
            fcstroot = conf.cmagfsfcstpath+ "/CMA_GFS/*/Z_NAFP_C_BABJ_{:s}*".format(YYYYMMDD,YYYYMMDDHH)
            #fcstroot = conf.cmagfsfcstpath+ "/CMA_GFS/{:s}*/Z_NAFP_C_BABJ_{:s}*".format(YYYYMMDD,YYYYMMDDHH)
            print(fcstroot)
            filelist = glob.glob(fcstroot)
            print(len(filelist))
            if len(filelist)<conf.cmagfsth:
                pass
            else:
                pass
                flag=True
        if ifcst == "EMEND":
            minfile = 999
            need_count = {"CLC":0,"PRC":0,"T2C":0,"UMC":0,"VMC":0}
            for pp in need_count.keys():
                fcstroot = conf.emendfcstpath+"/EMEND/{:s}/{:s}/*{:s}*.TXT".format(YYYYMMDDHH,pp,YYYYMMDDHH)
                print(fcstroot)
                filelist = glob.glob(fcstroot)
                need_count[pp]=len(filelist)
                if minfile > need_count[pp]:
                    minfile = need_count[pp]
            print(need_count)
            print(minfile)
            if minfile < conf.emendth:###### TODO#######
                pass
            else:
                pass
                flag = True

    return flag

@typechecked
def yunyao_point_area_parallel(starttime:datetime.datetime,endtime:datetime.datetime,ifcst:str,iref:str,iregion:list,ipara:list,fh:list,itimedelta:int,domain,obs,iii)->tuple:
    print("############################ yunyao_point_area_parallel, process: ",iii)
    time.sleep(iii)
    status=True
    mess = ""
    atleastOne = 0
    ########################dirroot##################################
    #TODO : 业务中如何获取这些数据？
    fcstroot,outputroot,obsroot = point_config(ifcst,iref,"stats")
    
    region = iregion
    # TODO : 业务中如何获取这些区域信息
    domain =getregion(iregion)
    
    VAR = ipara #[t,r,td,10u,10v,wind,p,sf]
    lat = np.arange(90, -90 - 1.5, -1.5)
    lon = np.arange(0, 360, 1.5)
    llon, llat = np.meshgrid(lon, lat)
      
    cdate = starttime
    obsdate = starttime
    # read fcst data
    tmpdf= {"mode_type":[], "reference_data_type":[],"level":[],"meteorological_element_type":[],"area_id":[],"forecast_time":[],\
            "forecast_hour":[],"forecast_interval":[],"pc":[],"acc":[],"rmse":[],"mae":[],"level":[],"ts":[],"ets":[],"mar":[],"far":[],}
    resdf = pd.DataFrame(tmpdf)


    try:
        #outputdate=outputroot+"aws_region"+str(cdate.strftime("%Y%m%d%H"))
        #ofile = open(outputdate, "w")
        #ofile.write("TIME      REGION      RMSE      BIAS     ABIAS")
        #ofile.write(' \r\n')

        dd = cdate.hour

        cdate,dd = modify_date(ifcst,cdate,dd)
        ccdate = cdate
        print(cdate,dd)

        #    ###### read obs ###########################
        #    ###### read from clickhouse ###############
        #    ppp = ",".join([pyweb2java(var) for var in VAR])
        #    print(ppp)
        #    sql = f"""
        #            SELECT {ppp}, station_code, longitude, latitude, message_type FROM surface_observation_data 
        #            WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
        #    """
        #    obs = clickclient.query_df(sql)
        #    print(obs)
        if len(obs)==0:
            raise Exception("观测数据为空，无法进行后续处理。")
        ##############################
        if iref == "AWS":
            obs = obs[(obs["message_type"] == "aws" )|(obs["message_type"]== "foreign")]
        elif iref == "GTS":
            obs = obs[obs["message_type"] == "surf_bufr"]
        
        #else:
        #    if not os.path.exists(outputroot+f"{obsdate.strftime('%Y-%m-%d %H:%M:%S')}.pkl"):
        #        continue
        #    else:
        #        with open(outputroot+f"{obsdate.strftime('%Y-%m-%d %H:%M:%S')}.pkl","rb") as f:
        #            obs = pickle.load(f)
        print(obs)
    ###################################################################
        if obs.shape[0]!=0 and obs.shape[1]!=0:
            renameColumn = {"station_code": "ID"}
            for var in VAR:
                renameColumn[pyweb2java(var)]=f"{var}obs"
    ########################################################
            print(renameColumn)
            obs = obs.rename(columns=renameColumn)
            #print(obs[["ID","longitude","latitude"]])
            station = xr.Dataset({
                "0000id": ("station", obs["ID"].values),  # 显式指定维度名 "station"
                "lat": ("station", obs["latitude"].values),
                "lon": ("station", obs["longitude"].values)
            })
            obs = obs.set_index("ID")
            print(obs)
        else:
            obs = np.array([])


        longTimestr = datetime.datetime.now()
        longTimestr = longTimestr.strftime("%Y%m%d%H%M%S")
        tmpweight = f"{obsdate.strftime('%Y%m%d%H')}-{ifcst}-{iref}-{longTimestr}.nc"
        for i in range(fh[0],fh[1]+1,int(itimedelta)):
            print(i)
            rmse=-999;bias=-999;abias=-999;far=-999;mar=-999;ts=-999;ets=-999
            #obsdate=cdate - datetime.timedelta(hours=i)
        #######################read fcst in the first time step#######################
            cdate = ccdate - datetime.timedelta(hours=i)
            print(ccdate,cdate,dd)
            if obs.shape[0] >0:
                # all in one
                ppppp = ",".join(ipara).replace("wind","10u,10v").split(",")
                ppppp = ",".join(ppppp).replace("wdir","wind,10u,10v").split(",") #检验风向必须检验风速
                ppppp = np.unique(ppppp).tolist()
                _,_,fcst = point_allInone(cdate, ifcst, ppppp, [i + dd, i + dd], 1, tmpweight, station)

                fcst = fcst.set_index("ID")
            else:
                fcst = np.array([])

            print("fcst",fcst)
            if fcst.shape[0] > 0 and obs.shape[0] > 0:
                atleastOne +=1
                for jj, dm in enumerate(domain):
                    result = obs.join(fcst)
                    
                    # result = result.dropna(subset=["latitude","lat"])
                    if (result.shape[0] > 0):
                        tmp1 = result[((result["latitude"] > dm[0]) & (result["latitude"] < dm[1]) & (
                                    result["longitude"] > dm[2]) & (result["longitude"] < dm[3]))]
                        tmp1 = tmp1.replace(-999.00, np.nan)
                        if tmp1.shape[0]>0:
                            print("var",VAR)
                            for var in VAR:
                                pc= -999;
                                rmse = -999;
                                bias = -999;
                                abias = -999;
                                far = [];
                                mar = [];
                                ts = [];
                                ets = []

                                if var in tmp1.columns and var+"obs" in tmp1.columns:
                                    if var == "wind":
                                        
                                        tmp2 = tmp1.dropna(subset=[var + "obs", "u10", "v10"])
                                        tmp3 = np.sqrt(tmp2["u10"]**2+tmp2["v10"]**2 -(tmp2[var+"obs"].astype(np.float64))**2)
                                        tmp2["wind"] = np.sqrt(tmp2["u10"]**2+tmp2["v10"]**2)
                                    elif var == "wdir":
                                        tmp2 = tmp1.dropna(subset=[var + "obs", "u10", "v10"])
                                        windobs = np.array(tmp2["windobs"],dtype = np.float64)
                                        wdirobs = np.array(tmp2["wdirobs"],dtype = np.float64)

                                        anu = -windobs*np.sin(wdirobs/180*np.pi)
                                        anv = -windobs*np.cos(wdirobs/180*np.pi)
                                        fcu = np.array(tmp2["u10"],dtype=np.float64)
                                        fcv = np.array(tmp2["v10"],dtype=np.float64)
                                        tmp2["wdir"] = utils.getWindWdirArray(-fcu,-fcv)[1]
                                        fc = np.sqrt(fcu**2+fcv**2)
                                        ana = np.sqrt(anu**2+anv**2)

                                        tmp = (fcu * anu + fcv * anv) / (fc * ana)

                                        tmp[np.where(tmp > 1)] = 1
                                        tmp3 = np.arccos(tmp) * 180 / np.pi

                                    else:
                                        tmp2 = tmp1.dropna(subset=[var, var + "obs"])
                                        if var == "rad":
                                            print(tmp2[[var,var+"obs"]]) 
                                        tmp3 = tmp2[var].astype(np.float64)-tmp2[var+"obs"].astype(np.float64)
                                    ooobs = np.ma.array(tmp2[[var+"obs"]],dtype = np.float64)
                                    fcstt = np.ma.array(tmp2[[var]],dtype = np.float64)
                                    aambb = np.ma.array(tmp3,dtype = np.float64)
                                    lat = np.ma.array(tmp2["latitude"],dtype = np.float64)
                                    #print("cgcgcgcgcgcgcgcgcgcgcgcgcgcgcgcgccg")
                                    pc,ts,ets,far,mar,rmse,bias,abias=utils.calcTCPC(ooobs,fcstt,aambb,lat,utils.pcth,var,"aws")


                                if ts == [] :  ts=[(np.nan,np.nan)]
                                if ets == [] :  ets=[(np.nan,np.nan)]
                                if mar == [] :  mar=[(np.nan,np.nan)]
                                if far == [] :  far=[(np.nan,np.nan)]


                                if np.isnan([rmse, abias]).all() and np.isnan(ts).all() :
                                    pass
                                else:
                                    for dfi in range(len(ts)):
                                        if pc == -999: pc = np.nan
                                        if rmse == -999: rmse = np.nan
                                        if abias == -999: abias = np.nan
                                        resdf.loc[len(resdf)] = {"mode_type": pyweb2java(ifcst),
                                                                 "reference_data_type": pyweb2java(iref), "level": ts[dfi][0],
                                                                 "meteorological_element_type": pyweb2java(var), \
                                                                 "area_id": region[jj], "forecast_time": cdate,
                                                                 "forecast_hour": cdate.strftime("%H"),
                                                                 "forecast_interval": i+dd,
                                                                 "pc": pc , "acc": np.nan, \
                                                                 "rmse": rmse, "mae": abias, \
                                                                 "ts": ts[dfi][1], "mar": mar[dfi][1], \
                                                                 "far": far[dfi][1], "ets": bias}


                        else:
                            mess += f"obs and fcst not match\r\n"
    except:
        status = False

    if mess == "":
        mess = "succeed"
    if atleastOne==0:
        status=False
        mess="all met failed, retry again"
    print("我要返回啦")
    return status,mess,resdf


# 站点区域地面检验
@typechecked
def yunyao_point_area(starttime:datetime.datetime,endtime:datetime.datetime,ifcst:str,iref:str,iregion:list,ipara:list,itimedelta:int,ilength:int)->tuple:
    status=True
    mess = ""
    atleastOne = 0
    ########################dirroot##################################
    #TODO : 业务中如何获取这些数据？
    fcstroot,outputroot,obsroot = point_config(ifcst,iref,"stats")
    
    region = iregion
    # TODO : 业务中如何获取这些区域信息
    domain =getregion(iregion)
    
    VAR = ipara #[t,r,td,10u,10v,wind,p,sf]
    length = ilength
    lat = np.arange(90, -90 - 1.5, -1.5)
    lon = np.arange(0, 360, 1.5)
    llon, llat = np.meshgrid(lon, lat)
      
    cdate = starttime
    obsdate = starttime
    # read fcst data
    while True:
        #outputdate=outputroot+"aws_region"+str(cdate.strftime("%Y%m%d%H"))
        #ofile = open(outputdate, "w")
        #ofile.write("TIME      REGION      RMSE      BIAS     ABIAS")
        #ofile.write(' \r\n')
        tmpdf= {"mode_type":[], "reference_data_type":[],"level":[],"meteorological_element_type":[],"area_id":[],"forecast_time":[],\
            "forecast_hour":[],"forecast_interval":[],"pc":[],"acc":[],"rmse":[],"mae":[],"level":[],"ts":[],"ets":[],"mar":[],"far":[],}
        resdf = pd.DataFrame(tmpdf)

        dd = cdate.hour

        cdate,dd = modify_date(ifcst,cdate,dd)
        ccdate = cdate
        print(cdate,dd)

        ###### read obs ###########################
        ###### read from clickhouse ###############
        ppp = ",".join([pyweb2java(var) for var in VAR])
        print(ppp)
        sql = f"""
                SELECT {ppp}, station_code, longitude, latitude, message_type FROM surface_observation_data 
                WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
        """
        obs = clickclient.query_df(sql)
        print(obs)
        if len(obs)==0: break
        ##############################
        if iref == "AWS":
            obs = obs[(obs["message_type"] == "aws" )|(obs["message_type"]== "foreign")]
        elif iref == "GTS":
            obs = obs[obs["message_type"] == "surf_bufr"]
        
        #else:
        #    if not os.path.exists(outputroot+f"{obsdate.strftime('%Y-%m-%d %H:%M:%S')}.pkl"):
        #        continue
        #    else:
        #        with open(outputroot+f"{obsdate.strftime('%Y-%m-%d %H:%M:%S')}.pkl","rb") as f:
        #            obs = pickle.load(f)
        print(obs)
    ###################################################################
        if obs.shape[0]!=0 and obs.shape[1]!=0:
            renameColumn = {"station_code": "ID"}
            for var in VAR:
                renameColumn[pyweb2java(var)]=f"{var}obs"
    ########################################################
            print(renameColumn)
            obs = obs.rename(columns=renameColumn)
            #print(obs[["ID","longitude","latitude"]])
            station = xr.Dataset({
                "0000id": ("station", obs["ID"].values),  # 显式指定维度名 "station"
                "lat": ("station", obs["latitude"].values),
                "lon": ("station", obs["longitude"].values)
            })
            obs = obs.set_index("ID")
            print(obs)
        else:
            obs = np.array([])


        longTimestr = datetime.datetime.now()
        longTimestr = longTimestr.strftime("%Y%m%d%H%M")
        tmpweight = f"{obsdate.strftime('%Y%m%d%H')}-{ifcst}-{iref}-{longTimestr}.nc"
        for i in range(0,int(itimedelta*ilength)+1,int(itimedelta)):
            print(i)
            rmse=-999;bias=-999;abias=-999;far=-999;mar=-999;ts=-999;ets=-999
            #obsdate=cdate - datetime.timedelta(hours=i)
        #######################read fcst in the first time step#######################
            cdate = ccdate - datetime.timedelta(hours=i)
            print(ccdate,cdate,dd)
            if obs.shape[0] >0:
                # all in one
                ppppp = ",".join(ipara).replace("wind","10u,10v").split(",")
                ppppp = ",".join(ppppp).replace("wdir","wind,10u,10v").split(",") #检验风向必须检验风速
                ppppp = np.unique(ppppp).tolist()
                _,_,fcst = point_allInone(cdate, ifcst, ppppp, [i + dd, i + dd], 1, tmpweight, station)

                fcst = fcst.set_index("ID")
            else:
                fcst = np.array([])

            print("fcst",fcst)
            if fcst.shape[0] > 0 and obs.shape[0] > 0:
                atleastOne +=1
                for jj, dm in enumerate(domain):
                    result = obs.join(fcst)
                    
                    # result = result.dropna(subset=["latitude","lat"])
                    if (result.shape[0] > 0):
                        tmp1 = result[((result["latitude"] > dm[0]) & (result["latitude"] < dm[1]) & (
                                    result["longitude"] > dm[2]) & (result["longitude"] < dm[3]))]
                        tmp1 = tmp1.replace(-999.00, np.nan)
                        if tmp1.shape[0]>0:
                            print("var",VAR)
                            for var in VAR:
                                pc= -999;
                                rmse = -999;
                                bias = -999;
                                abias = -999;
                                far = [];
                                mar = [];
                                ts = [];
                                ets = []

                                if var in tmp1.columns and var+"obs" in tmp1.columns:
                                    if var == "wind":
                                        
                                        tmp2 = tmp1.dropna(subset=[var + "obs", "u10", "v10"])
                                        tmp3 = np.sqrt(tmp2["u10"]**2+tmp2["v10"]**2 -(tmp2[var+"obs"].astype(np.float64))**2)
                                        tmp2["wind"] = np.sqrt(tmp2["u10"]**2+tmp2["v10"]**2)
                                    elif var == "wdir":
                                        tmp2 = tmp1.dropna(subset=[var + "obs", "u10", "v10"])
                                        windobs = np.array(tmp2["windobs"],dtype = np.float64)
                                        wdirobs = np.array(tmp2["wdirobs"],dtype = np.float64)

                                        anu = -windobs*np.sin(wdirobs/180*np.pi)
                                        anv = -windobs*np.cos(wdirobs/180*np.pi)
                                        fcu = np.array(tmp2["u10"],dtype=np.float64)
                                        fcv = np.array(tmp2["v10"],dtype=np.float64)
                                        tmp2["wdir"] = utils.getWindWdirArray(-fcu,-fcv)[1]
                                        fc = np.sqrt(fcu**2+fcv**2)
                                        ana = np.sqrt(anu**2+anv**2)

                                        tmp = (fcu * anu + fcv * anv) / (fc * ana)

                                        tmp[np.where(tmp > 1)] = 1
                                        tmp3 = np.arccos(tmp) * 180 / np.pi

                                    else:
                                        tmp2 = tmp1.dropna(subset=[var, var + "obs"])
                                        if var == "rad":
                                            print(tmp2[[var,var+"obs"]]) 
                                        tmp3 = tmp2[var].astype(np.float64)-tmp2[var+"obs"].astype(np.float64)
                                    ooobs = np.ma.array(tmp2[[var+"obs"]],dtype = np.float64)
                                    fcstt = np.ma.array(tmp2[[var]],dtype = np.float64)
                                    aambb = np.ma.array(tmp3,dtype = np.float64)
                                    lat = np.ma.array(tmp2["latitude"],dtype = np.float64)
                                    #print("cgcgcgcgcgcgcgcgcgcgcgcgcgcgcgcgccg")
                                    pc,ts,ets,far,mar,rmse,bias,abias=utils.calcTCPC(ooobs,fcstt,aambb,lat,utils.pcth,var,"aws")


                                if ts == [] :  ts=[(np.nan,np.nan)]
                                if ets == [] :  ets=[(np.nan,np.nan)]
                                if mar == [] :  mar=[(np.nan,np.nan)]
                                if far == [] :  far=[(np.nan,np.nan)]


                                if np.isnan([rmse, abias]).all() and np.isnan(ts).all():
                                    pass
                                else:
                                    for dfi in range(len(ts)):
                                        if pc == -999: pc = np.nan
                                        if rmse == -999: rmse = np.nan
                                        if abias == -999: abias = np.nan
                                        resdf.loc[len(resdf)] = {"mode_type": pyweb2java(ifcst),
                                                                 "reference_data_type": pyweb2java(iref), "level": ts[dfi][0],
                                                                 "meteorological_element_type": pyweb2java(var), \
                                                                 "area_id": region[jj], "forecast_time": cdate,
                                                                 "forecast_hour": cdate.strftime("%H"),
                                                                 "forecast_interval": i+dd,
                                                                 "pc": pc , "acc": np.nan, \
                                                                 "rmse": rmse, "mae": abias, \
                                                                 "ts": ts[dfi][1], "mar": mar[dfi][1], \
                                                                 "far": far[dfi][1], "ets": bias}


                        else:
                            mess += f"obs and fcst not match\r\n"

        break
    t1 = datetime.datetime.now()
    print(resdf.to_string())
    batch_size = 100000
    for i in range(0, len(resdf), batch_size):
        batch = resdf.iloc[i:i + batch_size]
        clickclient.insert_df("surface_area_verification_result", batch)
    print(datetime.datetime.now() - t1)

    if mess == "":
        mess = "succeed"
    if atleastOne==0:
        status=False
        mess="all met failed, retry again"

    return status,mess
# 格点区域地面检验
@typechecked
def yunyao_surf_pre_parallel(starttime:datetime.datetime,endtime:datetime.datetime, ifcst:str, iref:str, iregion:list, ipara:list,fh:list,itimedelta, domain)->tuple:
    status = True
    mess = ""
    tmpdf = {"mode_type": [], "reference_data_type": [], "level": [], "meteorological_element_type": [], "area_id": [],
             "forecast_time": [], \
             "forecast_hour": [], "forecast_interval": [], "pc": [], "acc": [], "rmse": [], "mae": [], "level": [],
             "ts": [], "ets": [], "mar": [], "far": [], }
    resdf = pd.DataFrame(tmpdf)
    atleastOne = 0

    
    ########################dirroot##################################
    # TODO : 业务中如何获取这些数据？
    fcstroot, analroot = surf_config(ifcst,iref)

    st = starttime.strftime("%H")  # initial time

    region = iregion

    # domain = getregion(iregion)

    VAR = ipara
    #lat = np.arange(90, -90 - 1.5, -1.5)
    #lon = np.arange(0, 360, 1.5)
    #llon, llat = np.meshgrid(lon, lat)
    #plevs = [1000, 925, 850, 500, 200]
    aaaa = -999
    print("################### 文件匹配模式为 ",fcstroot +f"/normal/{starttime.strftime('%Y%m%d')}/"+ 'fcst' + str(starttime.strftime("%Y%m%d")) + '*.grib')
    testfile = glob.glob(fcstroot +f"/normal/{starttime.strftime('%Y%m%d')}/"+ 'fcst' + str(starttime.strftime("%Y%m%d")) + '*.grib')[0]
    #testfile = fcstroot +f"{starttime.strftime('%Y%m%d')}/"+ 'fcst' + str(starttime.strftime("%Y%m%d00")) + '000.grib'
    check_file_exist(testfile)
    f = open(testfile, "rb")
    gid = eccodes.codes_grib_new_from_file(f)
    if gid is None:
        print("create handler error")
    ni = eccodes.codes_get(gid, "Ni")
    nj = eccodes.codes_get(gid, "Nj")
    values = eccodes.codes_get_values(gid)
    resolution = eccodes.codes_get(gid, 'iDirectionIncrementInDegrees')
    slat = eccodes.codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
    elat = eccodes.codes_get(gid, 'latitudeOfLastGridPointInDegrees')
    slon = eccodes.codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
    elon = eccodes.codes_get(gid, 'longitudeOfLastGridPointInDegrees')
#
    lat = np.arange(slat, elat + resolution, resolution)
    lon = np.arange(slon, elon + resolution, resolution)
    llon, llat = np.meshgrid(lon, lat)
    aaaa = np.full((nj, ni), np.nan)

    cdate = starttime
    HH = starttime.hour


    while True: # time<endtime

        tt = -1
        dd = cdate.hour

        cdate, dd = modify_date(ifcst, cdate, dd)

        ccdate = cdate

        for i in range(fh[0], fh[1]+1, itimedelta):
            rmse = np.nan;
            bias = np.nan;
            cor = np.nan
            ts = np.nan;
            far = np.nan;
            mar = np.nan;
            ets = np.nan;
            pc = np.nan;

            tt += 1
            # 确定起报时次
            cdate = ccdate - datetime.timedelta(hours=i)

            fcstdata = fcstroot + f"/normal/{str(cdate.strftime('%Y%m%d'))}/"+ "fcst" + str(cdate.strftime("%Y%m%d%H")) + str("%03d" % (i + dd)) + ".grib"
            check_file_exist(fcstdata)
            analdata = analroot + f"/sfc/{starttime.strftime('%Y%m%d')}/" + "single" + str(starttime.strftime("%Y%m%d%H000")) + '.grib'
            check_file_exist(analdata)
            fcstGribReader = grib_dict.grib2io_ground_shortName 
            analGribReader = grib_dict.grib2io_ground_shortName 
            print("checkout",fcstdata,analdata)
            #st = analdate.strftime("%H")
            for var in VAR:
                if not (var in fcstGribReader.keys() and var in analGribReader.keys()) :
                    continue
                if var != "wind" and var!="wdir":
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata) and os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        print(fh,fcstdata)
                        print(fh,fcstGribReader[var])
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[var][0],"typeOfFirstFixedSurface":fcstGribReader[var][2]})
                            #ds = xr.open_dataset(fcstdata, backend_kwargs={
                            #    "filter_by_keys": fcstGribReader[var][0]
                            #}, engine="cfgrib")
                        #    print(ds)
                            fcst = ds[fcstGribReader[var][0]].values
                            #if var == "lcc" and ifcst == "NCEP" and iref=="ERA5":
                            #    fcst /= 100
                            #if var == "tcc" and ifcst == "NCEP" and iref=="ERA5":
                            #    fcst /= 100   
                            #if var in ["mslp","sp"]:
                            #    fcst /= 100 
                            print(fh,var,"fcst",np.nanmean(fcst))
                        except KeyError:
                            fcst = aaaa
                    else:
                        fcst=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"

                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata) and os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        print(fh,analdata)
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[var][0],"typeOfFirstFixedSurface":analGribReader[var][2]})
                            #ds = xr.open_dataset(analdata, backend_kwargs={
                            #    "filter_by_keys": analGribReader[var][0]
                            #},engine="cfgrib")
                           
                            anal = ds[analGribReader[var][0]].values
                            if var =="tcc" or var =="lcc" and iref=="ERA5":
                                anal*=10
                            # if var == "rad" and  iref=="ERA5":
                            #    anal /= 3600
                            # if var in ["mslp","sp"]:
                            #    anal /= 100
                            print(fh,var,"anal",np.nanmean(anal))
                        except KeyError:
                            anal = aaaa
                    else:

                        anal = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"

                else:
                    subvar = "10u"
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata):
                        print(fcstdata)
                        print(fcstGribReader[subvar])
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[subvar][0],"typeOfFirstFixedSurface":fcstGribReader[subvar][2]})
                            fuuu = ds[fcstGribReader[subvar][0]].values
                        except KeyError:
                            fuuu = aaaa
                    else:
                        fuuu=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"

                    subvar = "10v"
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata):
                        print("10vvvvv",fcstdata)
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[subvar][0],"typeOfFirstFixedSurface":fcstGribReader[subvar][2]})
                            fvvv = ds[fcstGribReader[subvar][0]].values
                        except KeyError:
                            fvvv = aaaa
                    else:
                        fvvv=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"
                        
                    fuuu = -fuuu
                    fvvv = -fvvv
                    fcst = np.sqrt(fuuu**2+fvvv**2)
                    fcstAngle = np.rad2deg(np.arccos((fuuu*0+fvvv*1)/np.sqrt(fuuu*fuuu+fvvv*fvvv)))
                   
                    fcstAngle[np.where(fuuu<0)]  = 360 - fcstAngle[np.where(fuuu<0)]

                    subvar = "10u"
                    if os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[subvar][0],"typeOfFirstFixedSurface":analGribReader[subvar][2]})
                            auuu = ds[analGribReader[subvar][0]].values
                        except KeyError:
                            auuu = aaaa                        
                    else:
                        auuu = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"
                    subvar = "10v"
                    if os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[subvar][0],"typeOfFirstFixedSurface":analGribReader[subvar][2]})
                            avvv = ds[analGribReader[subvar][0]].values
                        except KeyError:
                            avvv = aaaa
                    else:
                        avvv = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"
                        
                    auuu = -auuu
                    avvv = -avvv
                    anal = np.sqrt(auuu**2+avvv**2)
                    analAngle = np.rad2deg(np.arccos((auuu*0+avvv*1)/np.sqrt(auuu*auuu+avvv*avvv)))
    
                    analAngle[np.where(auuu<0)] = 360-analAngle[np.where(auuu<0)]

                if not np.all(np.isnan(fcst)) and not np.all(np.isnan(anal)):
                    #ds = xr.open_dataset(globalConf.maskroot,engine="cfgrib")
                    #mask = ds["unknown"].values
###########################################**************************################################
                    #fcst[mask == 0] = np.nan
                    #anal[mask == 0] = np.nan
                    atleastOne += 1
                    for jj,dm in enumerate(domain):
                        sj = int((dm[0] - slat) / resolution)
                        ej = int((dm[1] - slat) / resolution)
                        si = int(dm[2] / resolution)
                        ei = int(dm[3] / resolution)
                        fc = np.full((nj, ni), np.nan)
                        fc[sj:ej + 1, si:ei + 1] = fcst[sj:ej + 1, si:ei + 1]
                        ana = np.full((nj, ni), np.nan)
                        ana[sj:ej + 1, si:ei + 1] = anal[sj:ej + 1, si:ei + 1]
                        lats = np.full((nj, ni), np.nan)
                        lats[sj:ej + 1, si:ei + 1] = llat[sj:ej + 1, si:ei + 1]
                        mask = np.isnan(fc-ana)
                        lats[mask] = np.nan
                        if var != 'wind' and var != "wdir":
                            mse = np.nansum((fc - ana) * (fc - ana) * np.cos(lats * np.pi / 180.))
                        elif var == "wind":
                            fcu = np.full((nj, ni), np.nan)
                            fcu[sj:ej + 1, si:ei + 1] = fuuu[sj:ej + 1, si:ei + 1]
                            fcv = np.full((nj, ni), np.nan)
                            fcv[sj:ej + 1, si:ei + 1] = fvvv[sj:ej + 1, si:ei + 1]
                            anu = np.full((nj, ni), np.nan)
                            anu[sj:ej + 1, si:ei + 1] = auuu[sj:ej + 1, si:ei + 1]
                            anv = np.full((nj, ni), np.nan)
                            anv[sj:ej + 1, si:ei + 1] = avvv[sj:ej + 1, si:ei + 1] 

                            #????? 高空不是这么写的！！！！！！！！
                            mse = np.nansum((fc - ana) * (fc - ana) * np.cos(lats * np.pi / 180.))
                        elif var == "wdir":
                            fcu = np.full((nj, ni), np.nan)
                            fcu[sj:ej + 1, si:ei + 1] = fuuu[sj:ej + 1, si:ei + 1]
                            fcv = np.full((nj, ni), np.nan)
                            fcv[sj:ej + 1, si:ei + 1] = fvvv[sj:ej + 1, si:ei + 1]
                            anu = np.full((nj, ni), np.nan)
                            anu[sj:ej + 1, si:ei + 1] = auuu[sj:ej + 1, si:ei + 1]
                            anv = np.full((nj, ni), np.nan)
                            anv[sj:ej + 1, si:ei + 1] = avvv[sj:ej + 1, si:ei + 1] 
                            fcAngle=np.full((nj, ni), np.nan)
                            fcAngle[sj:ej + 1, si:ei + 1] = fcstAngle[sj:ej + 1, si:ei + 1]
                            anaAngle=np.full((nj, ni), np.nan)
                            anaAngle[sj:ej + 1, si:ei + 1]  = analAngle[sj:ej + 1, si:ei + 1]
                            
                            
                            tmp = (fcu*anu+fcv*anv)/(fc*ana) 
                            tmp[np.where(tmp>1)]=1
                            angle = np.arccos(tmp)*180/np.pi
                            mse = np.nansum(
                                    (angle*angle) * np.cos(lats * np.pi / 180.))
                            fc = angle
                            ana = np.zeros_like(fc)
                        
                        mse = mse / np.nansum(np.cos(lats * np.pi / 180.))
                        
                        rmse = np.sqrt(mse)
                        bias = np.nansum((fc - ana) * np.cos(lats * np.pi / 180.))
                        bias = bias / np.nansum(np.cos(lats * np.pi / 180.))
                        abias = np.nansum(np.abs(fc - ana) * np.cos(lats * np.pi / 180.))
                        abias = abias / np.nansum(np.cos(lats * np.pi / 180.))

                        # 取消相关
                        #fcm = np.nansum(fc * np.cos(lats * np.pi / 180.))
                        #fcm = fcm / np.nansum(np.cos(lats * np.pi / 180.))
                        #ocm = np.nansum(ana * np.cos(lats * np.pi / 180.))
                        #ocm = ocm / np.nansum(np.cos(lats * np.pi / 180.))
                        #cor1 = np.nansum((fc - fcm) * (ana - ocm) * np.cos(lats * np.pi / 180.))
                        #cor2 = np.nansum((fc - fcm) * (fc - fcm) * np.cos(lats * np.pi / 180.))
                        #cor3 = np.nansum((ana - ocm) * (ana - ocm) * np.cos(lats * np.pi / 180.))
                        #cor = cor1 / (np.sqrt(cor2 * cor3))

                        if var == "wdir":
                            fcstt = np.ma.array(fcAngle,mask = np.isnan(fc- ana))
                            ooobs = np.ma.array(anaAngle,mask = np.isnan(fc - ana))
                            aambb = np.ma.array(fc-ana,mask = np.isnan(fc-ana))
                            lats = np.ma.array(lats,mask = np.isnan(fc-ana))
                        else:
                            fcstt = np.ma.array(fc,mask = np.isnan(fc- ana))
                            ooobs = np.ma.array(ana,mask = np.isnan(fc - ana))
                            aambb = np.ma.array(fc-ana,mask = np.isnan(fc-ana))
                            lats = np.ma.array(lats,mask = np.isnan(fc-ana))

                        pc,ts,ets,far,mar,_,_,_=utils.calcTCPC(ooobs,fcstt,aambb,lats,utils.pcth,var)

                        #if rmse > 1000.:
                        #    cor = np.nan;
                        #    rmse = np.nan;
                        #    bias = np.nan;
                        #if np.isnan(cor):
                        #    cor = np.nan;
                        #    rmse = np.nan;
                        #    bias = np.nan;

                        if ts == [] :  ts=[(np.nan,np.nan)]
                        if ets == [] :  ets=[(np.nan,np.nan)]
                        if mar == [] :  mar=[(np.nan,np.nan)]
                        if far == [] :  far=[(np.nan,np.nan)]

                        if np.isnan([rmse, abias]).all() and np.isnan(ts).all():
                            pass
                        else:
                            for dfi in range(len(ts)):
                                resdf.loc[len(resdf)] = {"mode_type": pyweb2java(ifcst),
                                                         "reference_data_type": pyweb2java(iref), "level": ts[dfi][0],
                                                         "meteorological_element_type": pyweb2java(var), \
                                                         "area_id": region[jj], "forecast_time": cdate,
                                                         "forecast_hour": cdate.strftime("%H"),
                                                         "forecast_interval": i+dd,
                                                         "pc": pc, "acc": np.nan, \
                                                         "rmse": rmse, "mae": abias, \
                                                         "ts": ts[dfi][1], "mar": mar[dfi][1], \
                                                         # "far": far[dfi][1], "ets": ets[dfi][1]}
                                                         "far": far[dfi][1], "ets": bias}


    # 去除
        break
    #print(resdf)
    #t1 = datetime.datetime.now()
    #batch_size = 10000
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("surface_area_verification_result", batch)
    #print(datetime.datetime.now() - t1)

    if mess == "":
        mess = "succeed"
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",atleastOne)
    if atleastOne==0:
        status = False
        mess = "all met failed, retry again"
    return status,mess,resdf

# 格点区域地面检验
@typechecked
def yunyao_surf_pre(starttime:datetime.datetime,endtime:datetime.datetime, ifcst:str, iref:str, iregion:list, ipara:list,itimedelta:int,ilength:int)->tuple:
    status = True
    mess = ""
    tmpdf = {"mode_type": [], "reference_data_type": [], "level": [], "meteorological_element_type": [], "area_id": [],
             "forecast_time": [], \
             "forecast_hour": [], "forecast_interval": [], "pc": [], "acc": [], "rmse": [], "mae": [], "level": [],
             "ts": [], "ets": [], "mar": [], "far": [], }
    resdf = pd.DataFrame(tmpdf)
    atleastOne = 0

    
    ########################dirroot##################################
    # TODO : 业务中如何获取这些数据？
    fcstroot, analroot = surf_config(ifcst,iref)

    st = starttime.strftime("%H")  # initial time

    region = iregion

    domain = getregion(iregion)

    VAR = ipara
    length = ilength
    #lat = np.arange(90, -90 - 1.5, -1.5)
    #lon = np.arange(0, 360, 1.5)
    #llon, llat = np.meshgrid(lon, lat)
    #plevs = [1000, 925, 850, 500, 200]
    aaaa = -999
    testfile = glob.glob(fcstroot +f"/normal/{starttime.strftime('%Y%m%d')}/"+ 'fcst' + str(starttime.strftime("%Y%m%d")) + '*.grib')[0]
    #testfile = fcstroot +f"{starttime.strftime('%Y%m%d')}/"+ 'fcst' + str(starttime.strftime("%Y%m%d00")) + '000.grib'
    check_file_exist(testfile)
    f = open(testfile, "rb")
    gid = eccodes.codes_grib_new_from_file(f)
    if gid is None:
        print("create handler error")
    ni = eccodes.codes_get(gid, "Ni")
    nj = eccodes.codes_get(gid, "Nj")
    values = eccodes.codes_get_values(gid)
    resolution = eccodes.codes_get(gid, 'iDirectionIncrementInDegrees')
    slat = eccodes.codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
    elat = eccodes.codes_get(gid, 'latitudeOfLastGridPointInDegrees')
    slon = eccodes.codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
    elon = eccodes.codes_get(gid, 'longitudeOfLastGridPointInDegrees')
#
    lat = np.arange(slat, elat + resolution, resolution)
    lon = np.arange(slon, elon + resolution, resolution)
    llon, llat = np.meshgrid(lon, lat)
    aaaa = np.full((nj, ni), np.nan)

    cdate = starttime
    HH = starttime.hour


    while True: # time<endtime

        tt = -1
        dd = cdate.hour

        cdate, dd = modify_date(ifcst, cdate, dd)

        ccdate = cdate

        for i in range(0, itimedelta * int(length), itimedelta):
            rmse = np.nan;
            bias = np.nan;
            cor = np.nan
            ts = np.nan;
            far = np.nan;
            mar = np.nan;
            ets = np.nan;
            pc = np.nan;

            tt += 1
            # 确定起报时次
            cdate = ccdate - datetime.timedelta(hours=i)

            fcstdata = fcstroot + f"/normal/{str(cdate.strftime('%Y%m%d'))}/"+ "fcst" + str(cdate.strftime("%Y%m%d%H")) + str("%03d" % (i + dd)) + ".grib"
            check_file_exist(fcstdata)
            analdata = analroot + f"/sfc/{starttime.strftime('%Y%m%d')}/" + "single" + str(starttime.strftime("%Y%m%d%H000")) + '.grib'
            check_file_exist(analdata)
            fcstGribReader = grib_dict.grib2io_ground_shortName 
            analGribReader = grib_dict.grib2io_ground_shortName 
            print("checkout",fcstdata,analdata)
            #st = analdate.strftime("%H")
            for var in VAR:
                if not (var in fcstGribReader.keys() and var in analGribReader.keys()) :
                    continue
                if var != "wind" and var!="wdir":
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata) and os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        print(fcstdata)
                        print(fcstGribReader[var])
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[var][0],"typeOfFirstFixedSurface":fcstGribReader[var][2]})
                            #ds = xr.open_dataset(fcstdata, backend_kwargs={
                            #    "filter_by_keys": fcstGribReader[var][0]
                            #}, engine="cfgrib")
                        #    print(ds)
                            fcst = ds[fcstGribReader[var][0]].values
                            #if var == "lcc" and ifcst == "NCEP" and iref=="ERA5":
                            #    fcst /= 100
                            #if var == "tcc" and ifcst == "NCEP" and iref=="ERA5":
                            #    fcst /= 100   
                            #if var in ["mslp","sp"]:
                            #    fcst /= 100 
                            print(var,"fcst",np.nanmean(fcst))
                        except KeyError:
                            fcst = aaaa
                    else:
                        fcst=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"

                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata) and os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        print(analdata)
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[var][0],"typeOfFirstFixedSurface":analGribReader[var][2]})
                            #ds = xr.open_dataset(analdata, backend_kwargs={
                            #    "filter_by_keys": analGribReader[var][0]
                            #},engine="cfgrib")
                           
                            anal = ds[analGribReader[var][0]].values

                            # DO NOT MODIFY 20251011
                            if var =="tcc" or var =="lcc" and iref=="ERA5":
                                anal*=10
                            # if var == "rad" and  iref=="ERA5":
                            #    anal /= 3600
                            # if var in ["mslp","sp"]:
                            #    anal /= 100
                            print(var,"anal",np.nanmean(anal))
                        except KeyError:
                            anal = aaaa
                    else:

                        anal = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"

                else:
                    subvar = "10u"
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata):
                        print(fcstdata)
                        print(fcstGribReader[subvar])
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[subvar][0],"typeOfFirstFixedSurface":fcstGribReader[subvar][2]})
                            fuuu = ds[fcstGribReader[subvar][0]].values
                        except KeyError:
                            fuuu = aaaa
                    else:
                        fuuu=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"

                    subvar = "10v"
                    if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata):
                        print("10vvvvv",fcstdata)
                        try:
                            ds = xr.open_dataset(fcstdata,engine="grib2io",filters={"shortName":fcstGribReader[subvar][0],"typeOfFirstFixedSurface":fcstGribReader[subvar][2]})
                            fvvv = ds[fcstGribReader[subvar][0]].values
                        except KeyError:
                            fvvv = aaaa
                    else:
                        fvvv=np.full((nj, ni),np.nan)
                        mess +=f"{fcstdata} not exists"
                        
                    fuuu = -fuuu
                    fvvv = -fvvv
                    fcst = np.sqrt(fuuu**2+fvvv**2)
                    fcstAngle = np.rad2deg(np.arccos((fuuu*0+fvvv*1)/np.sqrt(fuuu*fuuu+fvvv*fvvv)))
                   
                    fcstAngle[np.where(fuuu<0)]  = 360 - fcstAngle[np.where(fuuu<0)]

                    subvar = "10u"
                    if os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[subvar][0],"typeOfFirstFixedSurface":analGribReader[subvar][2]})
                            auuu = ds[analGribReader[subvar][0]].values
                        except KeyError:
                            auuu = aaaa                        
                    else:
                        auuu = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"
                    subvar = "10v"
                    if os.access(analdata, os.F_OK) and os.path.getsize(analdata):
                        try:
                            ds = xr.open_dataset(analdata,engine="grib2io",filters={"shortName":analGribReader[subvar][0],"typeOfFirstFixedSurface":analGribReader[subvar][2]})
                            avvv = ds[analGribReader[subvar][0]].values
                        except KeyError:
                            avvv = aaaa
                    else:
                        avvv = np.full((nj, ni), np.nan)
                        mess += f"{fcstdata} not exists"
                        
                    auuu = -auuu
                    avvv = -avvv
                    anal = np.sqrt(auuu**2+avvv**2)
                    analAngle = np.rad2deg(np.arccos((auuu*0+avvv*1)/np.sqrt(auuu*auuu+avvv*avvv)))
    
                    analAngle[np.where(auuu<0)] = 360-analAngle[np.where(auuu<0)]

                if not np.all(np.isnan(fcst)) and not np.all(np.isnan(anal)):
                    #ds = xr.open_dataset(globalConf.maskroot,engine="cfgrib")
                    #mask = ds["unknown"].values
###########################################**************************################################
                    #fcst[mask == 0] = np.nan
                    #anal[mask == 0] = np.nan
                    atleastOne += 1
                    for jj,dm in enumerate(domain):
                        sj = int((dm[0] - slat) / resolution)
                        ej = int((dm[1] - slat) / resolution)
                        si = int(dm[2] / resolution)
                        ei = int(dm[3] / resolution)
                        fc = np.full((nj, ni), np.nan)
                        fc[sj:ej + 1, si:ei + 1] = fcst[sj:ej + 1, si:ei + 1]
                        ana = np.full((nj, ni), np.nan)
                        ana[sj:ej + 1, si:ei + 1] = anal[sj:ej + 1, si:ei + 1]
                        lats = np.full((nj, ni), np.nan)
                        lats[sj:ej + 1, si:ei + 1] = llat[sj:ej + 1, si:ei + 1]
                        mask = np.isnan(fc-ana)
                        lats[mask] = np.nan
                        if var != 'wind' and var != "wdir":
                            mse = np.nansum((fc - ana) * (fc - ana) * np.cos(lats * np.pi / 180.))
                        elif var == "wind":
                            fcu = np.full((nj, ni), np.nan)
                            fcu[sj:ej + 1, si:ei + 1] = fuuu[sj:ej + 1, si:ei + 1]
                            fcv = np.full((nj, ni), np.nan)
                            fcv[sj:ej + 1, si:ei + 1] = fvvv[sj:ej + 1, si:ei + 1]
                            anu = np.full((nj, ni), np.nan)
                            anu[sj:ej + 1, si:ei + 1] = auuu[sj:ej + 1, si:ei + 1]
                            anv = np.full((nj, ni), np.nan)
                            anv[sj:ej + 1, si:ei + 1] = avvv[sj:ej + 1, si:ei + 1] 

                            #????? 高空不是这么写的！！！！！！！！
                            mse = np.nansum((fc - ana) * (fc - ana) * np.cos(lats * np.pi / 180.))
                        elif var == "wdir":
                            fcu = np.full((nj, ni), np.nan)
                            fcu[sj:ej + 1, si:ei + 1] = fuuu[sj:ej + 1, si:ei + 1]
                            fcv = np.full((nj, ni), np.nan)
                            fcv[sj:ej + 1, si:ei + 1] = fvvv[sj:ej + 1, si:ei + 1]
                            anu = np.full((nj, ni), np.nan)
                            anu[sj:ej + 1, si:ei + 1] = auuu[sj:ej + 1, si:ei + 1]
                            anv = np.full((nj, ni), np.nan)
                            anv[sj:ej + 1, si:ei + 1] = avvv[sj:ej + 1, si:ei + 1] 
                            fcAngle=np.full((nj, ni), np.nan)
                            fcAngle[sj:ej + 1, si:ei + 1] = fcstAngle[sj:ej + 1, si:ei + 1]
                            anaAngle=np.full((nj, ni), np.nan)
                            anaAngle[sj:ej + 1, si:ei + 1]  = analAngle[sj:ej + 1, si:ei + 1]
                            
                            
                            tmp = (fcu*anu+fcv*anv)/(fc*ana) 
                            tmp[np.where(tmp>1)]=1
                            angle = np.arccos(tmp)*180/np.pi
                            mse = np.nansum(
                                    (angle*angle) * np.cos(lats * np.pi / 180.))
                            fc = angle
                            ana = np.zeros_like(fc)
                        
                        mse = mse / np.nansum(np.cos(lats * np.pi / 180.))
                        
                        rmse = np.sqrt(mse)
                        bias = np.nansum((fc - ana) * np.cos(lats * np.pi / 180.))
                        bias = bias / np.nansum(np.cos(lats * np.pi / 180.))
                        abias = np.nansum(np.abs(fc - ana) * np.cos(lats * np.pi / 180.))
                        abias = abias / np.nansum(np.cos(lats * np.pi / 180.))

                        # 取消相关
                        #fcm = np.nansum(fc * np.cos(lats * np.pi / 180.))
                        #fcm = fcm / np.nansum(np.cos(lats * np.pi / 180.))
                        #ocm = np.nansum(ana * np.cos(lats * np.pi / 180.))
                        #ocm = ocm / np.nansum(np.cos(lats * np.pi / 180.))
                        #cor1 = np.nansum((fc - fcm) * (ana - ocm) * np.cos(lats * np.pi / 180.))
                        #cor2 = np.nansum((fc - fcm) * (fc - fcm) * np.cos(lats * np.pi / 180.))
                        #cor3 = np.nansum((ana - ocm) * (ana - ocm) * np.cos(lats * np.pi / 180.))
                        #cor = cor1 / (np.sqrt(cor2 * cor3))

                        if var == "wdir":
                            fcstt = np.ma.array(fcAngle,mask = np.isnan(fc- ana))
                            ooobs = np.ma.array(anaAngle,mask = np.isnan(fc - ana))
                            aambb = np.ma.array(fc-ana,mask = np.isnan(fc-ana))
                            lats = np.ma.array(lats,mask = np.isnan(fc-ana))
                        else:
                            fcstt = np.ma.array(fc,mask = np.isnan(fc- ana))
                            ooobs = np.ma.array(ana,mask = np.isnan(fc - ana))
                            aambb = np.ma.array(fc-ana,mask = np.isnan(fc-ana))
                            lats = np.ma.array(lats,mask = np.isnan(fc-ana))
                        
                        pc,ts,ets,far,mar,_,_,_=utils.calcTCPC(ooobs,fcstt,aambb,lats,utils.pcth,var)

                        #if rmse > 1000.:
                        #    cor = np.nan;
                        #    rmse = np.nan;
                        #    bias = np.nan;
                        #if np.isnan(cor):
                        #    cor = np.nan;
                        #    rmse = np.nan;
                        #    bias = np.nan;

                        if ts == [] :  ts=[(np.nan,np.nan)]
                        if ets == [] :  ets=[(np.nan,np.nan)]
                        if mar == [] :  mar=[(np.nan,np.nan)]
                        if far == [] :  far=[(np.nan,np.nan)]

                        if np.isnan([rmse, abias]).all() and np.isnan(ts).all():
                            pass
                        else:
                            for dfi in range(len(ts)):
                                resdf.loc[len(resdf)] = {"mode_type": pyweb2java(ifcst),
                                                         "reference_data_type": pyweb2java(iref), "level": ts[dfi][0],
                                                         "meteorological_element_type": pyweb2java(var), \
                                                         "area_id": region[jj], "forecast_time": cdate,
                                                         "forecast_hour": cdate.strftime("%H"),
                                                         "forecast_interval": i+dd,
                                                         "pc": pc, "acc": np.nan, \
                                                         "rmse": rmse, "mae": abias, \
                                                         "ts": ts[dfi][1], "mar": mar[dfi][1], \
                                                         "far": far[dfi][1], "ets": bias}


    # 去除
        break
    print(resdf)
    t1 = datetime.datetime.now()
    batch_size = 10000
    for i in range(0, len(resdf), batch_size):
        batch = resdf.iloc[i:i + batch_size]
        clickclient.insert_df("surface_area_verification_result", batch)
    print(datetime.datetime.now() - t1)

    if mess == "":
        mess = "succeed"
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",atleastOne)
    if atleastOne==0:
        status = False
        mess = "all met failed, retry again"
    return status,mess
# 站点区域高空检验
@typechecked
def yunyao_plev_pre_bufr(starttime:datetime.datetime,endtime: datetime.datetime ,ifcst:str,iref:str,iregion:list,ipara:list,itimedelta:int,ilength:int)->tuple:
    # TODO  QC code is 16bit int, left to right ,16 to 1
    # bit 1: BUFR error
    # bit 2: anal error 
    # bit 3: ERA5 error 
    # bit 4: area not match
    # bit 5: start time error 
    # bit 6: no such forecast
    # bit 7: no such ref true value
    # bit 8: length warning 
    # bit 9: param error
    qc = 0;
    status = True
    mess = ""
    atleastOne = 0
    ########################dirroot##################################
    #TODO : 业务中如何获取这些数据？
    fcstroot, analroot,outputroot,cmeanroot,obsroot = plev_config(ifcst,iref,"stats")

    ###################################################################
    st = starttime.strftime("%H")  # initial time
    region  = iregion
    # TODO ：业务中如何获取区域代码确定的区域？
    domain = getregion(iregion)

    VAR = ipara
    plevs = [1000, 925, 850, 700, 500, 200]
    aaa = -999
    length = ilength  # 检验时间个数
    #####################################################################
    testfile = fcstroot +f"/normal/{starttime.strftime('%Y%m%d')}/fcst" + str(starttime.strftime("%Y%m%d%H")) + '000.grib'
    print(fcstroot)
    check_file_exist(testfile)
    f = open(testfile, "rb")
    gid = eccodes.codes_grib_new_from_file(f)
    if gid is None:
        print("create handler error")
    ni = eccodes.codes_get(gid, "Ni")
    nj = eccodes.codes_get(gid, "Nj")
    values = eccodes.codes_get_values(gid)
    resolution = eccodes.codes_get(gid, 'iDirectionIncrementInDegrees')
    slat = eccodes.codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
    elat = eccodes.codes_get(gid, 'latitudeOfLastGridPointInDegrees')
    slon = eccodes.codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
    elon = eccodes.codes_get(gid, 'longitudeOfLastGridPointInDegrees')

    lat = np.arange(slat, elat + resolution, resolution)
    lon = np.arange(slon, elon + resolution, resolution)
    llon, llat = np.meshgrid(lon, lat)
    aaaa = np.full((nj, ni), np.nan)

    cdate = starttime
    HH = starttime.hour

    while True:
        #outputdate = outputroot + "." + str(cdate.strftime("%Y%m%d%H"))
        #ofile = open(outputdate, "w")
        #ofile.write("TIME VAR PLEV REGION   RMSE      BIAS     ABIAS")
        #ofile.write(' \r\n')
        #f = open(outputdate, "w")


        tmpdf= {"mode_type":[], "reference_data_type":[],"height":[],"meteorological_element_type":[],"area_id":[],"forecast_time":[],\
            "forecast_hour":[],"forecast_interval":[],"pc":[],"acc":[],"rmse":[],"mae":[]}
        resdf = pd.DataFrame(tmpdf)


        #if True:

        obsdata = clickclient.query_df("SELECT temperature,geo_height,humidity, wind_speed, wind_direction,height,station_code,longitude,latitude FROM upper_observation_data WHERE observation_time='{:s}'".format(cdate.strftime("%Y-%m-%d %H:%M:%S")))
        print(obsdata)
        #if obsdata.shape[0] != 0:
        if len(obsdata) != 0:
            llat = obsdata["latitude"].to_numpy().astype(np.float32)
            llon = obsdata["longitude"].to_numpy().astype(np.float32)
            prc = obsdata["height"].to_numpy().astype(np.float32)
            tem = obsdata["temperature"].to_numpy().astype(np.float32)
            rr = obsdata["humidity"].to_numpy().astype(np.float32)
            hh = obsdata["geo_height"].to_numpy().astype(np.float32)
            windo = obsdata["wind_speed"].to_numpy().astype(np.float32)
            wdir = obsdata["wind_direction"].to_numpy().astype(np.float32)
            uu = -np.sin(wdir/180*np.pi)*windo
            vv = -np.cos(wdir/180*np.pi)*windo
            kk = len(llat)
            knum = kk
            
            dd = cdate.hour
            cdate, dd = modify_date(ifcst,cdate,dd)
            ccdate = cdate

            for i in range(0, itimedelta * int(length)+1, itimedelta):
                print(i)
                print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
                cdate = ccdate - datetime.timedelta(hours=i)
                fcstdata = fcstroot + f"/normal/{cdate.strftime('%Y%m%d')}/fcst" + str(cdate.strftime("%Y%m%d%H")) + str("%03d" % (i+dd) )+ ".grib"
                ismissfile = check_file_exist(fcstdata)
                print(fcstdata,ccdate)
                if os.access(fcstdata, os.F_OK) and os.path.getsize(fcstdata):
                    atleastOne += 1
                    for var in VAR:
                        for plev in plevs:
                            if var != 'wind':
                                t = load_message_from_file(
                                    file_path=fcstdata,
                                    parameter=var,
                                    level_type="isobaricInhPa",
                                    level=plev,
                                )
                                if t is not None:
                                    fcst = eccodes.codes_get_double_array(t, "values")
                                    fcst = fcst.reshape([nj, ni])
                                else:
                                    fcst = aaaa
                            else:
                                t = load_message_from_file(
                                    file_path=fcstdata,
                                    parameter='u',
                                    level_type="isobaricInhPa",
                                    level=plev,
                                )
                                if t is not None:
                                    u = eccodes.codes_get_double_array(t, "values")
                                    u = u.reshape([nj, ni])
                                else:
                                    u = aaaa
                                t = load_message_from_file(
                                    file_path=fcstdata,
                                    parameter='v',
                                    level_type="isobaricInhPa",
                                    level=plev,
                                )
                                if t is not None:
                                    v = eccodes.codes_get_double_array(t, "values")
                                    v = v.reshape([nj, ni])
                                else:
                                    v = aaaa
                                fcst = np.sqrt(u ** 2 + v ** 2)

                            if var == 'gh':
                                anal = hh
                            if var == 't':
                                anal = tem
                            if var == 'u':
                                anal = uu
                            if var == 'v':
                                anal = vv
                            if var == "r":
                                anal = rr
                            if var == 'wind' or var =="wdir":
                                anal = windo
                            
                            anal = np.array(anal).reshape((knum))
                            anal[anal == -999] = np.nan
                            #################calculation the scores####################################################
                            if var != 'wind' and var != "wdir":
                                re = 0
                                for domin in domain:
                                    obst = [];
                                    fcstt = [];
                                    rmse = -999;
                                    abias = -999;
                                    bias = -999
                                    for ki in range(0, kk):
                                        if prc[ki] == float(plev):
                                            # 这段是个XX东西 begin
                                            if llat[ki] >= domin[0] and llat[ki] <= domin[1] and llon[ki] >= domin[
                                                2] and llon[ki] <= domin[3]:
                                                if llon[ki] < lon[ni - 3]:
                                                    tx = int((llat[ki] - slat) / resolution)
                                                    ty = int((llon[ki]) / resolution)
                                                    if (tx >= 2 and tx <= nj - 3):
                                                        for jjk in range(tx - 2, tx + 2):
                                                            if (llat[ki] - lat[jjk]) * (llat[ki] - lat[jjk + 1]) <= 0:
                                                                jj = jjk
                                                    else:
                                                        jj = tx
                                                    if (ty >= 2 and ty <= ni - 3):
                                                        for iik in range(ty - 2, ty + 2):
                                                            if (llon[ki] - lon[iik]) * (llon[ki] - lon[iik + 1]) <= 0:
                                                                ii = iik
                                                    else:
                                                        ii = ty
                                                    if (ii <= ni - 2 and jj <= nj - 2):
                                                        tmp1 = fcst[jj, ii + 1] - (fcst[jj, ii + 1] - fcst[jj, ii]) * (
                                                                    lon[ii + 1] - llon[ki]) / (lon[ii + 1] - lon[ii])
                                                        tmp2 = fcst[jj + 1, ii + 1] - (
                                                                    fcst[jj + 1, ii + 1] - fcst[jj + 1, ii]) * (
                                                                           lon[ii + 1] - llon[ki]) / (
                                                                           lon[ii + 1] - lon[ii])
                                                        tmp = tmp2 - (tmp2 - tmp1) * (lat[jj + 1] - llat[ki]) / (
                                                                    lat[jj + 1] - lat[jj])
                                                    else:
                                                        tmp = fcst[jj, ii]
                                                #print(var,"xxxxxxxxxxxxx",tmp,anal[ki])
                                                if abs(tmp - anal[ki]) <= 500:
                                                    obst.append(anal[ki])
                                                    fcstt.append(tmp)
                                            # 这段是个XX东西 end
                                    fcstt = np.array(fcstt)
                                    obst = np.array(obst)


                                    if var == 't':
                                        rmse = np.sqrt(np.nanmean((fcstt - obst) ** 2))
                                        bias = np.nanmean(fcstt - obst)
                                        abias = np.nanmean(abs(fcstt - obst))
                                    else:
                                        rmse = np.sqrt(np.nanmean((fcstt - obst) ** 2))
                                        bias = np.nanmean(fcstt - obst)
                                        abias = np.nanmean(abs(fcstt - obst))


                                    # write db
                                    if np.isnan([rmse, abias]).all():
                                        pass
                                    else:
                                        resdf.loc[len(resdf)] = {"mode_type":pyweb2java(ifcst),"reference_data_type":pyweb2java(iref),"height":str(plev),"meteorological_element_type":pyweb2java(var),\
                                          "area_id":region[re],"forecast_time":cdate,"forecast_hour":cdate.strftime("%H"),"forecast_interval":i,"pc":np.nan,"acc":np.nan,\
                                          "rmse":rmse,"mae":abias}
                                    #ofile.write(str("%3d" % i) + "  " + str(var) + '  ' + str(plev) + '  ' + str(
                                    #    region[re]) + '  ' + str("%.2f" % rmse) + "  " + str(
                                    #    "%.2f" % bias) + "  " + str("%.2f" % abias))
                                    #ofile.write(' \r\n')
                                    re += 1
                            else:
                                re = 0
                                for domin in domain:
                                    obsu = [];
                                    obsv = [];
                                    fcstu = [];
                                    fcstv = [];
                                    rmse = -999;
                                    abias = -999;
                                    bias = -999
                                    for ki in range(0, kk):
                                        if prc[ki] == float(plev):
                                            if llat[ki] >= domin[0] and llat[ki] <= domin[1] and llon[ki] >= domin[
                                                2] and llon[ki] <= domin[3]:
                                                if llon[ki] < lon[ni - 3]:
                                                    tx = int((llat[ki] - slat) / resolution)
                                                    ty = int((llon[ki]) / resolution)
                                                    if (tx >= 2 and tx <= nj - 3):
                                                        for jjk in range(tx - 2, tx + 2):
                                                            if (llat[ki] - lat[jjk]) * (llat[ki] - lat[jjk + 1]) <= 0:
                                                                jj = jjk
                                                    else:
                                                        jj = tx
                                                    if (ty >= 2 and ty <= ni - 3):
                                                        for iik in range(ty - 2, ty + 2):
                                                            if (llon[ki] - lon[iik]) * (llon[ki] - lon[iik + 1]) <= 0:
                                                                ii = iik
                                                    else:
                                                        ii = ty
                                                    if (ii <= ni - 2 and jj <= nj - 2):
                                                        tmpu1 = u[jj, ii + 1] - (u[jj, ii + 1] - u[jj, ii]) * (
                                                                    lon[ii + 1] - llon[ki]) / (lon[ii + 1] - lon[ii])
                                                        tmpu2 = u[jj + 1, ii + 1] - (
                                                                    u[jj + 1, ii + 1] - u[jj + 1, ii]) * (
                                                                            lon[ii + 1] - llon[ki]) / (
                                                                            lon[ii + 1] - lon[ii])
                                                        tmpu = tmpu2 - (tmpu2 - tmpu1) * (lat[jj + 1] - llat[ki]) / (
                                                                    lat[jj + 1] - lat[jj])
                                                        tmpv1 = v[jj, ii + 1] - (v[jj, ii + 1] - v[jj, ii]) * (
                                                                    lon[ii + 1] - llon[ki]) / (lon[ii + 1] - lon[ii])
                                                        tmpv2 = v[jj + 1, ii + 1] - (
                                                                    v[jj + 1, ii + 1] - v[jj + 1, ii]) * (
                                                                            lon[ii + 1] - llon[ki]) / (
                                                                            lon[ii + 1] - lon[ii])
                                                        tmpv = tmpv2 - (tmpv2 - tmpv1) * (lat[jj + 1] - llat[ki]) / (
                                                                    lat[jj + 1] - lat[jj])
                                                    else:
                                                        tmpu = u[jj, ii];
                                                        tmpv = v[jj, ii]
                                                if abs(tmpu - uu[ki]) <= 500:
                                                    obsu.append(uu[ki])
                                                    fcstu.append(tmpu)
                                                    obsv.append(vv[ki])
                                                    fcstv.append(tmpv)
                                    if var == "wind":
                                        fcstu = np.array(fcstu)
                                        obsu = np.array(obsu)
                                        fcstv = np.array(fcstv)
                                        obsv = np.array(obsv)
                                        rmse = np.sqrt(np.nanmean((fcstu - obsu) ** 2 + (fcstv - obsv) ** 2))
                                        bias = np.nanmean(np.sqrt(fcstu ** 2 + fcstv ** 2) - np.sqrt(obsu ** 2 + obsv ** 2))
                                        abias = np.nanmean(
                                            abs(np.sqrt(fcstu ** 2 + fcstv ** 2) - np.sqrt(obsu ** 2 + obsv ** 2)))
                                    else :
                                        fcstu = np.array(fcstu)
                                        obsu = np.array(obsu)
                                        fcstv = np.array(fcstv)
                                        obsv = np.array(obsv)
                                        
                                        fcstwind = np.sqrt(fcstu**2+fcstv ** 2)
                                        obswind = np.sqrt(obsu ** 2 + obsv ** 2)
                                        tmpaaa = (fcstu*obsu+fcstv*obsv)/(fcstwind*obswind) 
                                        tmpaaa[np.where(tmpaaa>1)]=1
                                        angle = np.arccos(tmpaaa)*180/np.pi

                                        rmse = np.sqrt(np.nanmean(angle**2))
                                        bias = np.nanmean(angle)
                                        abias = np.nanmean(abs(angle))


                                    # write db
                                    if np.isnan([rmse, abias]).all():
                                        pass
                                    else:
                                        resdf.loc[len(resdf)] = {"mode_type":pyweb2java(ifcst),"reference_data_type":pyweb2java(iref),"height":str(plev),"meteorological_element_type":pyweb2java(var),\
                                          "area_id":region[re],"forecast_time":cdate,"forecast_hour":cdate.strftime("%H"),"forecast_interval":i,"pc":np.nan,"acc":np.nan,\
                                          "rmse":rmse,"mae":abias}
                                    re += 1

            print(resdf)
            batch_size = 10000
            for i in range(0,len(resdf),batch_size):
                batch = resdf.iloc[i:i+batch_size]
                clickclient.insert_df("upper_area_verification_result",batch)

            mess = "succeed"
        else:
            status = False
            mess = f"{starttime} obsfile is not exists"
        break
    if mess == "":
        mess = "succeed"
    if atleastOne==0:
        status = False
        mess = "all met failed, retry again"
    return status,mess
# 区域高空检验
@typechecked
def yunyao_plev_pre(starttime:datetime.datetime, endtime: datetime.datetime, ifcst:str, iref:str, iregion:list, ipara:list,itimedelta:int,ilength:int,HPC_todolist=None)->tuple:
    status = False
    mess = ""
    qc = 0

    # check file complete?
    ismissfile = False
        
    fcstroot, analroot,outputroot,cmeanroot,obsroot = plev_config(ifcst,iref,"singlefcst")
    region = iregion

    domain =getregion(iregion)

    VAR = ipara
    length = ilength
    lat = np.arange(90, -90 - 1.5, -1.5)
    lon = np.arange(0, 360, 1.5)
    llon, llat = np.meshgrid(lon, lat)
    plevs = [1000,925,850,700,500,200]
    aaaa = np.full((121, 240), np.nan)
    
    cdate = starttime
    HH = starttime.hour
    while True:
        #               预报时间     变量      层数        区域
        acc = np.full((int(length), len(VAR), len(plevs), len(region)), np.nan)
        rmse = acc.copy();
        bias = acc.copy();
        abias = acc.copy();
        std = acc.copy();
        rmsem = acc.copy();
        rmsep = acc.copy();
        accur = acc.copy();
        outangbias = acc.copy()
        #outputdate = outputroot + "." + str(cdate.strftime("%Y%m%d%H"))
        #f = open(outputdate, "w")
        #f.write(
        #    "LEADTIME      VARIABLES     PLEVS     REGION    ACC      RMSE      BIAS       ABIAS      STD      RMSEM      RMSEP")
        #f.write(' \r\n')
        tmpdf= {"mode_type":[], "reference_data_type":[],"height":[],"meteorological_element_type":[],"area_id":[],"forecast_time":[],\
            "forecast_hour":[],"forecast_interval":[],"pc":[],"acc":[],"rmse":[],"mae":[]}
        resdf = pd.DataFrame(tmpdf)
        #检验的

        tt = -1
        dd = cdate.hour
        analdate = cdate
        analdata = analroot+f"/normal/{analdate.strftime('%Y%m%d')}/" + "prs" + str(analdate.strftime("%Y%m%d%H"))+"000.grib"
        ismissfile = check_file_exist(analdata)

        cdate,dd = modify_date(ifcst,cdate,dd)

        ccdate = cdate
        
        if HPC_todolist != None:
            todolist = HPC_todolist
        else:
            todolist = range(0, itimedelta * int(length), itimedelta)
        for i in todolist:

            print(i)
            tt += 1
            #确定起报时次
            cdate = ccdate - datetime.timedelta(hours=i)
            st = analdate.strftime("%H")
            fcstdata = fcstroot+f"/normal/{cdate.strftime('%Y%m%d')}/" + "prs" + str(cdate.strftime("%Y%m%d%H")) + str("%03d" % (i+dd) )+ ".grib"
            print(fcstdata,analdata)
            ismissfile = check_file_exist(fcstdata)

            climdata = cmeanroot + "/cmean_1d.1959" + str(analdate.strftime("%m%d"))
            ismissfile = check_file_exist(climdata)
            
            if globalConf.use_DB==0 :#HPC
                if ismissfile:
                    with open(globalConf.message+f"/{ifcst}/{cdate.strftime('%Y%m%d')}/plev_{iref}_{cdate.strftime('%Y%m%d')}_{i}.retry","w" ) as f:
                        pass
                  
            
            #date = cdate +datetime.timedelta(itimedelta)

            if os.access(fcstdata, os.F_OK) and os.access(analdata, os.F_OK) and os.path.getsize(
                    fcstdata) and os.path.getsize(analdata):
                status = True
                tv = 0
                for var in VAR:
                    tv += 1
                    tk = 0
                    for plev in plevs:
                        tk += 1
                        if var != 'wind' and var!= "wdir" :
                            t = load_message_from_file(
                                file_path=fcstdata,
                                parameter=var,
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                fcst = eccodes.codes_get_double_array(t, "values")
                                fcst = fcst.reshape([121, 240])
                            else:
                                fcst = aaaa
                            t = load_message_from_file(
                                file_path=fcstdata,
                                parameter='gh',
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                hgt = eccodes.codes_get_double_array(t, "values")
                                hgt = hgt.reshape([121, 240])
                            else:
                                hgt = aaaa

                            t = load_message_from_file(
                                file_path=fcstdata,
                                parameter='gh',
                                level_type="tropopause",
                                level=0,
                            )
                            if t is not None:
                                hs = eccodes.codes_get_double_array(t, "values")
                                hs = hs.reshape([121, 240])
                            else:
                                hs = aaaa
                            # 处理ERA5 数据的狗皮膏药
                #            if var =="gh" and iref == "ERA5":
                #                tvar = "z"
                #            else:
                #                tvar = var
                            t = load_message_from_file(
                                file_path=analdata,
                                parameter=var,
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                anal = eccodes.codes_get_double_array(t, "values")
                                anal = anal.reshape([121, 240])
                                # ERA5存储的是位势
                                #if var == "gh" and iref == "ERA5":
                                #    anal = anal/9.8066
                                    #print(anal)
                            else:
                                anal = aaaa

                            pppp = 1
   #                         if (ifcst =="CMA_GFS" and starttime<datetime.datetime(2025,6,1,0,0,0)):
   #                             pppp = 0.01
                            if os.access(climdata, os.F_OK):
                                t = load_message_from_file(
                                    file_path=climdata,
                                    parameter={
                                        "shortName": var,
                                        "dataTime": int(str(st) + '00')
                                    },
                                    level_type="isobaricInhPa",
                                    level=plev*pppp,
                                )
                                if t is not None:
                                
                                    cmean = eccodes.codes_get_double_array(t, "values")
                                    cmean = cmean.reshape([121, 240])
                                else:
                                    cmean = aaaa
                            print("cmean",cmean)
                        else:
                            t = load_message_from_file(
                                file_path=fcstdata,
                                parameter='u',
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                u = eccodes.codes_get_double_array(t, "values")
                                u = u.reshape([121, 240])
                                u = np.ma.masked_where(u==9999,u)
                            else:
                                u = aaaa
                            t = load_message_from_file(
                                file_path=fcstdata,
                                parameter='v',
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                v = eccodes.codes_get_double_array(t, "values")
                                v = v.reshape([121, 240])
                                v = np.ma.masked_where(v==9999,v)
                            else:
                                v = aaaa
                            fcst = np.sqrt(u ** 2 + v ** 2)
                            fcstu = u;
                            fcstv = v

                            t = load_message_from_file(
                                file_path=analdata,
                                parameter='u',
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                u = eccodes.codes_get_double_array(t, "values")
                                u = u.reshape([121, 240])
                                u = np.ma.masked_where(u==9999,u)
                            else:
                                u = aaaa
                            t = load_message_from_file(
                                file_path=analdata,
                                parameter='v',
                                level_type="isobaricInhPa",
                                level=plev,
                            )
                            if t is not None:
                                v = eccodes.codes_get_double_array(t, "values")
                                v = v.reshape([121, 240])
                                v = np.ma.masked_where(v==9999,v)
                            else:
                                v = aaaa
                            anal = np.sqrt(u ** 2 + v ** 2)
                            analu = u;
                            analv = v
                            if os.access(climdata, os.F_OK):
                                t = load_message_from_file(
                                    file_path=climdata,
                                    parameter={
                                        "shortName": "u",
                                        "dataTime": int(str(st) + '00')
                                    },
                                    level_type="isobaricInhPa",
                                    level=plev,
                                )
                                if t is not None:
                                    u = eccodes.codes_get_double_array(t, "values")
                                    u = u.reshape([121, 240])
                                else:
                                    u = aaaa
                                t = load_message_from_file(
                                    file_path=climdata,
                                    parameter={
                                        "shortName": "v",
                                        "dataTime": int(str(st) + '00')
                                    },
                                    level_type="isobaricInhPa",
                                    level=plev,
                                )
                                if t is not None:
                                    v = eccodes.codes_get_double_array(t, "values")
                                
                                    v = v.reshape([121, 240])
                                else:
                                    v = aaaa
                                cmean = np.sqrt(u ** 2 + v ** 2)
                                cliu = u;
                                cliv = v;
                                
                            #cmean = np.ones_like(aaaa)*-999.00
                        ###########################################################################################
                        #################calculation the scores####################################################

                        kk = 0
                        for domin in domain:
                            kk += 1
                            sj = int((90. - domin[1]) / 1.5)
                            ej = int((90. - domin[0]) / 1.5)
                            si = int(domin[2] / 1.5)
                            ei = int(domin[3] / 1.5)
                            fc = fcst[sj:ej + 1, si:ei + 1]
                            ana = anal[sj:ej + 1, si:ei + 1]
                            cli = cmean[sj:ej + 1, si:ei + 1]
                            lats = llat[sj:ej + 1, si:ei + 1]
                            fc = np.ma.masked_where(fc==9999,fc)
                            ana = np.ma.masked_where(fc.mask,ana)
                            cli = np.ma.masked_where(fc.mask, cli)
                            lats = np.ma.masked_where(fc.mask,lats)
                           
                            print(var,fcstdata,analdata,"fc",np.ma.mean(fc),"ana",np.mean(ana))
                            if np.isnan(np.ma.mean(fc)):
                                continue
                            if var != 'wind' and var != "wdir":
                                mse = np.sum((fc - ana) * (fc - ana) * np.cos(lats * np.pi / 180.))
                            elif var == "wind":
                                fcu = fcstu[sj:ej + 1, si:ei + 1];
                                fcv = fcstv[sj:ej + 1, si:ei + 1]
                                anu = analu[sj:ej + 1, si:ei + 1];
                                anv = analv[sj:ej + 1, si:ei + 1]                                
                                mse = np.sum(
                                    ((fcu - anu) * (fcu - anu) + (fcv - anv) * (fcv - anv)) * np.cos(lats * np.pi / 180.))
                            elif var == "wdir":
                                fcu = fcstu[sj:ej + 1, si:ei + 1];
                                fcv = fcstv[sj:ej + 1, si:ei + 1]
                                anu = analu[sj:ej + 1, si:ei + 1];
                                anv = analv[sj:ej + 1, si:ei + 1]  
                                clu = cliu[sj:ej + 1, si:ei + 1];
                                clv = cliv[sj:ej + 1, si:ei + 1]
                                
                                tmp = (fcu*anu+fcv*anv)/(fc*ana) 
                                tmp[np.where(tmp>1)]=1
                                angle = np.arccos(tmp)*180/np.pi
                                mse = np.sum(
                                    (angle*angle) * np.cos(lats * np.pi / 180.))
                                
                                tmpf = (fcu*clu+fcv*clv)/(fc*cli) 
                                tmpf[np.where(tmpf>1)]=1
                                anglef = np.arccos(tmpf)*180/np.pi

                                tmpa = (anu*clu+anv*clv)/(ana*cli) 
                                tmpa[np.where(tmpa>1)]=1
                                anglea = np.arccos(tmpa)*180/np.pi
                                
                                fc = angle
                                ana = np.zeros_like(fc)

                            mse = mse / np.sum(np.cos(lats * np.pi / 180.))
                            

                            rmse[tt - 1, tv - 1, tk - 1, kk - 1] = np.sqrt(mse)

                            bias[tt - 1, tv - 1, tk - 1, kk - 1] = np.sum((fc - ana) * np.cos(lats * np.pi / 180.))
                            bias[tt - 1, tv - 1, tk - 1, kk - 1] = bias[tt - 1, tv - 1, tk - 1, kk - 1] / np.sum(
                                np.cos(lats * np.pi / 180.))

                            abias[tt - 1, tv - 1, tk - 1, kk - 1] = np.sum(np.abs(fc - ana) * np.cos(lats * np.pi / 180.))
                            abias[tt - 1, tv - 1, tk - 1, kk - 1] = abias[tt - 1, tv - 1, tk - 1, kk - 1] / np.sum(
                                np.cos(lats * np.pi / 180.))
                  
                            std[tt - 1, tv - 1, tk - 1, kk - 1] = np.sum(
                                (fc - ana - bias[tt - 1, tv - 1, tk - 1, kk - 1]) * (
                                            fc - ana - bias[tt - 1, tv - 1, tk - 1, kk - 1]) * np.cos(lats * np.pi / 180.))
                            std[tt - 1, tv - 1, tk - 1, kk - 1] = np.sqrt(
                                std[tt - 1, tv - 1, tk - 1, kk - 1] / np.sum(np.cos(lats * np.pi / 180.)))

                            rmsem[tt - 1, tv - 1, tk - 1, kk - 1] = abs(bias[tt - 1, tv - 1, tk - 1, kk - 1])
                            rmsep[tt - 1, tv - 1, tk - 1, kk - 1] = rmse[tt - 1, tv - 1, tk - 1, kk - 1] - rmsem[
                                tt - 1, tv - 1, tk - 1, kk - 1]

                            if var == "wdir":
                                fcm = np.sum((anglef) * np.cos(lats * np.pi / 180.))
                                fcm = fcm / np.sum(np.cos(lats * np.pi / 180.))
                                ocm = np.sum((anglea) * np.cos(lats * np.pi / 180.))
                                ocm = ocm / np.sum(np.cos(lats * np.pi / 180.))
                                
                                acc1 = np.sum((anglef - fcm) * (anglea - ocm) * np.cos(lats * np.pi / 180.))
                                acc2 = np.sum((anglef - fcm) * (anglef - fcm) * np.cos(lats * np.pi / 180.))
                                acc3 = np.sum((anglea - ocm) * (anglea - ocm) * np.cos(lats * np.pi / 180.))

                                acc[tt - 1, tv - 1, tk - 1, kk - 1] = acc1 / (np.sqrt(acc2 * acc3))
                                
                            else:
                                fcm = np.sum((fc - cli) * np.cos(lats * np.pi / 180.))
                                fcm = fcm / np.sum(np.cos(lats * np.pi / 180.))
                                ocm = np.sum((ana - cli) * np.cos(lats * np.pi / 180.))
                                ocm = ocm / np.sum(np.cos(lats * np.pi / 180.))
                                
                                acc1 = np.sum((fc - cli - fcm) * (ana - cli - ocm) * np.cos(lats * np.pi / 180.))
                                acc2 = np.sum((fc - cli - fcm) * (fc - cli - fcm) * np.cos(lats * np.pi / 180.))
                                acc3 = np.sum((ana - cli - ocm) * (ana - cli - ocm) * np.cos(lats * np.pi / 180.))
                                acc[tt - 1, tv - 1, tk - 1, kk - 1] = acc1 / (np.sqrt(acc2 * acc3))
                                                            
                            if rmse[tt - 1, tv - 1, tk - 1, kk - 1] > 1000.:
                                rmse[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                bias[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                acc[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                std[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                abias[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                rmsep[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                rmsem[tt - 1, tv - 1, tk - 1, kk - 1] = -999
                                
        acc[np.isnan(acc)] = np.nan;#-999;
        rmse[np.isnan(rmse)] = np.nan;
        bias[np.isnan(bias)] = np.nan;
        std[np.isnan(std)] = np.nan;
        abias[np.isnan(abias)] = np.nan;
        rmsep[np.isnan(rmsep)] = np.nan;
        rmsem[np.isnan(rmsem)] = np.nan

    #        acc = np.full((int(length), len(VAR), len(plevs), len(region)), np.nan)
        tt = -1
        if True:
            for i in range(0, itimedelta * int(length), itimedelta):
                outdate = ccdate -  datetime.timedelta(hours=i)
                tt += 1
                tv = 0
                for var in VAR:
                    tv += 1
                    tk = 0
                    for plev in plevs:
                        tk += 1
                        kk = 0
                        for domin in domain:
                            kk += 1
                            if np.isnan(rmse[tt - 1, tv - 1, tk - 1, kk - 1]) and\
                                    np.isnan(acc[tt - 1, tv - 1, tk - 1, kk - 1]) and\
                                    np.isnan(abias[tt - 1, tv - 1, tk - 1, kk - 1]):
                                pass
                            else:
                                resdf.loc[len(resdf)] = {"mode_type":pyweb2java(ifcst),"reference_data_type":pyweb2java(iref),"height":str(plev),"meteorological_element_type":pyweb2java(var),\
                                  "area_id":region[kk-1],"forecast_time":outdate,"forecast_hour":outdate.strftime("%H"),"forecast_interval":i+dd,"pc":np.nan,"acc":acc[tt - 1, tv - 1, tk - 1, kk - 1],\
                                  "rmse":rmse[tt - 1, tv - 1, tk - 1, kk - 1],"mae":abias[tt - 1, tv - 1, tk - 1, kk - 1]}
            t1 = datetime.datetime.now()
            batch_size = 10000
            for i in range(0,len(resdf),batch_size):
                batch = resdf.iloc[i:i+batch_size]
                clickclient.insert_df("upper_area_verification_result",batch)
            print(datetime.datetime.now()-t1)
        break
        if mess == "":
            mess = "succeed"
    return status,mess
    
