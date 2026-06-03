import datetime
import os
import sys
import getRain24Sum
import xarray as xr
import xesmf as xe
import numpy as np

 
regridder = None
obsdate=datetime.datetime(2025,9,1,0,0,0)
obsRain24 = getRain24Sum.getRain(obsdate,24)
ds_out = xr.Dataset({
    "lat":("loc",obsRain24["latitude"].to_numpy()),
    "lon":("loc",obsRain24["longitude"].to_numpy())
    })
# get REGION ID 
mask = xr.open_dataset("/vol8/home/kongjun/VERIFY/met/met_backend/run/landmask_merge.grib",engine="cfgrib",indexpath="")
IDregridder = xe.Regridder(mask,ds_out,"nearest_s2d",locstream_out=True)
ID = IDregridder(mask["unknown"],skipna=True)

# modify region 
obsRain24["areaID"]=np.ma.array(ID,mask=[ID==0])
rain24_Dataset = xr.Dataset()
rain24_Dataset["rain24"] = xr.DataArray(data=obsRain24["precipitation"].to_numpy(),
                           dims=["loc"],
                           coords = {
                               "lat":("loc",obsRain24["latitude"].to_numpy()),
                               "lon":("loc",obsRain24["longitude"].to_numpy()),
                           }
            )
print(rain24_Dataset)
ds_in = xr.Dataset({
    "lat":np.linspace(10,50,41),
    "lon":np.linspace(100,150,51),
})
print(ds_in)
regridder = xe.Regridder(ds_in,ds_out,method="nearest_s2d")
print(regridder)

