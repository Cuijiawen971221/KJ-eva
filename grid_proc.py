from logging import FileHandler
from multiprocessing import Process, Pool
import subprocess
import yaml
import time
import datetime
from typeguard import typechecked
import random
import string
import os
import config
import xesmf as xe
import xarray as xr
import numpy as np
import glob
import pickle
import pandas as pd
from cfgrib.xarray_to_grib import to_grib
import cfgrib
#import pygrib
import utils
from clickhouse_util import clickclient
from py2java import *
from nwpc_data.grib.eccodes import load_message_from_file
import eccodes
import humidity_calc 
import grib_dict
import pynio_split
import grib2io
from grib2io import iplib
import traceback
import emend


KJ_ENV = False
globalConf = config.pparms("./pathconfig.yaml").param

#mport gridder
class package():
    startTime : datetime.datetime
    fcst : str
    para: str
    fh : str
    dt : int
    def __init__(self,st,fc,pa,fh,dt):
        self.startTime = st
        self.fcst = fc
        self.para = pa
        self.fh = fh
        self.dt = dt

def getAWSindex(var):
    indexdict={
        "lat":1,    # 经度
        "lon":2,    # 纬度
        "2t":3,     # 温度
        "2r":4,     # 相对湿度
        "10u":5,    # u风
        "10v":6,    # v风
        "mslp":7,   # 海平面气压
        "sp":8,     # 场压
        "vis":9,    # 能见度
        "rad":10,   # 辐射 
        "rain1":11, # 1小时降水
        "rain24":12, # 6小时降水
        "lcc":13,   # 低云
        "2d":14,    # 露点温度
        "ch":15,    # 云高
        "tcc":16    # 总云
    }
    if var in indexdict.keys():
        return indexdict[var]
    else:
        return -999

def getKT1279FileIndex(var):
    FileIndex = {
        "2t":"T2",
        "10u":"UT",
        "10v":"VT",
        "mslp":"PR",
    }
    if var in FileIndex.keys():
        return FileIndex[var]
    else:
        return "XX"

def config_path(fcst):
    if fcst == "KT1279":
        fcstpath = globalConf.kt1279fcstpath
        outputpath = globalConf.kt1279outputpath
        toolspath =  globalConf.kt1279toolspath
        weight = globalConf.kt1279weightpoint
    elif fcst == "KT1279_CLOUD":
        fcstpath = globalConf.kt1279cloudfcstpath
        outputpath = globalConf.kt1279cloudoutputpath
        toolspath =  globalConf.kt1279cloudtoolspath
        weight = globalConf.kt1279cloudweightpoint
    elif fcst == "VISFCST":
        fcstpath = globalConf.visfcstfcstpath
        outputpath = globalConf.visfcstoutputpath
        toolspath =  globalConf.visfcsttoolspath
        weight = globalConf.visfcstweightpoint           
    elif fcst == "ERA5":
        fcstpath = globalConf.era5fcstpath
        outputpath = globalConf.era5outputpath
        toolspath =  globalConf.era5toolspath
        weight = globalConf.era5weightpoint
    elif fcst == "NCEP":
        fcstpath = globalConf.ncepfcstpath
        outputpath = globalConf.ncepoutputpath
        toolspath =  globalConf.nceptoolspath
        weight = globalConf.ncepweightpoint
    elif fcst == "CLDAS":
        fcstpath = globalConf.cldasfcstpath
        outputpath = globalConf.cldasoutputpath
        toolspath = globalConf.cldastoolspath
        weight = globalConf.cldasweightpoint
    elif fcst == "ECMWF":
        fcstpath = globalConf.ecmwffcstpath
        outputpath = globalConf.ecmwfoutputpath
        toolspath = globalConf.ecmwftoolspath
        weight = globalConf.ecmwfweightpoint
    elif fcst == "AUTO":
        fcstpath = globalConf.autofcstpath
        outputpath = globalConf.autooutputpath
        toolspath = globalConf.autotoolspath
        weight = globalConf.autoweightpoint
    elif fcst == "REGION":
        fcstpath = globalConf.regionfcstpath
        outputpath = globalConf.regionoutputpath
        toolspath = globalConf.regiontoolspath
        weight = globalConf.regionweightpoint
    elif fcst == "KJRH":
        fcstpath = globalConf.kjrhfcstpath
        outputpath = globalConf.kjrhoutputpath
        toolspath = globalConf.kjrhtoolspath
        weight = globalConf.kjrhweightpoint
    elif fcst == "CLIMATE":
        fcstpath = globalConf.climatefcstpath
        outputpath = globalConf.climateoutputpath
        toolspath = globalConf.climatetoolspath
        weight = globalConf.climateweightpoint
    elif fcst == "CMA_GFS":
        fcstpath = globalConf.cmagfsfcstpath
        outputpath = globalConf.cmagfsoutputpath
        toolspath = globalConf.cmagfstoolspath
        weight = globalConf.cmagfsweightpoint
    elif fcst == "EMEND":
        fcstpath = globalConf.emendfcstpath
        outputpath = ""
        toolspath = ""
        weight = ""
    return fcstpath,outputpath,toolspath,weight


def fill_resdf(resdf,result,startTime,i,slat,fcst,lccScale=1.0,visScale=1.0):
    for ii in range(result.shape[0]):
        res = result[ii,:]
        uuu = -res[getAWSindex("10u")]
        vvv = -res[getAWSindex("10v")]
        wsp, wdir = utils.getWindWdir(uuu,vvv)
        if  res[getAWSindex("lcc")] !=-999.0:
            outlcc = res[getAWSindex("lcc")]*lccScale
        else:
            outlcc = -999.0
        if  res[getAWSindex("tcc")] !=-999.0:
            outtcc = res[getAWSindex("tcc")]*lccScale
        else:
            outtcc = -999.0
        
        if res[getAWSindex("sp")] != -999.0:
            sssppp = res[getAWSindex("sp")]
        else:
            sssppp = -999.0

        if res[getAWSindex("mslp")] != -999.0:
            mmslpp = res[getAWSindex("mslp")]
        else:
            mmslpp = -999.0

        if res[getAWSindex("2r")] == -999.0 and res[getAWSindex("2d")] != -999.0:
            rrr222 = humidity_calc.hum(res[getAWSindex("2t")],res[getAWSindex("2d")],res[getAWSindex("sp")]*100,True)
        else:
            rrr222 = res[getAWSindex("2r")]

        if res[getAWSindex("vis")] != -999.0:
            visss = res[getAWSindex("vis")] * visScale
        else:
            visss = -999.0

        tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
        resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": startTime.strftime("%H") , "mode_type":pyweb2java(fcst), "forecast_interval": i,\
        "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": rrr222,\
        "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain24")], "pressure": sssppp,\
        "sea_level_pressure": mmslpp,"radiation":res[getAWSindex("rad")],"visibility":visss,\
        "total_cloud_cover":outtcc,"low_cloud_cover":outlcc,"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    return resdf



#
def point_allInone(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight:str, station = None)->tuple:
    status = True
    mess = ""
    outpath,fcstpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")

    VAR=para

    if not isinstance(station, xr.Dataset):
        with open("/home/yunyao/workshop/met/met_backend/aws_station_info", "rb") as f:
            station = pickle.load(f)
    # 将站点信息组建为插值网格对象
    ds_out = xr.Dataset({
        "lat":("loc",np.array(station["lat"])),
        "lon":("loc",np.array(station["lon"]))
        }
    )
# create new empty result
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(ds_out.lat)

    result = np.ones((line, paramlength)) * -999.0
    dataf = pd.DataFrame(
        columns=["ID", "lat", "lon", "2t","2d", "2r", "u10", "v10", "mslp", "sp", "vis", "rad", "rain1",
                 "rain6", "lcc","tcc","wind","wdir","ch"])
############################################

    orig_status = True
    regridder = None
    #
    gribReader = grib_dict.grib2io_ground_shortName   

    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            #esult = -999.0
            result = np.ones((line, paramlength)) * -999.0

            for var in VAR:
                if var in gribReader.keys():
                    index = getAWSindex(var)
#                    file_index = getKT1279FileIndex(var)
#                    print(fcstpath+"/KT1279/{:s}/*{:s}*-{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    filename = glob.glob(fcstpath + "/{:s}/normal/{:s}/raw{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))
                    print(f"FIND FILENAME PATTERN",fcstpath + "/{:s}/normal/{:s}/raw{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))
                    if len(filename)>0:
                       
                       filename = filename[0]
                       print(f"READ {var} FROM "+filename)
                       try:
                           
                           ds = xr.open_dataset(filename,engine="grib2io",filters={"shortName":gribReader[var][0],"typeOfFirstFixedSurface":gribReader[var][2]})
    #                       print(ds)
                           if len(ds)==0: continue
                           
                           if regridder == None:
                               if not os.path.exists(f"{weight}/{tmpweight}"):
                                   regridder = xe.Regridder(ds,ds_out,"bilinear",locstream_out=True)
                                   regridder.to_netcdf(f"{weight}/{tmpweight}")
                               else:
                                   regridder = xe.Regridder(ds,ds_out,"bilinear",locstream_out=True,weights=f"{weight}/{tmpweight}")
                           
                       
                           ds_inp = regridder(ds[gribReader[var][0]],skipna=True)
                           result[:,index] = ds_inp.values
                       except ValueError:
                           print("key value error")
                           status= False
                           mess += f"{var} cant open,"

            if (result == -999).all():
                pass
            else:
                dataf["ID"] = np.array(station["0000id"])
                dataf["lat"] = np.array(station["lat"])
                dataf["lon"] = np.array(station["lon"])
                dataf["2t"] = result[:, 3]
                dataf["2r"] = result[:, 4]
                dataf["u10"] = result[:, 5]
                dataf["v10"] = result[:, 6]
                dataf["mslp"] = result[:, 7]
                dataf["sp"] = result[:, 8]
                dataf["vis"] = result[:, 9]
                dataf["rad"] = result[:, 10]
                dataf["rain1"] = result[:, 11]
                dataf["rain6"] = result[:, 12]
                dataf["lcc"] = result[:, 13]
                dataf["2d"] = result[:, 14]
                dataf["ch"] = result[:,15]
                dataf["tcc"] = result[:,16]
                #if not isinstance(station, xr.Dataset):
                if False:
                    print("##########################",outpath + "/{:s}/point{:s}{:0>3d}.pkl".format(fcst,YYYYMMDDHH, i))
                    with open(outpath + "/{:s}/point{:s}{:0>3d}.pkl".format(fcst,YYYYMMDDHH, i), "wb") as f:
                        pickle.dump(dataf, f)
    else:
        status = False
        mess = "task not in db"
    if mess =="":
        mess == "succeed"
    if not isinstance(station,xr.Dataset):
        return status,mess
    else:
        return status,mess,dataf


#自动站插值
@typechecked
def point_kt1279(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight:str, station = None)->tuple:
    print("comming in kt1279")
    status = True
    mess = ""

    fcstpath,outpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")

    VAR=para

    gribReader = {
        "2t": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "2t"
        }, "t2m"],
        "10u": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "10u"
        }, "u10"],
        "10v": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "10v"
        }, "v10"],
        "mslp": [{
            "typeOfLevel": "meanSea",
            "shortName": "mslet"
        }, "mslet"],
        "sp": [{
            "typeOfLevel": "surface",
            "shortName": "sp"
        }, "sp"],
        "rain1": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "instant"
        }, "cpr"],
        "rain6": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "avg"
        }, "cpr"],
        "vis": [{
            "typeOfLevel": "surface",
            "shortName": "vis",
        }, "vis"],
        "2r": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "2r",
        }, "r2"],
        "lcc": [{
            "typeOfLevel": "lowCloudLayer",
            "shortName": "lcc",
            "stepType": "instant"
        }, "lcc"],
        "2d": [{
            "typeOfLevel": "lowCloudLayer",
            "shortName": "2d",
        }, "d2m"],
        "tcc": [{
            "typeOfLevel": "atmosphere",
            "shortName": "tcc",
            "stepType": "instant"
        }, "tcc"],
        "rad": [{
            "typeOfLevel": "surface",
            "shortName": "sdswrf",
            "stepType": "instant"
        }, "sdswrf"],
    }
    # read aws station,如果没有传入站点信息，那么就从数据里面提取

    if not isinstance(station, xr.Dataset):
        with open("/home/yunyao/workshop/met/met_backend/aws_station_info", "rb") as f:
            station = pickle.load(f)
    # 将站点信息组建为插值网格对象
    ds_out = xr.Dataset({
        "lat":("loc",np.array(station["lat"])),
        "lon":("loc",np.array(station["lon"]))
    })

    paramlength = 14+3 # id ,lon, lat, T,rh,u,v,p,rain,vis    # 参数列表长度。+3 为id，lat， lon
    line = len(ds_out.lat)

    result = np.ones((line,paramlength))*-999.0
    dataf = pd.DataFrame(
        iolumns=["ID", "lat", "lon", "2t","2d", "2r", "u10", "v10", "mslp", "sp", "vis", "rad", "rain1",
                 "rain6", "lcc","tcc"])
    #check db
    orig_status = True
    # 
    regridder = None
    print(fh[0],fh[1]+1)
    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            for var in VAR:
                if True:
                    index = getAWSindex(var)
                    file_index = getKT1279FileIndex(var)
                    print(fcstpath+"/KT1279/{:s}/*{:s}*-{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    filename = glob.glob(fcstpath+"/KT1279/{:s}/*{:s}*-{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    if len(filename)>0:
                        filename = filename[0]
                        try:
                            ds = xr.open_dataset(filename)
                            print(ds)
                            if regridder == None:
                                if not os.path.exists(f"{weight}/{tmpweight}"):
                                    regridder = xe.Regridder(ds,ds_out,"bilinear",locstream_out=True)
                                    regridder.to_netcdf(f"{weight}/{tmpweight}")
                                else:
                                    regridder = xe.Regridder(ds,ds_out,"bilinear",locstream_out=True,weights=f"{weight}/{tmpweight}")
                            ds_inp = regridder(ds[gribReader[var][1]])
                            result[:,index] = ds_inp.values
                        except ValueError:
                            status= False
                            mess += f"{var} cant open,"
            if (result == -999).all():
                pass
            else:
                dataf["ID"] = np.array(station["0000id"])
                dataf["lat"] = np.array(station["lat"])
                dataf["lon"] = np.array(station["lon"])
                dataf["2t"] = result[:, 3]
                dataf["2r"] = result[:, 4]
                dataf["u10"] = result[:, 5]
                dataf["v10"] = result[:, 6]
                dataf["mslp"] = result[:, 7]
                dataf["sp"] = result[:, 8]
                dataf["vis"] = result[:, 9]
                dataf["swr"] = result[:, 10]
                dataf["rain1"] = result[:, 11]
                dataf["rain6"] = result[:, 12]
                dataf["lc"] = result[:, 13]
                dataf["2d"] = result[:, 14]
                if not isinstance(station, xr.Dataset):
                    with open(outpath + "/NCEP/point{:s}{:0>3d}.pkl".format(YYYYMMDDHH, i), "wb") as f:
                        pickle.dump(dataf, f)
    else:
        status = False
        mess = "task not in db"
    if mess =="":
        mess == "succeed"
    if not isinstance(station,xr.Dataset):
        return status,mess
    else:
        return status,mess, dataf

@typechecked
def point_ncep(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight:str, station = None)->tuple:
    #station :  机场位置信息
    status = True
    mess = ""
    fcstpath,outpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH=  startTime.strftime("%Y%m%d%H")
    YYYYMMDD=  startTime.strftime("%Y%m%d")
    HH=  startTime.strftime("%H")
    VAR=para
    # read aws station
    if not isinstance(station, xr.Dataset):
        with open("/home/yunyao/workshop/met/met_backend/aws_station_info", "rb") as f:
            station = pickle.load(f)
    ds_out = xr.Dataset({
        "lat":("loc",np.array(station["lat"])),
        "lon":("loc",np.array(station["lon"]))
    })
    paramlength = 13+3 # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(ds_out.lat)

    result = np.ones((line,paramlength))*-999.0
    dataf = pd.DataFrame(
        columns=["ID", "lat", "lon", "2t","2d", "2r", "u10", "v10", "mslp", "sp", "vis", "rad", "rain1",
                 "rain6", "lcc","tcc"])
    #check db
    orig_status = True
    # 
    regridder = None
    gribReader = {
        "2t": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "2t"
        }, "t2m"],
        "10u": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "10u"
        }, "u10"],
        "10v": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "10v"
        }, "v10"],
        "mslp": [{
            "typeOfLevel": "meanSea",
            "shortName": "mslet"
        }, "mslet"],
        "sp": [{
            "typeOfLevel": "surface",
            "shortName": "sp"
        }, "sp"],
        "rain1": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "instant"
        }, "cpr"],
        "rain6": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "avg"
        }, "cpr"],
        "vis": [{
            "typeOfLevel": "surface",
            "shortName": "vis",
        }, "vis"],
        "2r": [{
            "typeOfLevel": "heightAboveGround",
            "shortName": "2r",
        }, "r2"],
        "lcc": [{
            "typeOfLevel": "lowCloudLayer",
            "shortName": "lcc",
            "stepType": "instant"
        }, "lcc"],
        "2d": [{
            "typeOfLevel": "lowCloudLayer",
            "shortName": "2d",
        }, "d2m"],
        "tcc": [{
            "typeOfLevel": "atmosphere",
            "shortName": "tcc",
            "stepType": "instant"
        }, "tcc"],
        "rad": [{
            "typeOfLevel": "surface",
            "shortName": "sdswrf",
            "stepType": "instant"
        }, "sdswrf"],
    }
    if orig_status:
        for i in range(fh[0],fh[1]+1,dt):
            for var in VAR:
                if True: #if var=="2t":
                    index = getAWSindex(var)
                    filename = glob.glob(fcstpath+"/NCEP/{:s}/*t{:0>2d}z*f{:0>3d}.bin".format(YYYYMMDD,int(HH),i))
                    if len(filename)>0:
                        filename = filename[0]
                        print(filename)
                        try:
                            ds = xr.open_dataset(filename,backend_kwargs={
                                "filter_by_keys": gribReader[var][0]
                            },engine="cfgrib")
                            
                            if regridder == None:
                                if not os.path.exists(f"{weight}/{tmpweight}"):
                                    regridder = xe.Regridder(ds,ds_out,"bilinear",locstream_out=True)
                                    regridder.to_netcdf(f"{weight}/{tmpweight}")
                                else:
                                    regridder = xe.Regridder(ds, ds_out, "bilinear", locstream_out=True,weights=f"{weight}/{tmpweight}")
                            ds_inp = regridder(ds[gribReader[var][1]])
                            result[:,index] = ds_inp.values
                            print(result[:,index])
                        except :
                            status= False
                            mess += f"{var} cant open,"
                            print(mess )

            if (result==-999).all():
                pass
            else:
                dataf["ID"] = np.array(station["0000id"])
                dataf["lat"] = np.array(station["lat"])
                dataf["lon"] = np.array(station["lon"])
                dataf["2t"] = result[:, 3]
                dataf["2r"] = result[:, 4]
                dataf["u10"] = result[:, 5]
                dataf["v10"] = result[:, 6]
                dataf["mslp"] = result[:, 7]
                dataf["sp"] = result[:, 8]
                dataf["vis"] = result[:, 9]
                dataf["swr"] = result[:, 10]
                dataf["rain1"] = result[:, 11]
                dataf["rain6"] = result[:, 12]
                dataf["lc"] = result[:, 13]
                if not isinstance(station, xr.Dataset):
                    with open(outpath+"/NCEP/point{:s}{:0>3d}.pkl".format(YYYYMMDDHH,i),"wb") as f:
                        pickle.dump(dataf,f)
    else:
        status = False
        mess = "task not in db"
    if mess=="":
        mess = "succeed"

    if not isinstance(station,xr.Dataset):
        return status,mess
    else:
        return status,mess,dataf

@typechecked
def point_ecmwf(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight:str, station = None)->tuple:
    status = True
    mess = ""
    fcstpath, outpath, toolspath, weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = para
    # read aws station
    if not isinstance(station, xr.Dataset):
        with open("/home/yunyao/workshop/met/met_backend/aws_station_info", "rb") as f:
            station = pickle.load(f)
    ds_out = xr.Dataset({
        "lat": ("loc", np.array(station["lat"])),
        "lon": ("loc", np.array(station["lon"]))
    })
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(ds_out.lat)

    result = np.ones((line, paramlength)) * -999.0
    dataf = pd.DataFrame(
        columns=["ID", "lat", "lon", "2t", "2d", "2r", "u10", "v10", "mslp", "sp", "vis", "rad", "rain1",
                 "rain6", "lcc", "tcc"])
    # check db
    orig_status = True
    regridder = None
    gribReader = {
        "2t": [{
            "typeOfLevel": "surface",
            "shortName": "2t"
        }, "t2m"],
        "10u": [{
            "typeOfLevel": "surface",
            "shortName": "10u"
        }, "u10"],
        "10v": [{
            "typeOfLevel": "surface",
            "shortName": "10v"
        }, "v10"],
        "mslp": [{
            "typeOfLevel": "surface",
            "shortName": "mslet"
        }, "mslet"],
        "sp": [{
            "typeOfLevel": "surface",
            "shortName": "sp"
        }, "sp"],
        "rain1": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "instant"
        }, "cpr"],
        "rain6": [{
            "typeOfLevel": "surface",
            "shortName": "cpr",
            "stepType": "avg"
        }, "cpr"],
        "vis": [{
            "typeOfLevel": "surface",
            "shortName": "vis",
        }, "vis"],
        "2r": [{
            "typeOfLevel": "surface",
            "shortName": "2r",
        }, "r2"],
        "lcc": [{
            "typeOfLevel": "surface",
            "shortName": "lcc",
            "stepType": "instant"
        }, "lcc"],
        "2d": [{
            "typeOfLevel": "surface",
            "shortName": "2d",
        }, "d2m"],
        "tcc": [{
            "typeOfLevel": "surface",
            "shortName": "tcc",
            "stepType": "instant"
        }, "tcc"],
        "rad": [{
            "typeOfLevel": "surface",
            "shortName": "sdswrf",
            "stepType": "instant"
        }, "sdswrf"],
    }

    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            for var in VAR:
                if True:  # if var=="2t":
                    index = getAWSindex(var)
                    fcstTime = startTime - datetime.timedelta(hours=i)
                    filename = glob.glob(fcstpath + "/ECMWF/{:s}/W_NAFP_C_ECMF_*{:s}001".format(YYYYMMDDHH,fcstTime.strftime("%m%d%H")))
                    if len(filename) > 0:
                        filename = filename[0]
                        print("asdfasdf",filename)
                        try:
                            ds = xr.open_dataset(filename, backend_kwargs={
                                "filter_by_keys": gribReader[var][0]
                            }, engine="cfgrib")

                            if regridder == None:
                                if not os.path.exists(f"{weight}/{tmpweight}"):
                                    regridder = xe.Regridder(ds, ds_out, "bilinear", locstream_out=True)
                                    regridder.to_netcdf(f"{weight}/{tmpweight}")
                                else:
                                    regridder = xe.Regridder(ds, ds_out, "bilinear", locstream_out=True,
                                                             weights=f"{weight}/{tmpweight}")
                            ds_inp = regridder(ds[gribReader[var][1]])
                            result[:, index] = ds_inp.values
                            print(result[:, index])
                        except:
                            status = False
                            mess += f"{var} cant open,"
                            print(mess)

            if (result == -999).all():
                pass
            else:
                dataf["ID"] = np.array(station["0000id"])
                dataf["lat"] = np.array(station["lat"])
                dataf["lon"] = np.array(station["lon"])
                dataf["2t"] = result[:, 3]
                dataf["2r"] = result[:, 4]
                dataf["u10"] = result[:, 5]
                dataf["v10"] = result[:, 6]
                dataf["mslp"] = result[:, 7]
                dataf["sp"] = result[:, 8]
                dataf["vis"] = result[:, 9]
                dataf["swr"] = result[:, 10]
                dataf["rain1"] = result[:, 11]
                dataf["rain6"] = result[:, 12]
                dataf["lc"] = result[:, 13]
                dataf["2d"] = result[:, 14]
                if not isinstance(station, xr.Dataset):
                    with open(outpath + "/NCEP/point{:s}{:0>3d}.pkl".format(YYYYMMDDHH, i), "wb") as f:
                        pickle.dump(dataf, f)
    else:
        status = False
        mess = "task not in db"
    if mess == "":
        mess = "succeed"

    if not isinstance(station, xr.Dataset):
        return status, mess
    else:
        return status, mess, dataf

#机场站点插值
#理论上机场站点不会改动，使用静态地理坐标
@typechecked 
def airport_allInone(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="",station = None):
    status = True
    mess = ""
    outpath,fcstpath, toolspath, weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = para
    # read aws station
   # if KJ_ENV:
   #     if not isinstance(station, xr.Dataset):
   #         station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")
   #         with open("./station_info.pkl","rb") as f: 
    #            station = pickle.load(f)
    
    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)
    # check db
    orig_status = True
    #
    gribReader = grib_dict.grib2io_ground_shortName

    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt): # 实时插值，fh[0] == fh[1]

            filename = glob.glob(fcstpath + "/{:s}/normal/{:s}/raw{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))
            if len(filename) > 0:
                result = np.ones((line, paramlength)) * -999.0
                filename = filename[0]
                with grib2io.open(filename) as f:
                    for var in VAR:
                        if var == "rain24": continue
                        index = getAWSindex(var)
                        sdata = np.ones(line) * -999.0
                        if var in gribReader.keys(): 
                            msg = f.select(shortName=gribReader[var][0],level=gribReader[var][1])
                            if len(msg)!=1:
                                continue
                            msg = msg[0]
                            grid_def_in = grib2io.Grib2GridDef(msg.gdtn,msg.gridDefinitionTemplate)
                            sdata = grib2io.interpolate_to_stations(msg.data,"bilinear",grid_def_in,slat.values,slon.values)
                            result[:, index] = sdata
                if "rain24" in VAR  and (i-int(HH))-(i- int(HH))//24*24==0 :
                    var = "rain24"
                    
                    rain_filename = glob.glob(fcstpath+"/{:s}/rain/rain24/fcst{:s}*{:0>3d}.grb".format(fcst, YYYYMMDDHH, i))
                    print("%%%%%%%%%%%%%%%%%%%%% PATTERN {:s} MATCH {:s}".format(fcstpath+"/{:s}/rain/rain24/fcst{:s}*{:0>3d}.grb".format(fcst, YYYYMMDDHH, i),",".join(rain_filename)))
                    if len(rain_filename)!=0:
                        with grib2io.open(rain_filename[0]) as f :
                            index = getAWSindex(var)
                            sdata = np.ones(line) * -999.0 
    #                            print(f)
                            if var in gribReader.keys():
                                msg = f.select(shortName=gribReader[var][0])
    #                            print(msg)
                                if len(msg)==1:
                                    msg = msg[0]
                                    grid_def_in = grib2io.Grib2GridDef(msg.gdtn,msg.gridDefinitionTemplate)
                                    sdata = grib2io.interpolate_to_stations(msg.data,"bilinear",grid_def_in,slat.values,slon.values)
                                    result[:, index] = sdata
                                print(sdata)
                if (result == -999).all():
                    pass
                else:
                    result[:,1] = station["latitude"]
                    result[:,2] = station["longitude"]
                    resdf = fill_resdf(resdf,result,startTime,i,slat,fcst)
            else:
                pass

#        if KJ_ENV:
#            with open(fcstpath+"/{:s}/normal/{:s}/airport_interp_{:s}.{:0>3d}_{:0>3d}".format(fcst,YYYYMMDD, YYYYMMDDHH, fh[0],fh[1]),"wb") as f:
#                pickle.dump(resdf,f)
        
    if mess == "":
        mess = "succeed"
    #print(resdf.to_string())
    return status, mess, resdf



@typechecked 
def airport_ncep(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="",station = None):
    status = True
    mess = ""
    fcstpath, outpath, toolspath, weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = para
    # read aws station
    if not isinstance(station, xr.Dataset):
        station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")
    
    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    result = np.ones((line, paramlength)) * -999.0
    print(result.shape)
    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)
    # check db
    orig_status = True
    #
    gribReader = grib_dict.grib2io_ground_shortName

    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt): # 实时插值，fh[0] == fh[1]
            print(i)
            for var in VAR:
                if var in gribReader.keys():  # if var=="2t":
                    index = getAWSindex(var)
                    filename = glob.glob(fcstpath + "/NCEP/normal/{:s}/*t{:0>2d}z*f{:0>3d}.bin".format(YYYYMMDD, int(HH), i))
                    print(fcstpath + "/NCEP/normal/{:s}/*t{:0>2d}z*f{:0>3d}.bin".format(YYYYMMDD, int(HH), i))
                    if len(filename) > 0:
                        filename = filename[0]
                        ds = xr.open_dataset(filename,backend_kwargs={"filter_by_keys":gribReader[var][0]},engine="cfgrib")
                        #ds = xr.Dataset(data_vars ={gribReader[var][1]:(["latitude","longitude"],fcst_values)},coords ={"latitude":np.linspace(sslat,eelat,njj),\
                        #                                                      git                            "longitude":np.linspace(sslon,eelon,nii)})
                        tttt1 = datetime.datetime.now()
                        if len(ds.variables)>0:
                            ds_inp = ds[gribReader[var][1]].interp(latitude=slat,longitude=slon)
                            result[:, index] = ds_inp.values
                        print(datetime.datetime.now()-tttt1)
                else:
                    pass


            if (result == -999).all():
                pass
            else:
 #            result[0] = station["station_id"]
                result[:,1] = station["latitude"]
                result[:,2] = station["longitude"]
                resdf = fill_resdf(resdf,result,startTime,i,slat,fcst)
                #for ii in range(result.shape[0]):
                #    res = result[ii,:]
                #    uuu = -res[getAWSindex("10u")]
                #    vvv = -res[getAWSindex("10v")]
                #    wsp, wdir = utils.getWindWdir(uuu,vvv)
                #    tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
                #    resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": HH, "mode_type":pyweb2java(fcst), "forecast_interval": i,\
                #    "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": res[getAWSindex("2r")],\
                #    "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain1")], "pressure": res[getAWSindex("sp")]/100,\
                #    "sea_level_pressure": res[getAWSindex("mslp")]/100,"radiation":res[getAWSindex("rad")],"visibility":res[getAWSindex("vis")],\
                #    "total_cloud_cover":res[getAWSindex("tcc")]/10,"low_cloud_cover":res[getAWSindex("lcc")]/10,"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    if mess == "":
        mess = "succeed"
    print(resdf)
    #t1 = datetime.datetime.now()
    #batch_size = 100
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("airport_forecast_data", batch)
    #print(datetime.datetime.now() - t1)
    return status, mess, resdf


@typechecked
def airport_kt1279(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="", station = None)->tuple:
    print("comming in kt1279")
    status = True
    mess = ""

    fcstpath,outpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")

    VAR=para

    # read aws station,如果没有传入站点信息，那么就从数据里面提取

    if not isinstance(station, xr.Dataset):
        station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")

    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    result = np.ones((line,paramlength))*-999.0
    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)

    #check db
    orig_status = True
    gribReader = utils.gribReader[fcst]
    # 
    regridder = None
    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            for var in VAR:
                if True:
                    index = getAWSindex(var)
                    file_index = getKT1279FileIndex(var)
                    if var in ["lcc","tcc","ch"]:
                        print(fcstpath+"/KT1279_CLOUD/{:s}/*{:s}*.{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                        filename = glob.glob(fcstpath+"/KT1279_CLOUD/{:s}/*{:s}*.{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    elif var =="vis":
                        print(fcstpath+"/VISFCST/{:s}/*{:s}*{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                        filename = glob.glob(fcstpath+"/VISFCST/{:s}/*{:s}*{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                        print(filename)
                    else:
                        print(fcstpath+"/KT1279/{:s}/*{:s}*-{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                        filename = glob.glob(fcstpath+"/KT1279/{:s}/*{:s}*-{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    if len(filename)>0:
                        filename = filename[0]
                        
                        try:
                            ds = xr.open_dataset(filename)
                            if len(ds.variables)>0:
                                ds_inp = ds[gribReader[var][1]].interp(latitude=slat,longitude=slon)
                                result[:, index] = ds_inp.values
                            
                        except ValueError:
                            status= False
                            mess += f"{var} cant open,"
                    else:
                        result[:,index] = -999.0        
            if (result == -999).all():
                pass
            else:
                result[:,1] = station["latitude"]
                result[:,2] = station["longitude"]
                resdf = fill_resdf(resdf,result,startTime,i,slat,fcst)
                #for ii in range(result.shape[0]):
                #    res = result[ii,:]
                #    uuu = -res[getAWSindex("10u")]
                #    vvv = -res[getAWSindex("10v")]
                #    wsp, wdir = utils.getWindWdir(uuu,vvv)
                #    outlcc = 
                #    if res[getAWSindex("2r")] == -999.0:
                #                       rrr222 = humidity_calc.hum(res[getAWSindex("2t")],res[getAWSindex("2d")],res[getAWSindex("sp")],True)
                #    else:
                #        rrr222 = res[getAWSindex("2r")]
                #    tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
                #    resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": HH, "mode_type":pyweb2java(fcst), "forecast_interval": i,\
                #    "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": rrr222,\
                #    "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain1")], "pressure": res[getAWSindex("sp")]/100,\
                #    "sea_level_pressure": res[getAWSindex("mslp")]/100,"radiation":res[getAWSindex("rad")],"visibility":res[getAWSindex("vis")],\
                #    "total_cloud_cover":res[getAWSindex("tcc")]/10,"low_cloud_cover":res[getAWSindex("lcc")]/10,"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    else:
        status = False
        mess = "task not in db"
    if mess =="":
        mess == "succeed"
    #t1 = datetime.datetime.now()
    #batch_size = 100
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("airport_forecast_data", batch)
    #print(datetime.datetime.now() - t1)
    print(resdf)
    return status, mess, resdf


@typechecked
def airport_kt1279_cloud(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="", station = None)->tuple:
    print("comming in kt1279 cloud")
    status = True
    mess = ""

    fcstpath,outpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")

    VAR=para

    # read aws station,如果没有传入站点信息，那么就从数据里面提取

    if not isinstance(station, xr.Dataset):
        station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")

    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    result = np.ones((line,paramlength))*-999.0
    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)

    #check db
    orig_status = True
    gribReader = utils.gribReader[fcst]
    # 
    regridder = None
    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            for var in VAR:
                if True:
                    index = getAWSindex(var)
                    file_index = getKT1279FileIndex(var)
                    print(fcstpath+"/KT1279_CLOUD/{:s}/*{:s}*.{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    filename = glob.glob(fcstpath+"/KT1279_CLOUD/{:s}/*{:s}*.{:0>3d}.grb".format(YYYYMMDDHH,file_index,i))
                    if len(filename)>0:
                        filename = filename[0]
                        try:
                            ds = xr.open_dataset(filename)
                            print(ds)
                            if len(ds.variables)>0:
                                ds_inp = ds[gribReader[var][1]].interp(latitude=slat,longitude=slon)
                                result[:, index] = ds_inp.values
                        except ValueError:
                            status= False
                            mess += f"{var} cant open,"
                            
            if (result == -999).all():
                pass
            else:
                result[:,1] = station["latitude"]
                result[:,2] = station["longitude"]
                for ii in range(result.shape[0]):
                    res = result[ii,:]
                    uuu = -res[getAWSindex("10u")]
                    vvv = -res[getAWSindex("10v")]
                    wsp, wdir = utils.getWindWdir(uuu,vvv)
                    if res[getAWSindex("2r")] == -999.0:
                        rrr222 = humidity_calc.hum(res[getAWSindex("2t")],res[getAWSindex("2d")],res[getAWSindex("sp")],True)
                    else:
                        rrr222 = res[getAWSindex("2r")]
                    tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
                    resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": HH, "mode_type":pyweb2java(fcst), "forecast_interval": i,\
                    "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": rrr222,\
                    "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain1")], "pressure": res[getAWSindex("sp")]/100,\
                    "sea_level_pressure": res[getAWSindex("mslp")]/100,"radiation":res[getAWSindex("rad")],"visibility":res[getAWSindex("vis")],\
                    "total_cloud_cover":res[getAWSindex("tcc")],"low_cloud_cover":res[getAWSindex("lcc")],"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    else:
        status = False
        mess = "task not in db"
    if mess =="":
        mess == "succeed"
    #t1 = datetime.datetime.now()
    #batch_size = 100
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("airport_forecast_data", batch)
    #print(datetime.datetime.now() - t1)
    print(resdf)
    return status, mess, resdf



@typechecked
def airport_ecmwf(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="", station = None)->tuple:
    status = True
    mess = ""
    fcstpath, outpath, toolspath, weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = para
    # read aws station
    if not isinstance(station, xr.Dataset):
        station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")

    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    result = np.ones((line, paramlength)) * -999.0
    print(result.shape)
    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)
    # check db
    orig_status = True
    #
    gribReader = {
    "2t": [{
        "typeOfLevel": "surface",
        "shortName": "2t"
    }, "t2m"],
    "10u": [{
        "typeOfLevel": "surface",
        "shortName": "10u"
    }, "u10"],
    "10v": [{
        "typeOfLevel": "surface",
        "shortName": "10v"
    }, "v10"],
    "mslp": [{
        "typeOfLevel": "surface",
        "shortName": "msl"
    }, "msl"],
    "sp": [{
        "typeOfLevel": "surface",
        "shortName": "sp"
    }, "sp"],
    "rain1": [{
        "typeOfLevel": "surface",
        "shortName": "cpr",
        "stepType": "instant"
    }, "cpr"],
    "rain6": [{
        "typeOfLevel": "surface",
        "shortName": "cpr",
        "stepType": "avg"
    }, "cpr"],
    "vis": [{
        "typeOfLevel": "surface",
        "shortName": "vis",
    }, "vis"],
    #"2r": [{
    #    "typeOfLevel": "heightAboveGround",
    #    "shortName": "2r",
    #}, "r2"],
    "lcc": [{
        "typeOfLevel": "surface",
        "shortName": "lcc",
    }, "lcc"],
    "2d":[{
        "typeOfLevel": "surface",
        "shortName": "2d",
    }, "d2m"],
    "tcc":[{
        "typeOfLevel": "surface",
        "shortName": "tcc",
    }, "tcc"],
    "rad":[{
        "typeOfLevel": "surface",
        "shortName": "sdswrf",
    }, "sdswrf"],
    "wind":[{},""],
    "wdir":[{},""],
    }

    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt): # 实时插值，fh[0] == fh[1]
            print(i)
            for var in VAR:
                if var in gribReader.keys():  # if var=="2t":
                    index = getAWSindex(var)
                    fffcstTime = startTime+datetime.timedelta(hours=i) # CALC FCST TIME 
                    filename = glob.glob(fcstpath + "/ECMWF/{:s}/W_NAFP_C_ECMF_{:s}*_P_C*{:s}001".format(YYYYMMDDHH, YYYYMMDD, fffcstTime.strftime("%m%d%H")))
                    print(filename)
                    print(fcstpath + "/ECMWF/{:s}/W_NAFP_C_ECMF_{:s}*_P_C*{:s}001".format(YYYYMMDDHH, YYYYMMDD, fffcstTime.strftime("%m%d%H")))
                    if len(filename) > 0:
                        filename = filename[0]
                        ds = xr.open_dataset(filename,backend_kwargs={"filter_by_keys":gribReader[var][0]},engine="cfgrib")
                        print(ds,gribReader[var][0])
                        #ds = xr.Dataset(data_vars ={gribReader[var][1]:(["latitude","longitude"],fcst_values)},coords ={"latitude":np.linspace(sslat,eelat,njj),\
                        #                                                      git                            "longitude":np.linspace(sslon,eelon,nii)})
                        tttt1 = datetime.datetime.now()
                        if len(ds.variables)>0:
                            ds_inp = ds[gribReader[var][1]].interp(latitude=slat,longitude=slon)
                            result[:, index] = ds_inp.values
                        print(datetime.datetime.now()-tttt1)
                else:
                    pass

            if (result == -999).all():
                pass
            else:
    #            result[0] = station["station_id"]
                result[:,1] = station["latitude"]
                result[:,2] = station["longitude"]
                resdf = fill_resdf(resdf,result,startTime,i,slat,fcst)
                #for ii in range(result.shape[0]):
                #    res = result[ii,:]
                #    uuu = -res[getAWSindex("10u")]
                #    vvv = -res[getAWSindex("10v")]
                #    wsp, wdir = utils.getWindWdir(uuu,vvv)
                #    if res[getAWSindex("2r")] < 0:
                #        rrr222 = humidity_calc.hum(res[getAWSindex("2t")],res[getAWSindex("2d")],res[getAWSindex("sp")],True)
                #    else:
                #        rrr222 = res[getAWSindex("2r")]
                #    tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
                #    resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": HH, "mode_type":pyweb2java(fcst), "forecast_interval": i,\
                #    "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": rrr222,\
                #    "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain1")], "pressure": res[getAWSindex("sp")]/100,\
                #    "sea_level_pressure": res[getAWSindex("mslp")]/100,"radiation":res[getAWSindex("rad")],"visibility":res[getAWSindex("vis")],\
                #    "total_cloud_cover":res[getAWSindex("tcc")]*10,"low_cloud_cover":res[getAWSindex("lcc")]*10,"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    if mess == "":
        mess = "succeed"
    print(resdf)
    #t1 = datetime.datetime.now()
    #batch_size = 100
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("airport_forecast_data", batch)
    #print(datetime.datetime.now() - t1)

    return status, mess, resdf


@typechecked
def airport_auto(startTime:datetime.datetime, fcst:str, para: list, fh:list, dt:int, tmpweight="", station = None)->tuple:
    print("comming in auto")
    status = True
    mess = ""

    fcstpath,outpath,toolspath,weight = config_path(fcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")

    VAR=para

    # read aws station,如果没有传入站点信息，那么就从数据里面提取

    if not isinstance(station, xr.Dataset):
        station = pd.read_csv("/home/user/workshop/met/met_backend/station_info.csv")

    slat = xr.DataArray(np.array(station["latitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    slon = xr.DataArray(np.array(station["longitude"]),dims="location",coords={"location":np.array(station["station_id"])})
    paramlength = 14 + 3  # id ,lon, lat, T,rh,u,v,p,rain,vis
    line = len(slat)

    result = np.ones((line,paramlength))*-999.0
    tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
             "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
             "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
             "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
    resdf = pd.DataFrame(tmpdf)

    #check db
    orig_status = True
    gribReader = {
    "2t": [{
        "typeOfLevel": "surface",
        "shortName": "2t"
    }, "t2m"],
    "2d":[{
        "typeOfLevel": "surface",
        "shortName": "2d"
    }, "d2m"],
    "10u": [{
        "typeOfLevel": "surface",
        "shortName": "10u",
        "level":10
    }, "u10"],
    "10v": [{
        "typeOfLevel": "surface",
        "shortName": "10v",
        "level":10
    }, "v10"],
    "mslp": [{
        "typeOfLevel": "surface",
        "shortName": "msl"
    }, "msl"],  
    "sp": [{
        "typeOfLevel": "surface",
        "shortName": "sp"
    }, "sp"], 
    "vis":[{
        "typeOfLevel": "surface",
        "shortName": "vis",
    }, "vis"],
    "lcc":[{
        "typeOfLevel": "surface",
        "shortName": "lcc",
    }, "lcc"],
    "tcc":[{
        "typeOfLevel":"surface",
        "shortName":"tcc",
    },"tcc"],
    }
    # 
    regridder = None
    if orig_status:
        for i in range(fh[0], fh[1] + 1, dt):
            for var in VAR:
                if True:
                    index = getAWSindex(var)
                    file_index = getAUTOFileIndex(var)
                    filename = glob.glob(fcstpath+"/AUTO/{:s}/*{:s}*.{:0>3d}".format(YYYYMMDDHH,file_index,i))
                    if len(filename)>0:
                        filename = filename[0]
                        print("filename",filename)
                        try:
                            ds = xr.open_dataset(filename,engine="cfgrib")
                            print(ds)
                            if len(ds.variables)>0:
                                ds_inp = ds[gribReader[var][1]].interp(latitude=slat,longitude=slon)
                                result[:, index] = ds_inp.values
                        except ValueError:
                            status= False
                            mess += f"{var} cant open,"
                            
            if (result == -999).all():
                pass
            else:
                result[:,1] = station["latitude"]
                result[:,2] = station["longitude"]
                for ii in range(result.shape[0]):
                    res = result[ii,:]
                    uuu = -res[getAWSindex("10u")]
                    vvv = -res[getAWSindex("10v")]
                    wsp, wdir = utils.getWindWdir(uuu,vvv)
                    tgtime = startTime+datetime.timedelta(hours=i-8) #数据库会默认加8小时，真的是傻逼
                    resdf.loc[len(resdf)] = {"station_id": str(slat["location"][ii].values), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": HH, "mode_type":pyweb2java(fcst), "forecast_interval": i,\
                    "temperature": res[getAWSindex("2t")], "dew_point_temperature": res[getAWSindex("2d")], "humidity": res[getAWSindex("2r")],\
                    "wind_speed": wsp, "wind_direction": wdir, "precipitation": res[getAWSindex("rain1")], "pressure": res[getAWSindex("sp")]/100,\
                    "sea_level_pressure": res[getAWSindex("mslp")]/100,"radiation":res[getAWSindex("rad")],"visibility":res[getAWSindex("vis")],\
                    "total_cloud_cover":res[getAWSindex("tcc")]/10,"low_cloud_cover":res[getAWSindex("lcc")]/10,"cloud_height":res[getAWSindex("ch")],"target_time":tgtime} 

    else:
        status = False
        mess = "task not in db"
    if mess =="":
        mess == "succeed"
    #t1 = datetime.datetime.now()
    #batch_size = 100
    #for i in range(0, len(resdf), batch_size):
    #    batch = resdf.iloc[i:i + batch_size]
    #    clickclient.insert_df("airport_forecast_data", batch)
    #print(datetime.datetime.now() - t1)
    print(resdf)
    return status, mess, resdf
#############################################################
@typechecked
def grib_region_tmp_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    finaloutpath = outputpath+f"/REGION/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    dataset = xr.Dataset()
    sstime = startTime#+datetime.timedelta(hours=8)
    GROUND = ["VS","UT","VT","T2","PR","LC","D2"]
    PRESS  = ["VV","UU","RH","HH","TT"]
    HGT10 = ["UT","VT"]
    HGT2 = ["VS","T2","PR","LC","D2"] 
    for i in range(fh[0],fh[1]+1,dt):
        # combine all dataset 
        filel = []
        ds_ground = xr.Dataset()
        for keVar in GROUND:
            reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d%H')}/KW{keVar}{sstime.strftime('%Y%m%d%H')}999"+"{:0>3d}.grb".format(i)
            fileseq = glob.glob(reg)
            if len(fileseq) == 0 : continue
            tmp_ds_ground = xr.open_mfdataset(fileseq,engine="pynio")
            if keVar in HGT10:  tmp_ds_ground = tmp_ds_ground.expand_dims({"lv_HTGL7":[10]})
            if keVar in HGT2:  tmp_ds_ground = tmp_ds_ground.expand_dims({"lv_HTGL2":[2]})
            ds_ground = xr.merge([ds_ground,tmp_ds_ground])

        #print("% % % % % % %",ds_ground)
        # 查看 CF 可用键

        
        ds_plev= xr.Dataset()
        for level in ["925","850","700","500","200"]:
            for keVar in PRESS:
                reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d%H')}/KW{keVar}{sstime.strftime('%Y%m%d%H')}{level}"+"{:0>3d}.grb".format(i)
                fileseq = glob.glob(reg)
                if len(fileseq)==0 : continue
                tmp_ds_plev = xr.open_mfdataset(fileseq,engine="pynio")
                tmp_ds_plev = tmp_ds_plev.expand_dims({"tmppress":[float(level)]})
                ds_plev = xr.merge([ds_plev,tmp_ds_plev])
        #rint("% % % % % % % %",ds_plev)
        
        Dataset = xr.merge([ds_ground,ds_plev])
        Dataset = Dataset.rename({"gridlat_3":"lat","gridlon_3":"lon"})
 #       print("&&&&&&&&&&&&&&&&&&&&&&",Dataset)
        ISBL_SFC = Dataset
        #print("1",datetime.datetime.now())
        #ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.REGIONParamDict,grib_dict.Grib2KeyDict)
        if not os.path.exists(weightpath + f"/PLEV_REGION_to_05.nc"):
            regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
            regridder.to_netcdf(weightpath + f"/PLEV_REGION_to_05.nc")
        else:
            regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_REGION_to_05.nc")
        #print("2",datetime.datetime.now())
        ISBL_SFC = regridder(ISBL_SFC,skipna=True)
        #print(ISBL_SFC["TMP_3_ISBL"].values)
        #ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
        ##
        #UU = - np.sin(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
        #VV = - np.cos(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
        #ISBL_SFC["10U"]=UU
        #ISBL_SFC["10V"]=VV
        #print("3",datetime.datetime.now())
        result1 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.REGIONTMPParamDict,grib_dict.Grib2KeyDict)
        for v in result1:
            for attr in grib_dict.Grib2KeyDict[v].keys():
                result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

        #ISBL_SFC = Dataset
        if not os.path.exists(weightpath + f"/PLEV_REGION_to_15.nc"):
            regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
            regridder.to_netcdf(weightpath + f"/PLEV_REGION_to_15.nc")
        else:
            regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_REGION_to_15.nc")
        ISBL_SFC = regridder(ISBL_SFC,skipna=True)
#        print(ISBL_SFC)
        #ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
        #UU = - np.sin(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
        #VV = - np.cos(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
        #ISBL_SFC["10U"]=UU
        #ISBL_SFC["10V"]=VV
        result3 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.REGIONTMPParamDict,grib_dict.Grib2KeyDict)
        
        # copy grib attrs
        for v in result1:
            for attr in grib_dict.Grib2KeyDict[v].keys():
                #result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


        result = result1
        result.attrs["GRIB_centre"]="rjtd"
        result.attrs["edition"]=2

        #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
        to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        to_grib(result, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        
        result = result3
        result.attrs["GRIB_centre"]="rjtd"
        result.attrs["edition"]=2

        #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
        to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        atleast +=1
        
        # grid

    if atleast == 0 : status = 1
    return status




@typechecked
def grib_region_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    finaloutpath = outputpath+f"/REGION/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    dataset = xr.Dataset()
    sstime = startTime#+datetime.timedelta(hours=8)
    for i in range(fh[0],fh[1]+1,dt):
        filel = []
        #reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d%H')}/NAFP_*{sstime.strftime('%Y%m%d%H')}*-EAI-{i:03d}.NC"
        for kk in ["CBH","CLD","D10","GPH","RH2","RHU","SRP","T2M","TD2","TEM","UWND","VWND","VIS","W10"]:
            print(kk)
            reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d%H')}/NAFP_*{sstime.strftime('%Y%m%d%H')}*{kk}-EAI-{i:03d}.NC"
            fileseq = glob.glob(reg)

            for fn in fileseq:
                filel.append(fn)    
        #filel = glob.glob(reg)
        #print(filel)
#reg = f"{fcstpath}/{fcst}/{YYYYMMDDHH}"+"/KT*.{:0>3d}".format(i)
        #for ff in filel:
  	#    if "CB" in ff or "LC" in ff or "TF" in ff:
        #        fileOut.append(ff)
        #filel = fileOut
        if len(filel) == 0: continue # 没有文件，跳过,但是不至于返回失败。
        #try:
        if True:
            ds = xr.open_mfdataset(filel,engine="pynio")
            #print(ds)
            ISBL_SFC = ds
            #print("1",datetime.datetime.now())
            #ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.REGIONParamDict,grib_dict.Grib2KeyDict)
            if not os.path.exists(weightpath + f"/PLEV_REGION_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_REGION_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_REGION_to_05.nc")
            #print("2",datetime.datetime.now())
            ISBL_SFC = regridder(ISBL_SFC)
            ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
            #
            UU = - np.sin(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
            VV = - np.cos(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
            ISBL_SFC["10U"]=UU
            ISBL_SFC["10V"]=VV
            #print("3",datetime.datetime.now())
            result1 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.REGIONParamDict,grib_dict.Grib2KeyDict)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

            ISBL_SFC = ds
            if not os.path.exists(weightpath + f"/PLEV_REGION_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_REGION_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_REGION_to_15.nc")
            ISBL_SFC = regridder(ISBL_SFC)
            ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
            UU = - np.sin(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
            VV = - np.cos(np.deg2rad(ISBL_SFC["D10"]))*ISBL_SFC["W10"]
            ISBL_SFC["10U"]=UU
            ISBL_SFC["10V"]=VV
            result3 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.REGIONParamDict,grib_dict.Grib2KeyDict)
            
            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            to_grib(result, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            
            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            

            

            atleast +=1

        #except BaseException as e:
        #    if isinstance(e, KeyboardInterrupt):
        #        raise
        #    else:
        #        traceback.print_exc()
    if atleast == 0 : status = 1
    return status

@typechecked
def grib_kjrh_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    finaloutpath = outputpath+f"/{fcst}/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    sstime = startTime
    for i in range(fh[0],fh[1]+1,dt):
        filel = []
        ymdhms = f"{sstime.strftime('%Y%m%d%H')}0000"
        for kk in ["CBH","CLD","D10","GPH","RH2","RHU","T2M","TD2","TEM","UWND","VWND","VIS","W10"]:
            reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d%H')}/NAFP_KDSZ_KHMA_{ymdhms}-{kk}-EAI-{i:03d}*.NC"
            fileseq = glob.glob(reg)
            for fn in fileseq:
                filel.append(fn)

        if len(filel) == 0:
            continue

        ds = xr.open_mfdataset(filel,engine="pynio")
        ISBL_SFC = ds
        if not os.path.exists(weightpath + "/PLEV_REGION_to_05.nc"):
            regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
            regridder.to_netcdf(weightpath + "/PLEV_REGION_to_05.nc")
        else:
            regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + "/PLEV_REGION_to_05.nc")
        ISBL_SFC = regridder(ISBL_SFC)
        ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
        if "D10" in ISBL_SFC and "W10" in ISBL_SFC:
            UU = - np.sin(np.deg2rad(ISBL_SFC["D10"])) * ISBL_SFC["W10"]
            VV = - np.cos(np.deg2rad(ISBL_SFC["D10"])) * ISBL_SFC["W10"]
            ISBL_SFC["10U"] = UU
            ISBL_SFC["10V"] = VV
        result1 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.KJRHParamDict,grib_dict.Grib2KeyDict)
        for v in result1:
            for attr in grib_dict.Grib2KeyDict[v].keys():
                result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

        ISBL_SFC = ds
        if not os.path.exists(weightpath + "/PLEV_REGION_to_15.nc"):
            regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
            regridder.to_netcdf(weightpath + "/PLEV_REGION_to_15.nc")
        else:
            regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + "/PLEV_REGION_to_15.nc")
        ISBL_SFC = regridder(ISBL_SFC)
        ISBL_SFC = ISBL_SFC.where(ISBL_SFC!=0.0)
        if "D10" in ISBL_SFC and "W10" in ISBL_SFC:
            UU = - np.sin(np.deg2rad(ISBL_SFC["D10"])) * ISBL_SFC["W10"]
            VV = - np.cos(np.deg2rad(ISBL_SFC["D10"])) * ISBL_SFC["W10"]
            ISBL_SFC["10U"] = UU
            ISBL_SFC["10V"] = VV
        result3 = pynio_split.dataset_to_grib(ISBL_SFC,grib_dict.KJRHParamDict,grib_dict.Grib2KeyDict)
        for v in result1:
            for attr in grib_dict.Grib2KeyDict[v].keys():
                result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

        result = result1
        result.attrs["GRIB_centre"]="rjtd"
        result.attrs["edition"]=2
        to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        to_grib(result, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        result = result3
        result.attrs["GRIB_centre"]="rjtd"
        result.attrs["edition"]=2
        to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
        atleast += 1

    if atleast == 0:
        status = 1
    return status


    
#############################################################
@typechecked
def grib_cldas_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    finaloutpath = outputpath+f"/CLDAS/sfc/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    dataset = xr.Dataset()
    sstime = startTime#+datetime.timedelta(hours=8)
    reg = f"{fcstpath}/{fcst}/{sstime.strftime('%Y%m%d')}/*HOR*{sstime.strftime('%Y%m%d%H')}.nc"
    print(reg)
    filel = glob.glob(reg)
    print("filel",filel)
    ds = xr.Dataset()
    if len(filel) == 0:
        status = 1
    else:
        try:
            lon_new = np.arange(0,360,0.25)
            lat_new = np.arange(-90,90.25,0.25)
            for ff in filel:
                if "SSR" in ff:continue
                ds1 = xr.open_dataset(ff, engine="pynio")
                try:
                    ds1 = ds1.interp(LAT = lat_new, LON= lon_new, method='linear')
                except:
                    ds1 = ds1.interp(XLAT = lat_new, XLON= lon_new, method='linear')
                ds = xr.merge([ds,ds1],compat='override')
            
            #ds = ds.interp(LAT = lat_new, LON= lon_new, method='linear')

            SFC = pynio_split.dataset_to_grib(ds,grib_dict.CLDASParamDict,grib_dict.Grib2KeyDict)

            if not os.path.exists(weightpath + f"/SURF_CLDAS_to_05.nc"):
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/SURF_CLDAS_to_05.nc")
            else:
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear", weights=weightpath + f"/SURF_CLDAS_to_05.nc")
            result1 = regridder(SFC)
            mask = (result1.latitude >= 0.5) & (result1.latitude <= 59.5) & \
                    (result1.longitude >= 70.5) & (result1.longitude <= 139.5)
            result1 = result1.where(mask)
            #result1["2r"] = result1["2r"].where(result1["2r"] > 0)
            print(result1)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

            result1.attrs["GRIB_centre"]="rjtd"
            result1.attrs["edition"]=2
            to_grib(result1, finaloutpath+f"/single{startTime.strftime('%Y%m%d%H000')}.grib")

            #to_grib(SFC, finaloutpath+f"/raw{startTime.strftime('%Y%m%d%H000')}.grib")
            status = 0
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
            status = 1
    return status
####################################################### AUTO ###################################
@typechecked
def grib_auto_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    YYYYMMDDHH=startTime.strftime('%Y%m%d%H')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    finaloutpath = outputpath + f"/AUTO/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    # 读取文件
    for i in range(fh[0],fh[1]+1,dt):
        reg = f"{fcstpath}/{fcst}/{YYYYMMDDHH}"+"/KT*.{:0>3d}".format(i)
        filel = glob.glob(reg)
        print(reg)
        #for ff in filel:
  	#    if "CB" in ff or "LC" in ff or "TF" in ff:
        #        fileOut.append(ff)
        #filel = fileOut
        if len(filel) == 0: continue # 没有文件，跳过,但是不至于返回失败。
        try:
            ds = xr.open_mfdataset(filel,engine="pynio")
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.AUTOParamDict,grib_dict.Grib2KeyDict)
            if not os.path.exists(weightpath + f"/PLEV_KT1279_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_KT1279_to_05.nc")
            result1 = regridder(ISBL_SFC)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            if not os.path.exists(weightpath + f"/PLEV_KT1279_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_KT1279_to_15.nc")
            result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
    if atleast == 0 : status = 1
    return status
########################################################VIS############################
@typechecked
def grib_visfcst_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    YYYYMMDDHH=startTime.strftime('%Y%m%d%H')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    finaloutpath = outputpath + f"/VISFCST/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    # 读取文件
    for i in range(fh[0],fh[1]+1,dt):
        reg = f"{fcstpath}/{fcst}/{YYYYMMDDHH}"+"/KVVS*999{:0>3d}.grb".format(i)
        filel = glob.glob(reg)
        if len(filel) == 0: continue # 没有文件，跳过,但是不至于返回失败。
        try:
            filename = filel[0]
            ds = xr.open_dataset(filename,engine="pynio")
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.VISFCSTParamDict,grib_dict.Grib2KeyDict)
            if not os.path.exists(weightpath + f"/PLEV_VISFCST_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_VISFCST_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_VISFCST_to_05.nc")
            result1 = regridder(ISBL_SFC)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
            mask = (result1.latitude >= 2.5) & (result1.latitude <= 55.5) & \
                (result1.longitude >= 70.5) & (result1.longitude <= 137.0)
            result1 = result1.where(mask)

            if not os.path.exists(weightpath + f"/PLEV_VISFCST_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_VISFCST_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_VISFCST_to_15.nc")
            result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
    if atleast == 0 : status = 1
    return status
    

########################################################KT1279_CLOUD############################
@typechecked
def grib_kt1279_cloud_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    YYYYMMDDHH=startTime.strftime('%Y%m%d%H')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    finaloutpath = outputpath + f"/KT1279_CLOUD/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    # 读取文件
    for i in range(fh[0],fh[1]+1,dt):
        reg = f"{fcstpath}/{fcst}/{YYYYMMDDHH}"+"/KCR1*.{:0>3d}.grb".format(i)
        filel = glob.glob(reg)
        fileOut = []
        for ff in filel:
            if "CB" in ff or "LC" in ff or "TF" in ff:
                fileOut.append(ff)
        filel = fileOut
        if len(filel) == 0: continue # 没有文件，跳过,但是不至于返回失败。
        try:
            ds = xr.open_mfdataset(filel,engine="pynio")
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.KT1279CLOUDParamDict,grib_dict.Grib2KeyDict)
            if not os.path.exists(weightpath + f"/PLEV_KT1279_CLOUD_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_CLOUD_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_KT1279_CLOUD_to_05.nc")
            result1 = regridder(ISBL_SFC)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            if not os.path.exists(weightpath + f"/PLEV_KT1279_CLOUD_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_CLOUD_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_KT1279_CLOUD_to_15.nc")
            result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
    if atleast == 0 : status = 1
    return status
####################################################### KT1279 #######################################    
@typechecked
def grib_kt1279_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    YYYYMMDDHH=startTime.strftime('%Y%m%d%H')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    finaloutpath = outputpath + f"/KT1279/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    # 读取文件
    for i in range(fh[0],fh[1]+1,dt):
        reg = f"{fcstpath}/{fcst}/{YYYYMMDDHH}"+"/KTR3*G{:s}-{:0>3d}.grb".format(YYYYMMDDHH,i)
        filel = glob.glob(reg)
        if len(filel) == 0: continue # 没有文件，跳过,但是不至于返回失败。

        try:
            ds = xr.open_mfdataset(reg,engine="pynio")
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.KT1279ParamDict,grib_dict.Grib2KeyDict)
            if not os.path.exists(weightpath + f"/PLEV_KT1279_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_KT1279_to_05.nc")
            result1 = regridder(ISBL_SFC)
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            if not os.path.exists(weightpath + f"/PLEV_KT1279_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_KT1279_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_KT1279_to_15.nc")
            result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))
            

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(i))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
    if atleast == 0 : status = 1
    return status
####################################### CMAGFS #########################################
@typechecked
def grib_cmagfs_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

     # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    reg = f"{fcstpath}/{fcst}//*/Z_NAFP_C_BABJ_*{startTime.strftime('%Y%m%d%H')}*"
    filel = glob.glob(reg)
    finaloutpath = outputpath + f"/CMA_GFS/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True) 
    if len(filel) == 0: status = 1
    for filen in filel:
        #try:
        if True:
            timestr = filen.split("/")[-1].split("-")[-1][:3]
            interval = int(timestr)
            if interval < fh[0] or interval >= fh[1]:
                continue
            print("############################",filen)
            # 读取pynio数据
            ds = xr.open_dataset(filen+".grib",engine="pynio")
 
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.CMAGFSParamDict,grib_dict.Grib2KeyDict,100 ) #
            lon_new = np.arange(0,360,0.5)
            lat_new = np.arange(-90,90.25,0.5)
            result1 = ISBL_SFC.interp(latitude = lat_new, longitude= lon_new, method='linear')
                  
            #if not os.path.exists(weightpath + f"/PLEV_CMAGFS_to_05.nc"):
            #    regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
            #    regridder.to_netcdf(weightpath + f"/PLEV_CMAGFS_to_05.nc")
            #else:
            #    regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_CMAGFS_to_05.nc")
            #result1 = regridder(ISBL_SFC)
            #print(result1)
            
            lon_new = np.arange(0,360,1.5)
            lat_new = np.arange(90,-90.25,-1.5)
            result3 = ISBL_SFC.interp(latitude = lat_new, longitude= lon_new, method='linear')
            #if not os.path.exists(weightpath + f"/PLEV_CMAGFS_to_15.nc"):
            #    regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
            #    regridder.to_netcdf(weightpath + f"/PLEV_CMAGFS_to_15.nc")
            #else:
            #    regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_CMAGFS_to_15.nc")
            #result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]


            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))


            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            atleast +=1

        #except BaseException as e:
        #    if isinstance(e, KeyboardInterrupt):
        #        raise
        #    else:
        #        print(e)
    if atleast == 0 : status = 1
    return status
    status = 1
    return status
######################################## ERA5   ########################################
@typechecked
def grib_era5_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)
    
     # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )


    # ground
    reg = f"{fcstpath}/{fcst}/sfc/{YYYYMMDD}/ERA5_*{startTime.strftime('%Y%m%d%H')}*"
    filel = glob.glob(reg)
    print("filel",filel)
    finaloutpath = outputpath + f"/ERA5/sfc/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    for filen in filel:
        if True:#try:
            ds = xr.open_dataset(filen+".grib",engine="pynio")
            SFC = pynio_split.dataset_to_grib(ds,grib_dict.ERA5SFCParamDict,grib_dict.Grib2KeyDict)

            if not os.path.exists(weightpath + f"/PLEV_ERA5_to_05.nc"):
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_ERA5_to_05.nc")
            else:
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_ERA5_to_05.nc")
            result1 = regridder(SFC)
            for v in result1:
               for attr in grib_dict.Grib2KeyDict[v].keys():
                   result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
   
            if not os.path.exists(weightpath + f"/SFC_PLEV_ERA5_to_15.nc"):
                regridder = xe.Regridder(SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/SFC_PLEV_ERA5_to_15.nc")
            else:
                regridder = xe.Regridder(SFC, ds_out_15, "bilinear", weights=weightpath + f"/SFC_PLEV_ERA5_to_15.nc")
            result3 = regridder(SFC)
            for v in result3:
               for attr in grib_dict.Grib2KeyDict[v].keys():
                   result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/single{startTime.strftime('%Y%m%d%H')}"+"000.grib")
        #except:
        #    status = 1

    reg = f"{fcstpath}/{fcst}/plev/{YYYYMMDD}/ERA5_*{startTime.strftime('%Y%m%d%H')}*"
    filel = glob.glob(reg)
    print(filel)

    finaloutpath = outputpath + f"/ERA5/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    for filen in filel:
          
        if True:

            ds = xr.open_dataset(filen+".grib",engine="pynio")
            ISBL = pynio_split.dataset_to_grib(ds,grib_dict.ERA5ISBLParamDict,grib_dict.Grib2KeyDict)
            if (len(ISBL)>0):
        #    SFC = pynio_split.dataset_to_grib(ds,grib_dict.ERA5SFCParamDict,grib_dict.Grib2KeyDict)
                if not os.path.exists(weightpath + f"/ISBL_PLEV_ERA5_to_15.nc"):
                    regridder = xe.Regridder(ISBL, ds_out_15, "bilinear")
                    regridder.to_netcdf(weightpath + f"/ISBL_PLEV_ERA5_to_15.nc")
                else:
                    regridder = xe.Regridder(ISBL, ds_out_15, "bilinear", weights=weightpath + f"/ISBL_PLEV_ERA5_to_15.nc")
                result1 = regridder(ISBL)
        #    result3 = regridder(SFC)
                for v in result1:
                    for attr in grib_dict.Grib2KeyDict[v].keys():
                        result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
            
            
            result =xr.merge([result1,result3])
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"000.grib")
        #except:
        #   status = 1

    return status

######################################## NCEP   ########################################
@typechecked
def grib_ncep_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    YYYYMMDD=startTime.strftime('%Y%m%d')
    HH=startTime.strftime('%H')

    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)
    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    # 读取文件
    # 文件名格式：W_NAFP_C_KWBC_20250501193010_P_gfs.t12z.pgrb2.0p50.f240.bin
    reg = f"{fcstpath}/{fcst}/{YYYYMMDD}/W_NAFP_C_KWBC_*_P_gfs.t{HH}z.*.f*.bin"
    filel = glob.glob(reg)

    finaloutpath = outputpath + f"/NCEP/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    if len(filel) == 0: status = 1
    for filen in filel:
        try:
            timestr = filen.split("/")[-1].split(".")[-2][1:]
            interval = int(timestr)
            if interval < fh[0] or interval >= fh[1]:
                continue
            print("############################",filen)
            # 读取pynio数据
            ds = xr.open_dataset(filen+".grib",engine="pynio")
 
            ISBL_SFC = pynio_split.dataset_to_grib(ds,grib_dict.NCEPParamDict,grib_dict.Grib2KeyDict,100 ) # NCEP 气压单位为Pa，转化为hPa
                
            if not os.path.exists(weightpath + f"/PLEV_NCEP_to_05.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_NCEP_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_NCEP_to_05.nc")
            result1 = regridder(ISBL_SFC)
            

            if not os.path.exists(weightpath + f"/PLEV_NCEP_to_15.nc"):
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_NCEP_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL_SFC, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_NCEP_to_15.nc")
            result3 = regridder(ISBL_SFC)

            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

        

            result = result1
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))


            result = result3
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            to_grib(ISBL_SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
    if atleast == 0 : status = 1
    return status
######################################## emend   ######################################
@typechecked
def grib_emend_all(startTime:datetime.datetime, fcst:str,para:list,fh:list, dt:int):
    status = 0
    print("XXXXXXXXXXXXXXX EMEND GRIB XXXXXXXXXXXXXXXXXXXXXXXXXXX")
    status = emend.emend_decode(startTime,fcst,fh,dt)

    return 1 if status else 0


######################################## CLIMATE ######################################
@typechecked
def grib_climate_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status = 0
    atleast = 0
    
    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)
    
    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )

    reg = f"{fcstpath}/{fcst}/{startTime.strftime('%Y-%m-%d')}/F1.4-{startTime.strftime('%Y%m%d')}.famil.daily-ensmean.nc"
    filel = glob.glob(reg)
    
    finaloutpath = outputpath + f"/CLIMATE/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)
    
    if len(filel) == 0: status = 1
    print(reg)
    for filen in filel:
   #     try:
        if True:
            ds = xr.open_dataset(filen,engine="pynio")
            baseT = ds.time.values[0]
            timebaseT = datetime.datetime(year=baseT.year,month=baseT.month,day=baseT.day,hour=baseT.hour)
            for t in ds.time.values:
                #print(type(t))
                subdata = ds.sel(time=t)
                timeobj = datetime.datetime(year=t.year,month=t.month,day=t.day,hour=t.hour)
                #print(timeobj)
                result1 = pynio_split.dataset_to_grib(subdata,grib_dict.CLIMATEParamDict,grib_dict.Grib2KeyDict)
                for v in result1:
                    for attr in grib_dict.Grib2KeyDict[v].keys():
                        result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                result = result1
                result.attrs["GRIB_centre"]="rjtd"
                result.attrs["edition"]=2
                tmpTime =  (timeobj-timebaseT)
                interval = int(tmpTime.total_seconds() // 3600)
                print(interval)
                to_grib(result, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))
 
   #     except:
   #         status = 1
   #         pass

            
    return status

######################################## ECMWF ########################################
@typechecked
def grib_ecmwf_all(startTime:datetime.datetime, fcst:str, para:list, fh:list, dt:int)->int:
    status=0
    atleast = 0


    fcstpath,outputpath,toolspath,weightpath = config_path(fcst)

    # 0.5度格点
    ds_out_05 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
        }
    )
    # 1.5度格点
    # 注意注意，这里纬度是反的，是90到-90的
    ds_out_15 = xr.Dataset(
        {
            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
        }
    )
    # 读取文件
    reg = f"{fcstpath}/{fcst}/{startTime.strftime('%Y%m%d%H')}/W_NAFP_C_ECMF*{startTime.strftime('%Y%m%d*001')}"
    filel = glob.glob(reg)

    finaloutpath = outputpath + f"/ECMWF/normal/{startTime.strftime('%Y%m%d')}/"
    if not os.path.exists(finaloutpath):
        os.makedirs(finaloutpath,exist_ok = True)

    if len(filel) == 0: status = 1
    print(reg)
    for filen in filel:
        try:
            timestr = filen.split("/")[-1].split("_")
            fcsttime = datetime.datetime.strptime(timestr[4][:4]+timestr[-1][-9:-1],"%Y%m%d%H%M")
            timedelta = fcsttime-startTime
            interval = int(timedelta.total_seconds()/3600)
            # skip all interval not in fh
            if interval < fh[0] or interval >= fh[1]:
                continue

            print("############################",filen)
            # 读取pynio数据
            ds = xr.open_dataset(filen+".grib",engine="pynio")
            ISBL = pynio_split.dataset_to_grib(ds,grib_dict.ECMWFISBLParamDict,grib_dict.Grib2KeyDict)
            SFC  = pynio_split.dataset_to_grib(ds,grib_dict.ECMWFSFCParamDict, grib_dict.Grib2KeyDict)

            if not os.path.exists(weightpath + f"/PLEV_ECMWF_to_05.nc"):
                regridder = xe.Regridder(ISBL, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_ECMWF_to_05.nc")
            else:
                regridder = xe.Regridder(ISBL, ds_out_05, "bilinear", weights=weightpath + f"/PLEV_ECMWF_to_05.nc")
            result1 = regridder(ISBL,skipna=True)
            

            if not os.path.exists(weightpath + f"/PLEV_ECMWF_to_15.nc"):
                regridder = xe.Regridder(ISBL, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/PLEV_ECMWF_to_15.nc")
            else:
                regridder = xe.Regridder(ISBL, ds_out_15, "bilinear", weights=weightpath + f"/PLEV_ECMWF_to_15.nc")
            result3 = regridder(ISBL,skipna=True)
            # copy grib attrs
            for v in result1:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result1[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result3[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

            if not os.path.exists(weightpath + f"/SURF_ECMWF_to_05.nc"):
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear")
                regridder.to_netcdf(weightpath + f"/SURF_ECMWF_to_05.nc")
            else:
                regridder = xe.Regridder(SFC, ds_out_05, "bilinear", weights=weightpath + f"/SURF_ECMWF_to_05.nc")
            result2 = regridder(SFC,skipna=True)

            if not os.path.exists(weightpath + f"/SURF_ECMWF_to_15.nc"):
                regridder = xe.Regridder(SFC, ds_out_15, "bilinear")
                regridder.to_netcdf(weightpath + f"/SURF_ECMWF_to_15.nc")
            else:
                regridder = xe.Regridder(SFC, ds_out_15, "bilinear", weights=weightpath + f"/SURF_ECMWF_to_15.nc")
            result4 = regridder(SFC,skipna=True)


            for v in result2:
                for attr in grib_dict.Grib2KeyDict[v].keys():
                    result2[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]
                    result4[v].attrs[attr] = grib_dict.Grib2KeyDict[v][attr]

            mask = (result1.r.latitude>= -9.5) & (result1.r.latitude <= 59.5) & \
                   (result1.r.longitude >= 60.5) & (result1.r.longitude <= 149.5)
            result1 = result1.where(mask)

            mask = (result3.r.latitude>= -9.5) & (result3.r.latitude <= 59.5) & \
                   (result3.r.longitude >= 60.5) & (result3.r.longitude <= 149.5)
            result3 = result3.where(mask)



            result = xr.merge([result1,result2])
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2

            #result.to_netcdf(finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/fcst{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            result = xr.merge([result3,result4])
            result.attrs["GRIB_centre"]="rjtd"
            result.attrs["edition"]=2
            
            #result.to_netcdf(finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval),engine="netcdf4")
            to_grib(result, finaloutpath + f"/prs{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            to_grib(SFC, finaloutpath + f"/raw{startTime.strftime('%Y%m%d%H')}"+"{:0>3d}.grib".format(interval))

            atleast +=1

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            else:
                print(e)
                status = 1
    if atleast == 0 : status = 1
    return status


def gridder(paload:package):
    startTime = paload.startTime
    fcst = paload.fcst
    para = paload.para
    fh = paload.fh
    dt = paload.dt
    if fcst == "KT1279":
        grib_kt1279(startTime,fcst,para,fh,dt)
        grib_kt1279_prs(startTime,fcst,para,fh,dt)
    if fcst == "ERA5":
        grib_era5(startTime,fcst,para,fh,dt)
        grib_era5_prs(startTime,fcst,para,fh,dt)
    if fcst == "NCEP":
        grib_ncep(startTime,fcst,para,fh,dt)
        grib_ncep_prs(startTime,fcst,para,fh,dt)
    
	# TODO combine 2 process file
	
    time.sleep(1)
    print("asdfasdf")


if __name__ == "__main__":
    worker = []
    dtime = datetime.datetime.strptime("2025050100","%Y%m%d%H")
    status,mess = point_ncep(dtime, "NCEP",["2t","2r","10u","10v","rain1"],[0,240],1)
    print(status,mess)


    #for i in range(31):
    #    worker.append(package(dtime,"KT1279",["u","v","gh"],[0,240],3))
    #    dtime = dtime+dt.timedelta(hours=24)
    #with Pool(2) as p:
    #    p.map(gridder,worker)
    #    #grib_ncep(dtime,fcst,para,fh,dtt)
    #    #dtime = dtime+dt.timedelta(hours=6)
#    print(worker)
