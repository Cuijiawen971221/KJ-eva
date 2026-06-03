import numpy as np
import grid_proc
import datetime as dt
import os
import config as cf
from pydantic import BaseModel
from  main  import quyu_grid,airport_interp_single,airport_interp,Plev,dimian_single
import asyncio
import sys
import yunyao_met
from clickhouse_util import clickclient
import glob

class mpiModel(BaseModel):
    startTime : str
    para: str
    fstc: str

if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
    timedelta = sys.argv[2]
    ref = "AWS"

    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml")
 ###################
  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
     
    todo_tg_time = [] 
  # get target time
    tg_time = now_time
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    todo_tg_time.append(tg_time)
	
    area = yunyao_met.queryregion()
    plev = Plev(startTime =tg_time.strftime("%Y%m%d%H"), timedelta=timedelta,area=area,para="2t,2d,2r,wind,wdir,sp,mslp,rad,vis,tcc,lcc,ch",ref="AWS",fstc=fcst,length=timedelta)
    
    tgl = np.sort(glob.glob(conf.message+f"/awsplev_{fcst}*.retry"))[::-1]
    
    for tg in tgl[::4]:
        tgstr = dt.datetime.strptime(tg.split("/")[-1],f"awsplev_{fcst}*.retry")
        todo_tg_time.append(tgstr)
    print(todo_tg_time)
    for tg_time in np.unique(todo_tg_time):
        jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
        if not os.path.exists(jobpath):
            os.makedirs(jobpath,exist_ok=True)
        HH = tg_time.hour
        if HH >12:
            HH = H -12
        aboveTime = tg_time-dt.timedelta(hours=HH)
        jobabovemess = jobpath + f"/{fcst}_{aboveTime.strftime('%Y%m%d%H')}.ok"
        jobnextmess = jobpath + f"/awsplev_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        retrynextmess = jobpath + f"/awsplev_{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
        if not os.path.exists(jobnextmess):
            if os.path.exists(jobabovemess):

                result = asyncio.run(dimian_single(plev))
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
                print(f"{tg_time} grid proc failed")
        else:
            print(f"{tg_time} is ok")

        print(plev)
