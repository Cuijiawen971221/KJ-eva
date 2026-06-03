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

class mpiModel(BaseModel):
    startTime : str
    para: str
    fstc: str
    HPC_env: str
    
def check_bufr_count(tg_time):
    tg_time_str = tg_time.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select count(*)  from upper_observation_data where height='500' and observation_time='{tg_time_str}'"
   
    count = float(clickclient.query_df(sql)["count()"])

    print("%%%%%%%%%%%%%%%%%%% ",tg_time_str," station count :",count)
    if count > 100:
        status = True
    else:
        status = False
    return status

if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
    timedelta = sys.argv[2]
    ref = sys.argv[3]
    

    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param
 ###################
  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
    #now_time = dt.datetime.strptime("2025082900","%Y%m%d%H")#t.datetime.now() - dt.timedelta(hours=8+12) # UTC time 
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
        
  # get target time
    tg_time = now_time - dt.timedelta(hours=nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    todo_tg_time = [] 
    todo_tg_time.append(tg_time)
	
    area = yunyao_met.queryregion()
    
    tgl = np.sort(glob.glob(conf.message+f"/{fcst}/*/plev_{ref}_{fcst}*.retry"))[::-1]
    print(conf.message+f"/{fcst}/{tg_time.strftime('%Y%m%d')}/plev_{ref}_{fcst}*.retry")
    #rint(tgl)
    for tg in tgl: # one hour only retry 4 failed project
            tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
            tgdt =  dt.datetime.now() - tgCtime
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,tgdt)
            if abs(tgdt.total_seconds()) < 3*24*3600 or ref=="ERA5":
                tgstr = dt.datetime.strptime(tg.split("/")[-1],f"plev_{ref}_{fcst}_%Y%m%d%H.retry")
                todo_tg_time.append(tgstr)
            if len(todo_tg_time)>conf.area_retry and ref != "ERA5":
                break
            if ref == "ERA5" and len(todo_tg_time)> conf.area_retry + 14:
                break 
        
    print(todo_tg_time)
    
    for tg_time in np.unique(todo_tg_time):
        
        jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
        if not os.path.exists(jobpath):
            os.makedirs(jobpath,exist_ok=True)
        
        #HH = tg_time.hour
        #if HH >12:
        #    HH = HH -12
        #aboveTime = tg_time-dt.timedelta(hours=HH)
        
        jobabovemess = jobpath + f"/{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        
        jobnextmess = jobpath + f"/plev_{ref}_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        retrynextmess = jobpath + f"/plev_{ref}_{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
        if not os.path.exists(jobnextmess):
            print(jobabovemess)
            if ref == "BUFR":
                refStatus = check_bufr_count(tg_time)
            else:
                refStatus = True
            if os.path.exists(jobabovemess) and refStatus:
                plev = Plev(startTime =tg_time.strftime("%Y%m%d%H"), timedelta=timedelta,area=area,para="t,gh,r,wind,wdir",ref=ref,fstc=fcst,length="21",)
                result = asyncio.run(gaokong_single(plev))
                #result["status"] = True
                for sa in result:
                    print(sa[1])
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

