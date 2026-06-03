import numpy as np
import eccodes
# from scipy.ndimage.filters import uniform_filter 
from scipy.ndimage import uniform_filter 
from nwpc_data.grib.eccodes import load_message_from_file
import datetime
import os
import sys
import numpy as np
import eccodes
from scipy.ndimage.filters import uniform_filter
from nwpc_data.grib.eccodes import load_message_from_file
import datetime
import os
import sys
import getRain24Sum_cjw
import xarray as xr
import xesmf as xe
from interp_point2grid import *
#os.chdir('/vol8/home/kongjun/VERIFY/20250806_deploy/met_backend/python/gridrain/')
########################dirroot##################################
time         = int(sys.argv[1])  # initial time
fcstroot     = sys.argv[2]
obsroot      = sys.argv[3]
maskroot     = sys.argv[4]
###################################################################
starttime    = datetime.datetime(int(sys.argv[5][0:4]),int(sys.argv[5][4:6]),int(sys.argv[5][6:8]),time)   # YYYY-MM-DD-HH of starttime
endtime      = datetime.datetime(int(sys.argv[6][0:4]),int(sys.argv[6][4:6]),int(sys.argv[6][6:8]),time)     # YYYY-MM-DD-HH of endtime
lonst        = float(sys.argv[7])
loned        = float(sys.argv[8])
latst        = float(sys.argv[9])
lated        = float(sys.argv[10])
half_size_str= sys.argv[11]
half_size    = np.array(list(map(int, half_size_str.split(','))))
FCST_path    = sys.argv[12]
grid_file    = sys.argv[13]
cdo_path     = sys.argv[14]
region_id    = int(sys.argv[15])
outname_final= sys.argv[16]
domain=[latst,lated,lonst,loned]
scales=half_size
thresholds=[0.1,10,25,50,100,250]#[0.1,1,5,10,25,50,100]

#print('半窗尺寸',scales)
###################################################################
if time == 0:
    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'024.grb'
elif time == 12:
    testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'036.grb'

## get info from info_file
info_file = FCST_path+'/info.grb'
os.chdir(cdo_path)
cmd1 = f"./cdo remapbil,{grid_file} {testfile} {info_file}"
os.system(cmd1)

if True:
#try:
    f = open(info_file, "rb")
    gid = eccodes.codes_grib_new_from_file(f)
    if gid is None:
        print("create handler error")
    ni = eccodes.codes_get(gid, "Ni")
    nj = eccodes.codes_get(gid, "Nj")
    values = eccodes.codes_get_values(gid)
    resolution = eccodes.codes_get(gid, 'iDirectionIncrementInDegrees')
    slat = eccodes.codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
    elat = eccodes.codes_get(gid, 'latitudeOfLastGridPointInDegrees')
    slon = eccodes.codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
    elon  = eccodes.codes_get(gid, 'longitudeOfLastGridPointInDegrees')
    #print(slat,elat,slon,elon)
    cdate=starttime
    while cdate<=endtime:
        ####################################################################
        regridder = None
        obsdate=cdate-datetime.timedelta(hours=time)
        obsRain24 = getRain24Sum_cjw.getRain(obsdate,24)
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

        # select one area 
        # obsRain24 = obsRain24[obsRain24["areaID"]==area]
        if region_id == 100:
            obsRain24 = obsRain24[obsRain24["areaID"]>=100]
        else:
            obsRain24 = obsRain24[obsRain24["areaID"]==region_id]
        ####################################################################
        #obsdate=cdate-datetime.timedelta(hours=time)
        for i in range(24+time,240+24,24):
            ccdate=obsdate-datetime.timedelta(hours=i)
    #######################read fcst in the first time step#######################                        
            fcstdate1=fcstroot+'fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grb"
            fcstdate_new = FCST_path+'/fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grb"
            os.chdir(cdo_path)
            cmd2 = f"./cdo remapbil,{grid_file} {fcstdate1} {fcstdate_new}"
            os.system(cmd2)
                        ##
            if os.access(fcstdate_new,os.F_OK) and os.path.getsize(fcstdate_new):
                try:
                    t = load_message_from_file(
                        file_path=fcstdate_new,
                        parameter='prate',
                        level_type="surface",
                        level=0,
                                )
                    fcst1=eccodes.codes_get_double_array(t, "values")
                except:
                    t = load_message_from_file(
                        file_path=fcstdate_new,
                        parameter='tp',
                        level_type="surface",
                        level=0)
                    fcst1=eccodes.codes_get_double_array(t, "values")
                fcst1=fcst1.reshape([nj, ni])

                if slat>elat:
                    sj = int((slat - domain[1]) / resolution)
                    ej = int((slat - domain[0]) / resolution)
                else:
                    sj=int((domain[0]-slat)/resolution)
                    ej=int((domain[1]-slat)/resolution)
                si=int((domain[2] - slon) / resolution)
                ei=int((domain[3] - slon) / resolution)
                print('>>>>>>>>>>>>>',nj,ni,'<<<<<<<<<<<<<<',sj,ej,si,ei)
    ##############################################################################
    ########### read fcst in the second time step#######################

                fcsttmp=fcst1
                fcst=fcsttmp[sj:ej+1,si:ei+1]
                fcst[fcst<0] = 0#print('预报统计：',fcst.min(),fcst.max())
    ########### read obs ####################################################
                obsfile=obsroot+str(obsdate.strftime("%Y%m%d%H"))+".grib"
                
                if os.access(obsfile,os.F_OK) and os.path.getsize(obsfile):
                    f = open(obsfile, "rb")
                    gid = eccodes.codes_grib_new_from_file(f)
                    if gid is None:
                        print("create handler error")
                    values = eccodes.codes_get_values(gid)
                    obstmp = np.reshape(values, (nj, ni))
                    obstmp[obstmp==9999]=-999
                    obstmp[obstmp<0] = np.nan
                    obs=obstmp[sj:ej+1,si:ei+1]
                    ##
                    station_df = obsRain24
                    
                    #grid_resolution = 0.5  # 0.5度网格
                    lat_grid = np.linspace(elat,slat,obs.shape[0])
                    lon_grid = np.linspace(slon,elon,obs.shape[1])
                    grid_data = grid_data_by_lat_lon(
                                               station_df,
                                               'latitude',
                                               'longitude',
                                               'precipitation',
                                               lon_grid, 
                                               lat_grid,
                                               resolution
                                           )
 
                    ## 
                    #obstmp[obstmp==9999]=-999
                    #obstmp[obstmp<0] = np.nan
                    obs = np.flipud(grid_data)
                    obs[obs<0] = np.nan
                    #obs=obstmp[sj:ej+1,si:ei+1]
                    print('观测统计：', obs.min(), obs.max())

    ########### read landmask #################################################
                    f = open(maskroot, "rb")
                    gid = eccodes.codes_grib_new_from_file(f)
                    if gid is None:
                        print("create handler error")

                    # load matrix
                    values = eccodes.codes_get_values(gid)
                    masktmp = np.reshape(values, (nj, ni))
                    mask=masktmp[sj:ej+1,si:ei+1]
                    # print('索引',sj,ej,si,ei)
    #################calculation the scores####################################################
                    allmask=mask.copy()
                    fcst[allmask==0]=-999
                    obs[allmask==0]=-999

                    masknan=np.zeros(allmask.shape)
                    masknan[allmask==0.0]=1

                    outputdate=outname_final+str("%03d"%i)+"."+str(obsdate.strftime("%Y%m%d%H"))
                    print('输出文件-->',outputdate)
                    f = open(outputdate, "w")
                    for thr in thresholds:

    ## convert fcst and obs to binary value
                        i_f=(fcst>=thr).astype(float)
                        i_o=(obs>=thr).astype(float)

                        for scale in scales:
    #####################################################################################################################
    ## calculate the ratios in each fractions
    ### s_f is (yes(1))/all
    ### s_fw is (yes(1)+no(0)+nan)/all
    ### s_n is nan/all
    ### so s_fr=s_f/(s_fw-s_n)  that is yes(1)/(yes(1)+no(0))
    ####  along the boundary all>yes+no+nan  #### for uniform_filter (filled with zero)################################## 
    #####################################################################################################################

                            s_f=uniform_filter(i_f,size=scale,mode="constant",cval=0.0)
                            s_o=uniform_filter(i_o,size=scale,mode="constant",cval=0.0)
                            s_fw=uniform_filter(np.ones(i_f.shape),size=scale,mode="constant",cval=0.0)
                            s_ow=uniform_filter(np.ones(i_o.shape),size=scale,mode="constant",cval=0.0)
                            s_n=uniform_filter(masknan,size=scale,mode="constant",cval=0.0)
                            s_fr=s_f/(s_fw-s_n+0.001)
                            s_or=s_o/(s_ow-s_n+0.001)

    ## filter the missing value
                            s_fr[allmask==0.0]=np.nan
                            s_or[allmask==0.0]=np.nan

    ## get results
                            fbs=np.nanmean((s_fr-s_or)**2)
                            fre=np.nanmean(s_fr**2+s_or**2)
                            if fre>0:
                                fss=1-fbs/fre
                                # f.write(str("%3g"%thr)+"  mm  "+str("%3d"%round(scale*resolution*100))+"  km"+"  FSS=  "+str("%.3f"%fss)+"  FBS=  "+str("%.3f"%fbs))
                                f.write(str("%3g"%thr)+"  mm  "+str("%3d"%(scale*resolution*100))+"  km"+"  FSS=  "+str("%.3f"%fss)+"  FBS=  "+str("%.3f"%fbs))
                                f.write(' \r\n')
                            else:
                                fss=-999.0
                                # f.write(str("%3g"%thr)+"  mm  "+str("%3d"%round(scale*resolution*100))+"  km"+"  FSS=  "+str("%.0f"%fss)+"   FBS=  "+str("%.3f"%fbs))
                                f.write(str("%3g"%thr)+"  mm  "+str("%3d"%(scale*resolution*100))+"  km"+"  FSS=  "+str("%.0f"%fss)+"   FBS=  "+str("%.3f"%fbs))
                                f.write(' \r\n')
                            #print('-------->>>>>>>>',fbs,fre)
                            
        cdate=cdate+datetime.timedelta(days=1)

#except:
#    print('no data!!!')

