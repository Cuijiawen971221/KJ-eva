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

class mpiModel(BaseModel): # 
    startTime : str 
    para: str 
    fstc: str



#class mpiModel(BaseModel):
#    startTime : str
#    para : str
#
#    fstc : str

def check_bufr_count(tg_time):
    tg_time_str = tg_time.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select count(*)  from surface_observation_data where message_type='surf_bufr' and observation_time='{tg_time_str}'"

    count = float(clickclient.query_df(sql)["count()"])

    print("%%%%%%%%%%%%%%%%%%% ",tg_time_str," station count :",count)
    if count > 1800:
        status = True
    else:
        status = False
    return status

def check_aws_count(tg_time):
    tg_time_str = tg_time.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select count(*)  from surface_observation_data where message_type='station' and observation_time='{tg_time_str}'"

    count = float(clickclient.query_df(sql)["count()"])

    print("%%%%%%%%%%%%%%%%%%% ",tg_time_str," station count :",count)
    if count > 75000:
        status = True
    else:
        status = False
    return status


if __name__ == "__main__":
  # param get 

    fcst = sys.argv[1]
    timedelta = sys.argv[2]
    ref = sys.argv[3]
    leng = sys.argv[4]
    print(fcst)
  # global configure set
    conf = cf.pparms("./pathconfig.yaml").param
 ###################
  # UTC time
    #now_time = dt.datetime(2025,5,5,6)
    now_time = dt.datetime.now() - dt.timedelta(hours=8) # UTC time 
    nowHH = now_time.hour 
    
    if nowHH>=6 and nowHH<12:
        nowHH= nowHH-6
    elif nowHH>=12 and nowHH <18:
        nowHH = nowHH-12
    elif nowHH>=18:
        nowHH = nowHH-18
    
    todo_tg_time = []
  # get target time

    tg_time = now_time - dt.timedelta(hours=nowHH)
    print(tg_time,now_time,nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    todo_tg_time.append(tg_time)
    print(tg_time)
    area = yunyao_met.queryregion()
    strleng = 240//int(timedelta)
    
    
    tgl = np.sort(glob.glob(conf.message+f"/{fcst}/*/{ref}_{fcst}*.retry"))[::-1]
    print(conf.message+f"/{fcst}/*/{ref}_{fcst}*.retry") 
    for tg in tgl: # one hour only retry 4 failed project
        tgCtime = dt.datetime.fromtimestamp(os.path.getctime(tg))
        tgdt = dt.datetime.now() - tgCtime
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",tg,tgdt)
        if abs(tgdt.total_seconds()) < 3*24*3600 or ref=="ERA5":
            tgstr = dt.datetime.strptime(tg.split("/")[-1],f"{ref}_{fcst}_%Y%m%d%H.retry")
            todo_tg_time.append(tgstr)
        if len(todo_tg_time)>conf.area_retry and ref!="ERA5":
            break
        if len(todo_tg_time)> conf.area_retry+28 and ref=="ERA5":
            break
    print(todo_tg_time)

    for tg_time in np.unique(todo_tg_time):
        jobpath = conf.message + f"/{fcst}/{tg_time.strftime('%Y%m%d')}/"
        if not os.path.exists(jobpath):
            os.makedirs(jobpath,exist_ok=True)
        
        HH = tg_time.hour
        if HH >12:
            HH = HH -12
        aboveTime = tg_time-dt.timedelta(hours=HH)
        jobabovemess = jobpath + f"/{fcst}_{aboveTime.strftime('%Y%m%d%H')}.ok"

        jobnextmess = jobpath + f"/{ref}_{fcst}_{tg_time.strftime('%Y%m%d%H')}.ok"
        retrynextmess = jobpath + f"/{ref}_{fcst}_{tg_time.strftime('%Y%m%d%H')}.retry"
        if not os.path.exists(jobnextmess):

            if ref == "GTS":
                refStatus = check_bufr_count(tg_time)
            elif ref == "AWS":
                refStatus = check_aws_count(tg_time)
            else:
                refStatus = True

            if os.path.exists(jobabovemess):

                plev = Plev(startTime =tg_time.strftime("%Y%m%d%H"), timedelta=timedelta,area=area,para="2t,2d,2r,10u,10v,sp,mslp,vis,tcc,lcc,ch,rad,wind,wdir",ref=ref,fstc=fcst,length=leng)
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

