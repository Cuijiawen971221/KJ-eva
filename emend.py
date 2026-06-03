from clickhouse_util import clickclient
import datetime
import glob
import config
import re
import numpy as np
import pandas as pd
import utils

globalConf = config.pparms("./pathconfig.yaml" ).param
fcstpath = globalConf.emendfcstpath
VAR = ["CLC", "PRC", "T2C", "UMC", "VMC", "VIC"]
#VAR = ["PRC", "T2C", "UMC", "VMC", "VIC"]

def emend_decode(startTime:datetime.datetime, fcst:str,fh:list, dt:int):
    status = True
    try:
        sql = """
                    SELECT station_id, station_code, longitude, latitude FROM station_info
         """
        station_list = clickclient.query_df(sql)
        #print(station_list)
        YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
        YYYYMMDD = startTime.strftime("%Y%m%d")
        HH = startTime.strftime("%H")
        print(fcstpath + "/{:s}/*/*{:s}*.TXT".format(YYYYMMDDHH, YYYYMMDDHH))
        filename_list = glob.glob(fcstpath + "/{:s}/{:s}/*/*{:s}*.TXT".format(fcst,YYYYMMDDHH, YYYYMMDDHH))
        print(filename_list)
        station_codes = np.unique([str(filen.split("-")[-2]) for filen in filename_list])
        tmpdf = {"station_id": [], "forecast_date": [], "forecast_hour": [], "mode_type": [], "forecast_interval": [],\
                 "temperature": [], "dew_point_temperature": [], "humidity": [], "wind_speed": [], "wind_direction": [], \
                 "precipitation": [], "pressure": [], "sea_level_pressure": [],"radiation":[],"visibility":[],\
                 "total_cloud_cover":[],"low_cloud_cover":[],"cloud_height":[],"target_time":[]}
        resdf = pd.DataFrame(tmpdf)

        print(station_codes)
        for station_code in station_codes:
          # if station_code != "000": continue
            station_id = np.array(station_list[station_list["station_code"]==station_code]["station_id"])[0]

            result = np.ones((fh[1], len(VAR))) * -999.0
            filename_list = glob.glob(fcstpath + "/{:s}/{:s}/*/*{:s}*-{:s}*.TXT".format(fcst,YYYYMMDDHH, YYYYMMDDHH, station_code))
            for file_name in filename_list:
                print(file_name)
                var =  str(file_name.split("-")[-3])
                index = VAR.index(var)
                data = []
                with open(file_name, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            data.append(float(parts[1]))
                result[:,index] = data
            resdf = fill_resdf(resdf,result,startTime,fcst,station_id)
        # print(resdf.to_csv("emend.csv"))
        batch_size = 20000
        for i in range(0, len(resdf), batch_size):
            batch = resdf.iloc[i:i + batch_size]
            clickclient.insert_df("airport_forecast_data", batch)
        print(datetime.datetime.now() - t1)
    except:
        status = False
    return status    

def fill_resdf(resdf,result,startTime,fcst,station_id):
    tmp_prc = 0
    for ii in range(1,result.shape[0]+1,1):
        res = result[ii-1,:]
        lcc = res[VAR.index("CLC")]
        ###### 24 h #################????
        #tmp_prc = np.ones_like(res[VAR.index("PRC")])*-999.0
        #for i in range(len(tmp_prc)//24):
        #    tmp_prc[i*24-1] = np.sum(res[VAR.index("PRC")][i:i*24+24])
        #prc = tmp_prc  #res[VAR.index("PRC")]
        tmp_prc += res[VAR.index("PRC")]
        if (ii - ii//24*24) == 0:
            prc=tmp_prc
            tmp_prc = 0
        else:
            prc = -999.0
        ###### 24 h #################
    #   prc = 
       
        t2 = res[VAR.index("T2C")]+273.15 
        u10 = -res[VAR.index("UMC")]
        v10 = -res[VAR.index("VMC")]
        vis = res[VAR.index("VIC")]
        wsp, wdir = utils.getWindWdir(u10,v10)
        tgtime = startTime+datetime.timedelta(hours=ii-8)
        resdf.loc[len(resdf)] = {"station_id": str(station_id), "forecast_date": startTime.strftime("%Y-%m-%d") , "forecast_hour": startTime.strftime("%H") , "mode_type":fcst, "forecast_interval": ii,\
        "temperature": t2, "dew_point_temperature": -999.0, "humidity": -999.0,\
        "wind_speed": wsp, "wind_direction": wdir, "precipitation": prc, "pressure": -999.0,\
        "sea_level_pressure": -999.0,"radiation":-999.0,"visibility":vis,\
        "total_cloud_cover":-999.0,"low_cloud_cover":lcc,"cloud_height":-999.0,"target_time":tgtime} 
    return resdf


if __name__ == "__main__":
    stime = '2024070200'
    startTime = datetime.datetime.strptime(stime,"%Y%m%d%H")
    fh = [0,72]
    dt = 1
    emend_decode(startTime, "EMEND", fh, dt)
