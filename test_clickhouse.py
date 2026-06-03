from clickhouse_util import clickclient
import numpy as np
import xarray as xr
from py2java import pyweb2java
import datetime

if __name__ == "__main__":
    ppp = ",".join([pyweb2java(var) for var in ["2t","2d"]])
    obsdate = datetime.datetime.strptime("2025050100","%Y%m%d%H")
    sql = "SELECT station_id, station_code, longitude, latitude FROM station_info"
    station = clickclient.query_df(sql)
    print(station)
    
   # station_longitude = np.array(station["longitude"],dtype = np.float64)
   # station_longitude[np.where(station_longitude<0)] = 360 + station_longitude[np.where(station_longitude<0)]
   # station_latitude = np.array(station["latitude"],dtype = np.float64)
   # statFromDB = xr.Dataset({\
   #         "longitude": station_longitude,
   #         "latitude":station_latitude,
   #         "station_id": np.array(station["station_id"])\
   #                 })

