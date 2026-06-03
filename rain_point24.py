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
########################dirroot##################################
time      = int(sys.argv[1])
fcstroot  = sys.argv[2]
outputroot= sys.argv[3]
###################################################################
starttime    = datetime.datetime(int(sys.argv[4][0:4]),int(sys.argv[4][4:6]),int(sys.argv[4][6:8]),time)   # YYYY-MM-DD-HH of starttime
endtime      = datetime.datetime(int(sys.argv[5][0:4]),int(sys.argv[5][4:6]),int(sys.argv[5][6:8]),time)   # YYYY-MM-DD-HH of endtime

print('开始时间：',starttime)
print('结束时间：',endtime)

thresholds=[0.1,10,25,50,100,250]
if time == 0:
    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'024.grb'
    cycl_str = '00'
elif time == 12:
    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'036.grb'
    cycl_str = '12'
#if True:
try:
    fcstStr = fcstroot.split("fcst")[-1].split("/")[1]
    cdate=starttime
    
    while cdate<=endtime:
        regridder = None
        obsdate=cdate-datetime.timedelta(hours=time)
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
        print(obsRain24)
        # select one area 
        # obsRain24 = obsRain24[obsRain24["areaID"]==area]
        obsRain24 = obsRain24[obsRain24["areaID"]>=100]
        ds_out_filter = xr.Dataset({
            "lat":("loc",obsRain24["latitude"].to_numpy()),
            "lon":("loc",obsRain24["longitude"].to_numpy())
            })

        for i in range(24+time,240+24,24):
            ccdate=obsdate-datetime.timedelta(hours=i)
    #######################read fcst in the first time step#######################                        
            fcstdate1=fcstroot+'fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grb"
            print(fcstdate1)
            if os.access(fcstdate1,os.F_OK) and os.path.getsize(fcstdate1):
                tp = xr.open_dataset(fcstdate1,engine="cfgrib",indexpath="",backend_kwargs={"filter_by_keys":{"shortName":["prate","tp"]}})
                                
                if "tp" in tp.variables.keys():
                    var = "tp"
                elif "prate" in tp.variables.keys():
                    var = "prate"

                if regridder == None:
                    regridder = xe.Regridder(tp,ds_out_filter,"bilinear",locstream_out=True)
                
                fcstRain24Data = regridder(tp[var],skipna=True)
                obsRain24["fcstRain24"] = fcstRain24Data
                #with open("testrain24.txt","w") as f:
                #    f.write(obsRain24.to_string())                
                # get MASK
                region_list = [100,101,102,103,104,105,106,107]
                for _,regionID in enumerate(region_list):
                
                    outputroot_i = f'{outputroot}_region{regionID}_{cycl_str}/tslist'
                    print('------===========>>>>>>>>>>>>',outputroot_i)
                    if regionID == 100:
                        obsRain24_region = obsRain24[obsRain24["areaID"]>99]
                    else:
                        obsRain24_region = obsRain24[obsRain24["areaID"]==regionID]
                    fcst = np.array(obsRain24_region["fcstRain24"])
                    obs  = np.array(obsRain24_region["precipitation"])
                    mask_ = ((fcst>=0) & (obs>=0))
                    fcst = fcst[mask_]
                    obs  = obs[mask_]
                    fcst_n = np.array(fcst,dtype=np.float32)
                    obs_n  = np.array(obs,dtype=np.float32)
                    #print(fcst_n,obs_n)
                    bias = 1000*abs(np.mean(fcst_n[fcst_n>0.1]) - np.mean(obs_n[obs_n>0.1]))
                    
                    outputdate=outputroot_i+str("%03d"%i)+"."+str(obsdate.strftime("%Y%m%d%H"))
                    
                    f = open(outputdate, "w")
                    f.write("           AA      BB     CC      DD    bias")
                    f.write(' \r\n')
                    
                    for thr in thresholds:
                        aa=0
                        bb=0
                        cc=0
                        dd=0
                        for ii in range(len(fcst)):
                            if fcst[ii]>=thr and obs[ii]>=thr:
                                aa+=1
                            if fcst[ii]>=thr and obs[ii]>=0 and obs[ii]<thr:
                                bb+=1
                            if obs[ii]>=thr and fcst[ii]>=0 and fcst[ii]<thr:
                                cc+=1
                            if fcst[ii]>=0 and fcst[ii]<thr and obs[ii]>=0 and obs[ii]<thr:
                                dd+=1
                        f.write(str("%3g"%thr)+"  mm  "+str("%9d"%aa)+str("%9d"%bb)+str("%9d"%cc)+str("%9d"%dd)+str("%9d"%bias))
                        f.write(' \r\n')
                        print(str("%3g"%thr)+"  mm  "+str("%9d"%aa)+str("%9d"%bb)+str("%9d"%cc)+str("%9d"%dd))
        cdate=cdate+datetime.timedelta(days=1)

except Exception as e:
    if isinstance(e,KeyboardInterrupt):
        raise
    else:
        print('no data!!!')




### python /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/../python/gridrain/rain_point24.py 12 /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/../fcst/NCEP/rain/rain24/ /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/OBS/obs24. /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/mask_region.grib /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/../output/gridrain/ts/data/rain24/NCEP_CLDAS/region105/12/tslist 20250502 20250503 70.5 144 15 64.5 1,3,5,10,15 /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/FCST/24_NCEP /vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/./run/ncep_china.txt /vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/
