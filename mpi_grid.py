import numpy as np 
import grid_proc
import datetime as dt
import os
import config as cf
from pydantic import BaseModel
from  main  import quyu_grid
import asyncio
import yunyao_met

class mpiModel(BaseModel):
    startTime : str
    para: str
    fstc: str


if __name__ == "__main__":
   
  # global configure set  
    conf = cf.pparms("./pathconfig.yaml")

    now_time = dt.datetime.now()
  # get target time 
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
    tg_time = now_time - dt.timedelta(hours=nowHH)    
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")

  # check if tg time job is ok 
    for fcst in conf.model:
        # print(fcst)

        jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
        if not os.path.exists(jobpath):
            os.makedirs(jobpath,exist_ok=True)
  # 
        jobmess = jobpath + f"/{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        if not os.path.exists(jobmess):
            if fcst == "ECMWF":
                if yunyao_met.yunyao_check_fcst_orig(tg_time,fcst):
                    model = mpiModel(fstc=fcst,para="u",startTime=tg_time.strftime("%Y%m%d%H"))
                    result =  asyncio.run(quyu_grid(model))
                    result["status"] = True
                    if result["status"]:
                        with open(jobmess,"w") as f:
                            pass
                else:
                    print("no such file")
                    pass

        else:
            print("already done")
            pass



     
