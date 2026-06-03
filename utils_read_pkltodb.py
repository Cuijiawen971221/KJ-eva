from clickhouse_util_host  import clickclient_db
import grid_proc
import sys
import glob
import datetime as dt
import pickle

if __name__ =="__main__":
    fcst = sys.argv[1]
    outpath,fcstpath, toolspath, weight = grid_proc.config_path(fcst)

  # UTC time
    now_time = dt.datetime.now() - dt.timedelta(hours=8)# UTC time 

  # get target time
    nowHH = now_time.hour
    if nowHH>12:
        nowHH=nowHH-12
    tg_time = now_time - dt.timedelta(hours=nowHH)
    tg_time = dt.datetime.strptime(tg_time.strftime("%Y%m%d%H"),"%Y%m%d%H")
    YYYYMMDDHH= tg_time.strftime("%Y%m%d%H")
    YYYYMMDD= tg_time.strftime("%Y%m%d")
    HH= tg_time.strftime("%H")

    filel = glob.glob(fcstpath + f"/{fcst}/normal/{YYYYMMDD}/airport_interp_{YYYYMMDDHH}*.*_*")
    for filen in filel:
        print(filen)
        with open(filen,"rb") as f:
            sa = pickle.load(f)
            batch_size = 10000
            for i in range(0, len(sa), batch_size):
                batch = sa.iloc[i:i + batch_size]
                clickclient_db.insert_df("airport_forecast_data", batch)

     
    


