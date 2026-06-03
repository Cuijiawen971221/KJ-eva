import numpy as np
import grid_proc
import datetime as dt
import os
import config as cf
from pydantic import BaseModel
from  main  import quyu_grid
import asyncio
import sys
import yunyao_met
import glob

class mpiModel(BaseModel):
    startTime : str
    para: str
    fstc: str


if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
#    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param

  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
#    now_time = dt.datetime.strptime("2024070200","%Y%m%d%H")
    todo_tg_time = []
  # get target time
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
    if fcst == "CLDAS" or fcst == "ERA5":
        nowHH=0 
    tg_time = now_time - dt.timedelta(hours=nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    print("FIRST target Time",tg_time)
    todo_tg_time.append(tg_time)
  # check if tg time job is ok
    if fcst in conf.model:
        tgl = np.sort(glob.glob(conf.message+f"/{fcst}/*/{fcst}*.retry"))[::-1]

        for tg in tgl: # one hour only retry 4 failed project
            tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
            tgdt =  dt.datetime.now()-tgCtime
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,abs(tgdt.total_seconds()))
            if abs(tgdt.total_seconds()) < 3*24*3600 or fcst=="ERA5": # ERA5 has not time limit
                tgstr = dt.datetime.strptime(tg.split("/")[-1],f"{fcst}_%Y%m%d%H.retry")
                todo_tg_time.append(tgstr)
            if len(todo_tg_time)>conf.grid_retry and not fcst == "ERA5":
                break
        print(todo_tg_time)
        for tg_time in np.unique(todo_tg_time):
        # print(fcst)
            t1 = dt.datetime.now()
            jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
            if not os.path.exists(jobpath):
                os.makedirs(jobpath,exist_ok=True)
  #
            jobmess = jobpath + f"/{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
            retrymess = jobpath + f"/{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
            if not os.path.exists(jobmess):
                print("############################",tg_time,fcst)
                if yunyao_met.yunyao_check_fcst_orig(tg_time,fcst):
                    print(yunyao_met.yunyao_check_fcst_orig(tg_time,fcst)) 
                    model = mpiModel(fstc=fcst,para="u",startTime=tg_time.strftime("%Y%m%d%H"))
                    result =  asyncio.run(quyu_grid(model))
                    #result["status"] = True
                    print(result)
                    if result["status"]:
                        with open(jobmess,"w") as f:
                            pass
                        if os.path.exists(retrymess):
                            os.remove(retrymess)
                    else:
                        if os.path.exists(retrymess):
                            pass
                        else:
                            with open(retrymess,"w") as f:
                                pass
                else:
                    if os.path.exists(retrymess):
                        pass
                    else:
                        with open(retrymess,"w") as f:
                            pass
                    print(f"{tg_time} file not enought")
            else:
                print(f"{tg_time} is ok")
                pass
            t2 = dt.datetime.now()
            print(f"time use : {t2-t1}")
    else:
        print(f"{fcst} is not config in pathconfig.yaml")


