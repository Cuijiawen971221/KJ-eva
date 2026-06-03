import numpy as np
import grid_proc
import datetime as dt
import os
import config as cf
from pydantic import BaseModel
from  main  import quyu_grid,airport_interp_single,airport_interp,Plev,dimian_single,gaokong_single
import asyncio
import sys
import yunyao_met
from clickhouse_util import clickclient
import glob
import xarray as xr 
from cfgrib.xarray_to_grib import to_grib

class mpiModel(BaseModel):
    startTime : str
    para: str
    fstc: str
    HPC_env: str

if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
#   timedelta = sys.argv[2]
#   ref = sys.argv[3]
    

    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param
 ###################
  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=32) # UTC time 
    #now_time = dt.datetime.strptime("2025082900","%Y%m%d%H")#t.datetime.now() - dt.timedelta(hours=8+12) # UTC time 
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
        
  # get target time
    tg_time = now_time - dt.timedelta(hours=nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    print(tg_time)
    todo_tg_time = [] 
    todo_tg_time.append(tg_time)
	
    area = yunyao_met.queryregion()
    
    tgl = np.sort(glob.glob(conf.message_rain+f"/{fcst}/*/cvrain24_{fcst}*.retry"))[::-1]
#   print(conf.message+f"/{fcst}/{tg_time.strftime('%Y%m%d')}/rain24_{fcst}*.retry")
    #rint(tgl)
    for tg in tgl: # one hour only retry 4 failed project
            tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
            tgdt =  dt.datetime.now() - tgCtime
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,tgdt)
            if abs(tgdt.total_seconds()) < 3*24*3600:
                tgstr = dt.datetime.strptime(tg.split("/")[-1],f"cvrain24_{fcst}_%Y%m%d%H.retry")
                todo_tg_time.append(tgstr)
            if len(todo_tg_time)>conf.area_retry:
                break
        
    print(todo_tg_time)
    
    for tg_time in np.unique(todo_tg_time):
        
        jobpath = conf.message_rain + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
        if not os.path.exists(jobpath):
            os.makedirs(jobpath,exist_ok=True)
        
        #HH = tg_time.hour
        #if HH >12:
        #    HH = HH -12
        #aboveTime = tg_time-dt.timedelta(hours=HH)
        
        jobabovemess = jobpath + f"/rain24_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        
        jobnextmess = jobpath + f"/cvrain24_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        retrynextmess = jobpath + f"/cvrain24_{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
        if not os.path.exists(jobnextmess):
            print(jobabovemess)
            if os.path.exists(jobabovemess):
                if True:
#                try:
                    filelist = glob.glob(conf.ncepoutputpath+f"{fcst}/rain/rain24/fcst{tg_time.strftime('%Y%m%d%H')}*.grb")
                    print(filelist)   
                    for filen in filelist:
                        try:
                            rain = xr.open_dataset(filen,engine="cfgrib",indexpath="")["prate"]
                            paramDims = rain.dims
                            tmpCoords = rain.coords
                            print(tmpCoords,paramDims)
                            tmpDataArray=xr.DataArray(
                                rain.data, coords=tmpCoords, dims = paramDims
                            )
                            tmpDataArray.attrs["GRIB_paramId"] = 3059

                            outGrib = tmpDataArray.to_dataset(name="prate")
                            outGrib.attrs["GRIB_centre"] = "rjtd"
                            outGrib.attrs["edition"] = 1
                            _, outpath,_,_ = grid_proc.config_path(fcst)
                            finaloutpath = outpath+f"/{fcst}/normal/{tg_time.strftime('%Y%m%d')}/"
                            os.makedirs(finaloutpath,exist_ok=True)
                            print(outGrib)
                            to_grib(outGrib, finaloutpath+filen.split("/")[-1].replace("fcst","rain24"))
                        except:
                            rain = xr.open_dataset(filen,engine="cfgrib",indexpath="")["tp"]
                            paramDims = rain.dims
                            tmpCoords = rain.coords
                            print(tmpCoords,paramDims) 
                            tmpDataArray=xr.DataArray(
                                rain.data, coords=tmpCoords, dims = paramDims
                            )
                            tmpDataArray.attrs["GRIB_paramId"] = 3059
                        
                            outGrib = tmpDataArray.to_dataset(name="tp")
                            outGrib.attrs["GRIB_centre"] = "rjtd"
                            outGrib.attrs["edition"] = 1
                            _, outpath,_,_ = grid_proc.config_path(fcst)
                            finaloutpath = outpath+f"/{fcst}/normal/{tg_time.strftime('%Y%m%d')}/"
                            os.makedirs(finaloutpath,exist_ok=True)
                            print(outGrib)
                            to_grib(outGrib, finaloutpath+filen.split("/")[-1].replace("fcst","rain24"))
                    result = {"status":True}
                    # job here
#                   plev = Plev(startTime =tg_time.strftime("%Y%m%d%H"), timedelta=timedelta,area=area,para="t,gh,r,wind,wdir",ref=ref,fstc=fcst,length="21",)
#                   result = asyncio.run(gaokong_single(plev))
#                   #result["status"] = True
#                   for sa in result:
#                       print(sa[1])
#                except:
#                    result={"status":False}
                if result["status"]:
                    with open(jobnextmess,"w") as f:
                        pass
                    if os.path.exists(retrynextmess):
                        os.remove(retrynextmess)
                else:
                    if os.path.exists(retrynextmess):
                        pass
                    else:
                         with open(retrynextmess,"w") as f:
                             pass
            else:
                
                if os.path.exists(retrynextmess):
                   pass
                else:
                    with open(retrynextmess,"w") as f:
                        pass
                print(f"{tg_time} grid proc failed")
        else:
            print(f"{tg_time} is ok")

