import numpy as np
import grid_proc
import datetime as dt
import os
import config as cf
from pydantic import BaseModel
from  main  import quyu_grid,airport_interp_single,airport_interp
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
    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param

  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
#    now_time = dt.datetime.strptime("2025042000","%Y%m%d%H")
    todo_tg_time = []
  # get target time
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
    tg_time = now_time - dt.timedelta(hours=nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    print(tg_time)
    todo_tg_time.append(tg_time)
  # check if tg time job is ok
    if fcst in conf.model:
        # print(fcst)
        tgl = np.sort(glob.glob(conf.message+f"/{fcst}/*/airport_{fcst}*.retry"))[::-1]
        
        for tg in tgl: # one hour only retry 4 failed project
            tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
            tgdt =  dt.datetime.now() - tgCtime
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,tgdt)
            if abs(tgdt.total_seconds()) < 3*24*3600:
                tgstr = dt.datetime.strptime(tg.split("/")[-1],f"airport_{fcst}_%Y%m%d%H.retry")
                todo_tg_time.append(tgstr)
            if len(todo_tg_time)>conf.airport_retry:
                break
        for tg_time in np.unique(todo_tg_time):
            t1 = dt.datetime.now()
            jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
            if not os.path.exists(jobpath):
                os.makedirs(jobpath,exist_ok=True)
  #
            jobabovemess = jobpath + f"/{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
            if fcst =="CMA_GFS":
                jobrainabovemess = conf.message_rain+f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"+f"/rain24_CMAGFS_{tg_time.strftime('%Y%m%d%H')}.ok"
            else:
                jobrainabovemess = conf.message_rain+f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"+f"/rain24_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
            jobnextmess = jobpath + f"/airport_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
            retrynextmess = jobpath + f"/airport_{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
            if not os.path.exists(jobnextmess):
                print(jobabovemess,jobrainabovemess)
                rainStatus = False
                if fcst not in ["AUTO","CMA_GFS","KT1279","ECMWF","NCEP"]:
                   rainStatus = True
                else:
                   rainStatus = os.path.exists(jobrainabovemess)
                   rainStatus = True
                print("rainStatus",rainStatus)
                print("modelStatus",os.path.exists(jobabovemess))
                if os.path.exists(jobabovemess) and rainStatus :
                    print("OOOOOOOOKKKKKKKKKK")
                    model = mpiModel(fstc=fcst,\
                      para="2t,2d,2r,10u,10v,sp,mslp,vis,tcc,lcc,ch,rad,rain24",\
                      startTime=tg_time.strftime("%Y%m%d%H"))
                    result =  asyncio.run(airport_interp_single(model))

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
         
                #for sa in sta:
                #    messout.append(sa[1])
                #    if sa[0] :
                #        status = sa[0]
                #        t1 = datetime.datetime.now()
                #        batch_size = 100
                #        for i in range(0, len(sa[2]), batch_size):
                #            batch = sa[2].iloc[i:i + batch_size]
                #            clickclient.insert_df("airport_forecast_data", batch)
                #        print(datetime.datetime.now() - t1)



                else:
                    if os.path.exists(retrynextmess):
                        pass
                    else:
                        with open(retrynextmess,"w") as f:
                            pass
                    print(f"{tg_time} grid proc failed")
            else:
                print(f"{tg_time} is ok")
                pass
            t2 = dt.datetime.now()
            print(f"time use : {t2-t1}")


