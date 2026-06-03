import numpy as np
import eccodes
from scipy.ndimage.filters import uniform_filter
from nwpc_data.grib.eccodes import load_message_from_file
import datetime
import os
import sys
import getRain24Sum
import xarray as xr
import xesmf as xe

time = 12
starttime    = datetime.datetime(2026,2,10,12)   # YYYY-MM-DD-HH of starttime
endtime      = datetime.datetime(2026,2,10,12)   # YYYY-MM-DD-HH of endtime

print('开始时间：',starttime)
print('结束时间：',endtime)

thresholds=[0.1,10,25,50,100,250]
#if time == 0:
#    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'024.grb'
#    cycl_str = '00'
#elif time == 12:
#    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'036.grb'
#    cycl_str = '12'
if True:
#try:
    #fcstStr = fcstroot.split("fcst")[-1].split("/")[1]
    cdate=starttime

    while cdate<=endtime:
        regridder = None
        obsdate=cdate-datetime.timedelta(hours=time)
        obsRain24 = getRain24Sum.getRain(obsdate,24)
        ds_out = xr.Dataset({
            "lat":("loc",obsRain24["latitude"].to_numpy()),
            "lon":("loc",obsRain24["longitude"].to_numpy())
            })

