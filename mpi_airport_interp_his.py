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
  # """
  # 用法: python mpi_airport_interp_his.py <模式> <开始时次> <结束时次>
  # 时次格式: YYYYMMDDHH
  # """
    if len(sys.argv) != 4:
        print(f"用法: python {os.path.basename(__file__)} <模式> <开始时次> <结束时次>")
        print("时次格式: YYYYMMDDHH")
        sys.exit(2)
    fcst = sys.argv[1]
    st_str_ = sys.argv[2]
    ed_str_ = sys.argv[3]
    print(fcst, st_str_, ed_str_)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param
    
    st_t    = dt.datetime.strptime(st_str_,"%Y%m%d%H")
    ed_t    = dt.datetime.strptime(ed_str_,"%Y%m%d%H")
    current_t = st_t
    
    while current_t <= ed_t:
        current_t_str = current_t.strftime("%Y%m%d%H")        
        now_time = dt.datetime.strptime(current_t_str,"%Y%m%d%H")
        todo_tg_time = []
  # get target time
        nowHH = now_time.hour
        if nowHH>=12:
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
                tgdt =  now_time - tgCtime
                print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,tgdt)
                if abs(tgdt.total_seconds()) < 3*24*3600:
                    tgstr = dt.datetime.strptime(tg.split("/")[-1],f"airport_{fcst}_%Y%m%d%H.retry")
                    todo_tg_time.append(tgstr)
                if len(todo_tg_time)>conf.airport_retry:
                    break
            print('=============>>>>>>>',todo_tg_time)
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
                        model = mpiModel(fstc=fcst,para="2t,2d,2r,10u,10v,sp,mslp,vis,tcc,lcc,ch,rad,rain24",startTime=tg_time.strftime("%Y%m%d%H"))
                        result =  asyncio.run(airport_interp_single(model))
                        print('====================================',result)
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
                    pass
                # t2 = dt.datetime.now()
                # print(f"time use : {t2-t1}")
        current_t += dt.timedelta(hours = 12)


