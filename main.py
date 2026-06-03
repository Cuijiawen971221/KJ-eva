# 20250814 fix grid ground area verify, Author: CGC


import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
import datetime as dt
from yunyao_met import *
import config as CONF
from grid_proc import *
import multiprocessing
import uniform_decoder
from rain_fss_ts_function import *
import mh_decoder
import jd_decoder
from mode_function import *
import numpy as np
from clickhouse_util import clickclient
import met_clickhouse_util
import wind_grib
#import met_weather
from py2java import *


class Plev(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "2025010100") # 开始时间
    timedelta: str = Field(descrption = "12")# time step
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    para: str = Field(descrption="u,v,t,r,q,gh,wind,wdir") # 变量，以，分割
    ref : str = Field(descrption="ERA5/SELF/BUFR")  # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    length: str = Field(descrption="21, 21*12=240")#  
     
class Model(BaseModel): # 
    startTime : str =Field(descrption="2025010100")
    para: str =Field(descrption="u,v,gh,r,wind,wdir")
    fstc: str=Field(descrption="KT1279/NCEP/EC/CMAGFS")
    
class synoModel(BaseModel): # 
    startTime : str =Field(descrption="2025010100")
    para: str =Field(descrption="u,v,gh,r,wind,wdir")
    fstc: str=Field(descrption="KT1279/NCEP/EC/CMAGFS")
    level: str=Field(descrption="50000,50000")
    fh: str=Field(descrption="0,240")

class Scan(BaseModel): # 
    startTime: str=Field(descrption="2025010100")
    fcst: str=Field(descrption="KT1279/NCEP/EC/CMAGFS")

class Obs(BaseModel):
    startTime: str=Field(descrption="2025010100")

class ObsAir(BaseModel):
    startTime: str=Field(descrption="20250101")
    
class rain_grid_FSS(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "20250101")        # 开始时间
    endTime: str = Field(descrption = "20250103")          # 开始时间
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    level: str = Field(descrption="3,6,12,24")             # 3h累计降水，6h累计降水，...（单选）
    ref : str = Field(descrption="ERA5/CMPAS/CLDAS")       # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    length: str = Field(descrption="10")                  # 评估时间长度
    cycl: str = Field(descrption="00,06,12,18")            # 起报时间（先设置单选）
    half_size: str = Field(descrption="1,2,3,4,5")

class rain_grid_MODE(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "20250101")        # 开始时间
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    level: str = Field(descrption="3,6,12,24")             # 3h累计降水，6h累计降水，...（单选）
    ref : str = Field(descrption="ERA5/CMPAS/CLDAS")       # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    cycl: str = Field(descrption="00,06,12,18")            # 起报时间（先设置单选）
    h_delta: str = Field(descrption="6,12,18")             # 预报时效（自行选择，6,12,18....）
    smooth: str = Field(descrption="1/2/3/4/5")            # 平滑系数
    threshold: str= Field(descrption="1/2/3/4/5")          # 阈值
    minsize: str = Field(descrption="1/2/3/4/5")           # 最小面积

class Wind_plot(BaseModel):
    startTime: str = Field(descrption = "2025010100") # 开始时间
    timedelta: str = Field(descrption = "12")# time step
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    level_value: str | None = Field(default=None, description="500/700/850")


app = FastAPI()

@app.post("/get_surface_wind_data")
async def get_surface_wind_data(wind_plot:Wind_plot):
    status = True
    mess = ""
    stime = dt.datetime.strptime(wind_plot.startTime,"%Y%m%d%H")
    status,mess, data = wind_grib.read_wind_from_grib(wind_plot.fstc, stime, int(wind_plot.timedelta), "surface", 10, None)
    return {
        "method": 'post',
        "status": status,
        "mess": mess,
        "data": data
    }

@app.post("/get_upper_wind_data")
async def get_upper_wind_data(wind_plot:Wind_plot):
    status = True
    mess = ""
    stime = dt.datetime.strptime(wind_plot.startTime,"%Y%m%d%H")
    status,mess, data = wind_grib.read_wind_from_grib(wind_plot.fstc, stime, int(wind_plot.timedelta), "pressure", int(wind_plot.level_value), None)
    return {
        "method": 'post',
        "status": status,
        "mess": mess,
        "data": data
    }
    
@app.post("/save_upper_real_data_to_file")
async def save_upper_real_data_to_file(obs:Obs):
    status = True
    mess = ""
    stime = dt.datetime.strptime(obs.startTime,"%Y%m%d%H")
    status,mess = met_clickhouse_util.save_upper_real_data_to_file(stime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

@app.post("/save_upper_real_data_to_file")
async def save_upper_real_data_to_file(obs:Obs):
    status = True
    mess = ""
    stime = dt.datetime.strptime(obs.startTime,"%Y%m%d%H")
    status,mess = met_clickhouse_util.save_upper_real_data_to_file(stime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    } 

@app.post("/save_surface_real_data_to_file")
async def save_surface_real_data_to_file(obs:Obs):
    status = True
    mess = ""
    stime = dt.datetime.strptime(obs.startTime,"%Y%m%d%H")
    status,mess = met_clickhouse_util.save_surface_real_data_to_file(stime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }   

##站点信息保存到文件
@app.post("/save_station")
async def save_station():
    status = True
    mess = ""
    status,mess = met_clickhouse_util.save_station_to_file()
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    } 

##站点信息保存到文件
@app.post("/save_area")
async def save_area():
    status = True
    mess = ""
    status,mess = met_clickhouse_util.save_area_to_file()
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

### 保存插值或检验数据到数据库
@app.post("/save_data_to_ck")
async def save_data_to_ck():
    status = True
    mess = ""
    status,mess = met_clickhouse_util.save_data_to_ck()
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }  
  

@app.post("/grid_rain_eva")
## 格点降水检验--->FSS
async def grid_rain_eva(rain:rain_grid_FSS):
    stime  = rain.startTime     #dt.datetime.strptime(rain.startTime,"%Y%m%d")
    etime  = rain.endTime     #dt.datetime.strptime(rain.endTime,"%Y%m%d")
    area   = rain.area.split(",")
    level  = int(rain.level)
    ref    = rain.ref
    fstc   = rain.fstc
    length = int(rain.length)     ##
    cycl   = rain.cycl            ## str
    half_size = rain.half_size
    status,mess,fss_result = run_main_fss_(level,fstc,cycl,stime,etime,length,ref,area,half_size)
    return{
        "method":'post',
        "status":status,
        "mess":mess,
        "result":fss_result
    }

## 格点降水检验--->FSS(结果汇总)
@app.post("/grid_rain_eva_all")
async def grid_rain_eva_all(rain:rain_grid_FSS):
    stime  = rain.startTime     #dt.datetime.strptime(rain.startTime,"%Y%m%d")
    etime  = rain.endTime     #dt.datetime.strptime(rain.endTime,"%Y%m%d")
    area   = rain.area.split(",")
    level  = int(rain.level)
    ref    = rain.ref
    fstc   = rain.fstc
    length = int(rain.length)     ##
    cycl   = rain.cycl            ## str
    half_size = rain.half_size
    status,mess,fss_result = run_main_fss_all(level,fstc,cycl,stime,etime,length,ref,area,half_size)
    return{
        "method":'post',
        "status":status,
        "mess":mess,
        "result":fss_result
    }

##  降水空间检验MODE算法
@app.post("/grid_rain_mode")
async def grid_rain_mode(rain:rain_grid_MODE):
    """
    stratTime = '20250510'
    area      = '6'
    level     = '6'                   
    ref       = 'ERA5'                     
    fstc      = 'NCEP'                     
    cycl      = '00'                     
    h_delta   = '6'                  
    smooth    = '5'              
    threshold = '5'         
    minsize   = '5'            
    """
    stime     = rain.startTime
    area      = rain.area.split(",")          #: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")  # 区域，以，分割
    level     = rain.level                    #: str = Field(descrption="3,6,12,24")  # 3h累计降水，6h累计降水，...（单选）
    ref       = rain.ref                      #: str = Field(descrption="ERA5/CMPAS/CLDAS")  # 真值，单选
    fstc      = rain.fstc                     #: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    cycl      = rain.cycl                     #: str = Field(descrption="00,06,12,18")  # 起报时间（先设置单选）
    h_delta   = rain.h_delta                  #: str = Field(descrption="6,12,18")  # 预报时效（自行选择，6,12,18....）
    smooth    = int(rain.smooth)              #: str = Field(descrption="1/2/3/4/5")  # 平滑系数
    threshold = float(rain.threshold)           #: str = Field(descrption="1/2/3/4/5")  # 阈值
    minsize   = int(rain.minsize)            #: str = Field(descrption="1/2/3/4/5")  # 最小面积
    status,mess,mode_result = run_main_mode_(stime, cycl, fstc, ref, level, h_delta, area, smooth, threshold, minsize)
    
    return {
        "method": 'post',
        "status": status,
        "mess": mess,
        "result": mode_result
    }



@app.post("/gts_decoder")
async def gts_to_database(obs:Obs):
    status = True
    mess = ""
    stime = dt.datetime.strptime(obs.startTime,"%Y%m%d%H")
    try:
        status,mess = uniform_decoder.decoder_main(stime)
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            raise
        else:
            status = 1
            mess = str(e)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }   


@app.post("/mh_decoder")
async def mh_to_database(obs:ObsAir):
    status = True
    mess = ""
    #stime = dt.datetime.strptime(obs.startTime,"%Y%m%d")
    status,mess = mh_decoder.decoder_main(obs.startTime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }   

@app.post("/jd_decoder")
async def jd_to_database(obs:ObsAir):
    status = True
    mess = ""
    #stime = dt.datetime.strptime(obs.startTime,"%Y%m%d")
    status,mess = jd_decoder.decoder_main(obs.startTime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }  

#预报数据齐套性检验
@app.post("/scan_orig_fcst")
async def scan_orig_fcst(scan:Scan):
    status = False
    mess = ""
    stime = dt.datetime.strptime(scan.startTime,"%Y%m%d%H")
    try:
        if stime.hour in [00,12]:
            fcst = scan.fcst
            status = yunyao_check_fcst_orig(stime,fcst)
            if not status:
                mess="failed from process"
            else:
                mess="succeed"
        else:
            status = False 
            mess = "only 00 12 be accepted"
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            raise
        else:
            status = 1
            mess = str(e)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

@app.post("/airport_model_single")
async def airport_interp_single(model:Model):
    status = False
    mess = ""
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fstc = model.fstc
    
    sql = """
                SELECT station_id, station_code, longitude, latitude FROM station_info WHERE is_estimate=1 
     """
    station = clickclient.query_df(sql)
    station_longitude = np.array(station["longitude"],dtype = np.float64)
    station_longitude[np.where(station_longitude<0)] = 360 + station_longitude[np.where(station_longitude<0)]
    station_latitude = np.array(station["latitude"],dtype = np.float64)
    station_id = np.array(station["station_id"])
    AREA={
         "KT1279": [0,360,-90,90],
         "NCEP":[0,360,-90,90],
         "ECMWF":[0,360,-90,90],
         "KT1279_CLOUD":[0,360,-90,90],
         "VISFCST": [70.5,137,2.5,55],
         "AUTO":[0,360,-90,90],
         "CLIMATE":[0,360,-90,90],
         "CMA_GFS":[0,360,-90,90],
         "EMEND":[0,360,-90,90],
         "REGION":[0,360,-90,90],
         "KJRH":[0,360,-90,90],
    }
    filter_lat=[]
    filter_lon=[]
    filter_id =[]
    for i in range(len(station_longitude)):
        if station_longitude[i]>=AREA[fstc][0] and station_longitude[i]<=AREA[fstc][1] and station_latitude[i]>=AREA[fstc][2] and station_latitude[i]<=AREA[fstc][3]:
            filter_lat.append(station_latitude[i])
            filter_lon.append(station_longitude[i])
            filter_id.append(station_id[i])
    
    statFromDB = xr.Dataset({\
            "longitude": filter_lon,
            "latitude":filter_lat,
            "station_id": filter_id,\
                    })

    #with open("./station_info.pkl","rb") as f:
    #w   statFromDB = pickle.load(f)
    
#    print(statFromDB)
    JOB = CONF.JOB
    # JOB={"KT1279": np.concatenate((np.arange(0,99,1),np.arange(99,120,3),np.arange(120,241,6))),
    # #JOB={"KT1279": np.arange(0,100,1),
    #      "NCEP": np.arange(0,241,3),
    #      "ECMWF": np.concatenate((np.arange(0,78,3),np.arange(78,246,6))),
    #      "KT1279_CLOUD": np.arange(0,72,1),
    #      "VISFCST": np.arange(0,48,1),
    #      "AUTO": np.arange(0,241,3),
    #      "CLIMATE": np.arange(0,24*61,24),
    #      "CMA_GFS":np.arange(0,241,3),
    #      "EMEND":np.arange(1,73,1),
    #      "REGION":np.arange(0,73,1),
    #     }
           
    if True:
        
        todolist = np.array_split(JOB[fstc],16)
        jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max())],1,"",statFromDB) for tdl in todolist]
        #print("jobs:",jobs)
        messout = []
        with multiprocessing.Pool(processes=16) as pool:
            sta = pool.starmap(airport_allInone,jobs)
        for sa in sta:
            messout.append(sa[1])
            if sa[0] :
                status = sa[0]
                t1 = datetime.datetime.now()
                batch_size = 20000
                for i in range(0, len(sa[2]), batch_size):
                    batch = sa[2].iloc[i:i + batch_size]
                    clickclient.insert_df("airport_forecast_data", batch)
                print(datetime.datetime.now() - t1)
                #save to filesystem

        #tats,mess,sa = airport_allInone(stime,fstc,para,[0,240],1,"",statFromDB)
        #1 = datetime.datetime.now()
        
        #batch_size = 10000
        #for i in range(0, len(sa), batch_size):
        #    batch = sa.iloc[i:i + batch_size]
        #    clickclient.insert_df("airport_forecast_data", batch)
        #print(datetime.datetime.now() - t1)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }


# 机场站点插值
@app.post("/airport_model")
async def airport_interp(model:Model):
    status = False
    mess = ""
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fstc = model.fstc
    
    sql = """
                SELECT station_id, station_code, longitude, latitude FROM station_info 
     """
    station = clickclient.query_df(sql)
    station_longitude = np.array(station["longitude"],dtype = np.float64)
    station_longitude[np.where(station_longitude<0)] = 360 + station_longitude[np.where(station_longitude<0)]
    station_latitude = np.array(station["latitude"],dtype = np.float64)
    statFromDB = xr.Dataset({\
            "longitude": station_longitude,
            "latitude":station_latitude,
            "station_id": np.array(station["station_id"])\
                    })
    print(statFromDB)
    if True:#try:
        if fstc =="KT1279":
            todolist = np.array_split(np.arange(0,241,3),8)
            jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max())+1],3,"",statFromDB) for tdl in todolist]
            messout= []
            with multiprocessing.Pool(processes=8) as pool:
                sta = pool.starmap(airport_kt1279,jobs)
            for sa in sta:
                messout.append(sa[1])
                if sa[0] :
                    status = sa[0]
                    t1 = datetime.datetime.now()
                    batch_size = 10000
                    for i in range(0, len(sa[2]), batch_size):
                        batch = sa[2].iloc[i:i + batch_size]
                        clickclient.insert_df("airport_forecast_data", batch)
                    print(datetime.datetime.now() - t1)
            #status,mess = airport_kt1279(stime, fstc, para, [0,99], 1)
        elif fstc == "NCEP":
            todolist = np.array_split(np.arange(0,241,3),8)
            print(todolist)
            jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max())+1],3,"",statFromDB) for tdl in todolist]
            messout= []
            with multiprocessing.Pool(processes=8) as pool:
                sta = pool.starmap(airport_ncep,jobs)
            for sa in sta:
                messout.append(sa[1])
                if sa[0] :
                    status = sa[0]
                    t1 = datetime.datetime.now()
                    batch_size = 100
                    for i in range(0, len(sa[2]), batch_size):
                        batch = sa[2].iloc[i:i + batch_size]
                        clickclient.insert_df("airport_forecast_data", batch)
                    print(datetime.datetime.now() - t1)
#
            #mess = ",".join(np.unique(messout))
            #status,mess = airport_ncep(stime, fstc, para, [0,240],  3)
        elif fstc == "ECMWF":
            todolist = np.array_split(np.arange(0,241,3),8)
            jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max()+1)],3,"",statFromDB) for tdl in todolist]
            messout= []
            with multiprocessing.Pool(processes=8) as pool:
                sta = pool.starmap(airport_ecmwf,jobs)
            for sa in sta:
                messout.append(sa[1])
                if sa[0] :
                    status = sa[0]
                    t1 = datetime.datetime.now()
                    batch_size = 100
                    for i in range(0, len(sa[2]), batch_size):
                        batch = sa[2].iloc[i:i + batch_size]
                        clickclient.insert_df("airport_forecast_data", batch)
                    print(datetime.datetime.now() - t1)
        elif fstc == "AUTO":
            todolist = np.array_split(np.arange(0,241,3),8)
            jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max())],3,"",statFromDB ) for tdl in todolist]
            messout= []
            with multiprocessing.Pool(processes=8) as pool:
                sta = pool.starmap(airport_auto,jobs)
            for sa in sta:
                messout.append(sa[1])
                if sa[0] :
                    status = sa[0]
                    t1 = datetime.datetime.now()
                    batch_size = 100
                    for i in range(0, len(sa[2]), batch_size):
                        batch = sa[2].iloc[i:i + batch_size]
                        clickclient.insert_df("airport_forecast_data", batch)
                    print(datetime.datetime.now() - t1)
        elif fstc == "KT1279_CLOUD":    
            todolist = np.array_split(np.arange(0,73,1),4)
            jobs = [(stime, fstc, para, [int(tdl.min()),int(tdl.max())],3) for tdl in todolist]
            messout= []
            with multiprocessing.Pool(processes=4) as pool:
                sta = pool.starmap(airport_kt1279_cloud,jobs)
            for sa in sta:
                messout.append(sa[1])
                if sa[0] :
                    status = sa[0]
                    t1 = datetime.datetime.now()
                    batch_size = 100
                    for i in range(0, len(sa[2]), batch_size):
                        batch = sa[2].iloc[i:i + batch_size]
                        clickclient.insert_df("airport_forecast_data", batch)
                    print(datetime.datetime.now() - t1)
            #status,mess = airport_kt1279(stime, fstc, para, [0,99], 1)
    #except Exception as e:
    #    if isinstance(e, KeyboardInterrupt):
    #        raise
    #    else:
    #        status = 1
    #        mess = str(e)
       
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

# 站点插值
@app.post("/point_model")
async def aws_interp(model:Model):
    status = False
    mess = ""
    stime = dt.datetime.strptine(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fstc = model.fstc
    try:
        if fstc =="KT1279":
            status,mess = point_kt1279(stime, fstc, para, [0,99], 1)
        elif fstc == "NCEP":
            status,mess = point_ncep(stime, fstc, para, [0,240],  3)
        elif fstc == "EC":
            pass
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            raise
        else:
            status = 1
            mess = str(e)
       
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

# 地面检验并行版本
@app.post("/dm_single_parallel")
async def dimian_single_parallel(plev:Plev):
    try:
        stime = dt.datetime.strptime(plev.startTime,"%Y%m%d%H")
        area = plev.area.split(",")
        para = plev.para.split(",")
        ref = plev.ref
        fstc = plev.fstc
        length=int(plev.length)
        timedelta = int(plev.timedelta)
        JOB = CONF.JOB
        TODOLIST = np.arange(0,240+1,timedelta)
        JOB = np.sort(list(set(JOB[fstc])& set(TODOLIST)))

        domain = getregion(area)


        messout = []
        dbout = []
        if ref == "AWS":
            n_proc = 4
            ###### read obs ###########################
            ###### read from clickhouse ###############
            ppp = ",".join([pyweb2java(var) for var in para])
            print(ppp)
            obsdate = stime
            sql = f"""
                    SELECT {ppp}, station_code, longitude, latitude, message_type FROM surface_observation_data 
                    WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
            """
            obs = clickclient.query_df(sql)
            print(obs)
            todolist = np.array_split(JOB,n_proc)
            jobs = []
            for ii in range(n_proc):
                tdl = todolist[ii]
                jobs.append((stime, stime, fstc, ref, area, para, [int(tdl.min()),int(tdl.max())],timedelta,domain,obs,ii))
#            yunyao_point_area_parallel(stime, stime, fstc, ref, area, para, [int(tdl.min()),int(tdl.max())],timedelta,domain,obs,ii)
            with multiprocessing.Pool(processes=n_proc) as pool:
                sta = pool.starmap(yunyao_point_area_parallel,jobs)
                print(sta) 
        elif ref == "GTS":
            n_proc = 4
            ###### read obs ###########################
            ###### read from clickhouse ###############
            ppp = ",".join([pyweb2java(var) for var in para])
            print(ppp)
            obsdate = stime
            sql = f"""
                    SELECT {ppp}, station_code, longitude, latitude, message_type FROM surface_observation_data 
                    WHERE observation_time ='{obsdate.strftime('%Y-%m-%d %H:%M:%S')}'
            """ 
            obs = clickclient.query_df(sql)
            print(obs)
            todolist = np.array_split(JOB,n_proc) 
            jobs = []
            for ii in range(n_proc):
                tdl = todolist[ii]
                jobs.append((stime, stime, fstc, ref, area, para, [int(tdl.min()),int(tdl.max())],timedelta,domain,obs,ii))
            with multiprocessing.Pool(processes=n_proc) as pool:
                sta = pool.starmap(yunyao_point_area_parallel,jobs)
        elif ref == "CLDAS":
            n_proc=4
            todolist = np.array_split(JOB,n_proc)
            jobs = [(stime, stime, fstc, ref, area, para, [int(tdl.min()),int(tdl.max())],timedelta,domain) for tdl in todolist]
            with multiprocessing.Pool(processes=n_proc) as pool:
                sta = pool.starmap(yunyao_surf_pre_parallel,jobs)
        elif ref == "ERA5":
            n_proc=4
            todolist = np.array_split(JOB,n_proc)
            jobs = [(stime, stime, fstc, ref, area, para, [int(tdl.min()),int(tdl.max())],timedelta,domain) for tdl in todolist]
            with multiprocessing.Pool(processes=n_proc) as pool:
                sta = pool.starmap(yunyao_surf_pre_parallel,jobs)
                
        for sa in sta:
            messout.append(sa[1])
            if sa[0] :
                status = sa[0]
                dbout.append(sa[2])
        result = pd.concat(dbout).reset_index(drop=True)
        print(result.to_string())
        #clickclient.insert_df("airport_forecast_data", dbout)
        clickclient.insert_df("surface_area_verification_result", result)

        mess = "".join(messout)
    except:
        status = False
        mess = "dimian_single_parallel error"
   
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

# 地面检验
@app.post("/dm_single")
async def dimian_single(plev:Plev):
    stime = dt.datetime.strptime(plev.startTime,"%Y%m%d%H")
    area = plev.area.split(",")
    para = plev.para.split(",")
    ref = plev.ref
    fstc = plev.fstc
    length=int(plev.length)
    timedelta = int(plev.timedelta)
    #try:
    if True:
        if ref == "AWS":
            status,mess = yunyao_point_area(stime,stime,fstc,ref,area,para,timedelta,length)
        elif ref == "GTS":
            status,mess = yunyao_point_area(stime,stime,fstc,ref,area,para,timedelta,length)
        elif ref == "CLDAS":
            status,mess = yunyao_surf_pre(stime,stime,fstc,ref,area,para,timedelta,length)
        elif ref == "ERA5":
            status,mess = yunyao_surf_pre(stime,stime,fstc,ref,area,para,timedelta,length)
    #except Exception as e:
    #    if isinstance(e, KeyboardInterrupt):
    #        raise
    #    else:
    #        status = False
    #        mess =str(e)
    #            # 获取堆栈追踪对象
    #        tb = e.__traceback__
    #       # 获取错误发生的文件名
    #       filename = tb.tb_frame.f_code.co_filename
    #        # 获取错误发生的函数名
    #        funcname = tb.tb_frame.f_code.co_name
    #        # 获取错误发生的行号
    #        lineno = tb.tb_lineno
    #        # 获取错误类型和错误信息
    #        error_type = type(e).__name__
    #        error_msg = str(e)
    #        print(f"错误类型: {error_type}")
    #        print(f"错误信息: {error_msg}")
    #        print(f"文件: {filename}")
    #        print(f"函数: {funcname}")
    #        print(f"行号: {lineno}")

    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

# 格点插值检验
@app.post("/grid_model")
async def quyu_grid(model:Model):
    status = 1
    mess = ""
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fcst = model.fstc
    print(stime,para,fcst)
    if fcst == "KT1279":
        fh=[0,99]
        dtt = 1

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.concatenate((np.arange(0,99,1),np.arange(99,120,3),np.arange(120,241,6))),4)]
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)
        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_kt1279_all, (stime, fcst, para, time_range, dtt)))
        # 关闭进程池
        pool.close()
        pool.join()
        print(results)
        # 检查所有进程的返回状态
        for result in results:
            if result.get() == 0:
                status = 0
                break
    elif fcst == "AUTO":
        fh = [0,240]
        dtt = 3
                # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.arange(0,241,3),4)]
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)
        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_auto_all, (stime, fcst, para, time_range, dtt)))
        # 关闭进程池
        pool.close()
        pool.join()
        print(results)
        # 检查所有进程的返回状态
        for result in results:
            if result.get() == 0:
                status = 0
                break
    elif fcst == "KT1279_CLOUD":
        fh=[0,72]
        dtt = 1

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split((np.arange(0,72,1)),4)]
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)
        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_kt1279_cloud_all, (stime, fcst, para, time_range, dtt)))
        # 关闭进程池
        pool.close()
        pool.join()

        # 检查所有进程的返回状态
        for result in results:
            if result.get() == 0:
                status = 0
                break
    elif fcst == "VISFCST":
        fh=[0,48]
        dtt = 1

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split((np.arange(0,48,1)),4)]
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)
        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_visfcst_all, (stime, fcst, para, time_range, dtt)))
        # 关闭进程池
        pool.close()
        pool.join()

        # 检查所有进程的返回状态
        for result in results:
            if result.get() == 0:
                status = 0
                break

    elif fcst == "ERA5":
        fh = [0, 0]
        dtt = 1
        status= grib_era5_all(stime,fcst,para,fh,dtt)
        if status:
            mess+="failed in ERA5 interp"
#        status = grib_era5(stime,fcst,para,fh,dtt)
#        if status:
#            mess+="failed in ERA5 0.5deg interp"
#        status = grib_era5_prs(stime,fcst,para,fh,dtt)
#        if status:
#            mess+="failed in ERA5 1.5deg interp"
    elif fcst == "NCEP":
        if stime.hour in [0,6,12,18]:
            fh=[0,240]
            dtt = 3

            # 设置并行进程数
            n_processes = 4
            # 将时间段分成n_processes份
            time_ranges = [
                [0, 60],
                [60, 120],
                [120, 180],
                [180, 241]
            ]   
            # 创建进程池
            pool = multiprocessing.Pool(processes=n_processes)
            
            # 并行执行grib_ncep_all
            results = []
            for time_range in time_ranges:
                results.append(pool.apply_async(grib_ncep_all, (stime, fcst, para, time_range, dtt)))
            
            # 关闭进程池
            pool.close()
            pool.join()
            
            # 检查所有进程的返回状态
            for result in results:
                if result.get() == 0:
                    status = 0
                    break
        else:
            status = False
            mess = "only 00, 06, 12, 18 can be accepted"

    elif fcst == "ECMWF":
        fh=[0,240]
        dtt = 3

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.concatenate((np.arange(0,78,3),np.arange(78,246,6))),4)]
 
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)

        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_ecmwf_all, (stime, fcst, para, time_range, dtt)))
        
        # 关闭进程池
        pool.close()
        pool.join()
        
        # 检查所有进程的返回状态
        for result in results:
            print("status: ",result.get())
            if result.get() == 0:
                status = 0
                break

    elif fcst == "CLDAS":
        fh = [0, 0]
        dtt = 1
        status= grib_cldas_all(stime,fcst,para,fh,dtt)
        if status:
            mess+="failed in CLDAS 0.5deg interp"

    elif fcst == "CLIMATE":
        fh = [0,0]
        dtt = 1
        status = grib_climate_all(stime,fcst,para,fh,dtt)
        if status:
            mess+="failed in CLIMATE interp"
    elif fcst == "CMA_GFS":

        fh=[0,240]
        dtt = 3

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.arange(0,241,3),4)]

        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)

        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_cmagfs_all, (stime, fcst, para, time_range, dtt)))

        # 关闭进程池
        pool.close()
        pool.join()

        # 检查所有进程的返回状态
        for result in results:
            print("status: ",result.get())
            if result.get() == 0:
                status = 0
                break
    elif fcst == "EMEND":
        fh = [0,72]
        dtt = 1
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        status = grib_emend_all(stime,fcst,para,fh,dtt) 
        if status:
            mess += "failed in EMEND interp"
    elif fcst == "REGION":
    
        fh=[0,72]
        dtt = 1

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.arange(0,73,1),4)]
 
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)

        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_region_tmp_all, (stime, fcst, para, time_range, dtt)))
        
        # 关闭进程池
        pool.close()
        pool.join()
        
        # 检查所有进程的返回状态
        for result in results:
            print("status: ",result.get())
            if result.get() == 0:
                status = 0
                break
    elif fcst == "KJRH":
    
        fh=[0,72]
        dtt = 1

        # 设置并行进程数
        n_processes = 4
        # 将时间段分成n_processes份
        time_ranges = [[_[0],_[-1]+1] for _ in np.array_split(np.arange(0,73,1),4)]
 
        # 创建进程池
        pool = multiprocessing.Pool(processes=n_processes)

        # 并行执行grib_ncep_all
        results = []
        for time_range in time_ranges:
            results.append(pool.apply_async(grib_kjrh_all, (stime, fcst, para, time_range, dtt)))
        
        # 关闭进程池
        pool.close()
        pool.join()
        
        # 检查所有进程的返回状态
        for result in results:
            print("status: ",result.get())
            if result.get() == 0:
                status = 0
                break
    else:
        status = 1
        mess = f"no {fcst} model"
    return {
        "method": 'post',
        "status": True if status ==0 else False,
        "mess": mess
    }
@app.post("/syno")
async def synoptic(model:synoModel):
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fcst = model.fstc
    level = model.level.split(",")
    fh = [int(ff) for ff in  model.fh.split(",")]           
    status = 1
    mess = ""
    status,mess = met_weather.yunyao_synoptic(stime,stime,fcst,para,[fh[0],fh[1]],level,12)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }
@app.post("/syno_feature")
async def synoptic(model:synoModel):
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fcst = model.fstc
    level = model.level.split(",")
    fh = [int(ff) for ff in  model.fh.split(",")]           
    status = 1
    mess = ""
    print(model)
    print(para)
    if "fugao" in para:
        print("fugao")
        status,mess = met_weather.FUGAO(stime,stime,fcst,["fugao"],[fh[0],fh[1]],[50000],12)
    if "lengwo" in para:
        status,mess = met_weather.LENGWO(stime,stime,fcst,["lengwo"],[fh[0],fh[1]],[50000],12)
    if "gaodiya" in para:
        status,mess = met_weather.GAODIYA(stime,stime,fcst,["msl"],[fh[0],fh[1]],[99999],12)

    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

@app.post("/syno_param")
async def synoptic(model:synoModel):
    stime = dt.datetime.strptime(model.startTime,"%Y%m%d%H")
    para = model.para.split(",")
    fcst = model.fstc
    level = model.level.split(",")
    fh = [int(ff) for ff in  model.fh.split(",")]

    status = 1
    mess = ""
    print(model)
    
    status,mess = met_weather.yunyao_synoptic(stime,stime,fcst,para,[fh[0],fh[1]],level,12)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }

#@app.post("/gk_plev")
#async def gaokong_gird(plev: Plev):  # item需要与Item对象定义保持一致
## json define
#    stime = dt.datetime.strptime(plev.startTime,"%Y%m%d%H")
#    area = plev.area.split(",")
#    para = plev.para.split(",")
#    ref = plev.ref
#    fstc = plev.fstc
#    length = int(plev.length)
#    timedelta = int(plev.timedelta)
## param qc control
## meteva block
## def yunyao_plev_pre(starttime,endtime,fcst,anal,output,cmean,region,para):
## starttime,endtime,fcst,anal,output,cmean,region,para,time
#
##   形式场检验
#    if ref != "BUFR":
#        yunyao_plev_pre(stime,stime,fstc,ref,area,para,timedelta,length)
##   站点高空检验
#    else:
#        yunyao_plev_pre_bufr(stime,stime,fstc,ref,area,timedelta,length)
#
## output block
#    return {
#        "method": 'post',
#        "startTime": stime,
#    }


#高空检验
@app.post("/gk_single")
async def gaokong_single(plev:Plev):
    stime = dt.datetime.strptime(plev.startTime,"%Y%m%d%H")
    area = plev.area.split(",")
    para = plev.para.split(",")
    ref = plev.ref
    fstc = plev.fstc
    length=int(plev.length)
    timedelta = int(plev.timedelta)
    if ref != "BUFR":
        status,mess = yunyao_plev_pre(stime,stime,fstc,ref,area,para,timedelta,length)
    else:
        status,mess = yunyao_plev_pre_bufr(stime,stime,fstc,ref,area,para,timedelta,length)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }
if __name__ == '__main__':
    import sys
    port = 5200
    cpu_count = 1
    if len(sys.argv) >=2:
        port = int(sys.argv[1])
        print(port)
    config = uvicorn.Config("main:app", workers=cpu_count * 2, limit_concurrency=1000, port=port, host="0.0.0.0")
    server = uvicorn.Server(config)
    server.run()
#    uvicorn.run(app=app, host="0.0.0.0", port=port)
