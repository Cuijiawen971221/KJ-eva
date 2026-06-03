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

if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
    timedelta = sys.argv[2]
    ref = sys.argv[3]
    

    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml")
 ###################
  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
    #now_time = dt.datetime.strptime("2025081400","%Y%m%d%H")#t.datetime.now() - dt.timedelta(hours=8+12) # UTC time 
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
    print(tgl)
    for tg in tgl: # one hour only retry 4 failed project
            tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
            tgdt =  tgCtime-dt.datetime.now()
            if abs(tgdt.total_seconds()) < 3*24*3600:
                tgstr = dt.datetime.strptime(tg.split("/")[-1],f"plev_{ref}_{fcst}_%Y%m%d%H.retry")
                todo_tg_time.append(tgstr)
            if len(todo_tg_time)>5:
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
            if os.path.exists(jobabovemess):
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
                    with open(retrynextmess,"w") as f:
                        pass
            else:
                
                with open(retrynextmess,"w") as f:
                    pass
                print(f"{tg_time} grid proc failed")
        else:
            print(f"{tg_time} is ok")

