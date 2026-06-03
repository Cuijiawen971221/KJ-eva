import numpy as np
import eccodes
from scipy.ndimage.filters import uniform_filter 
from nwpc_data.grib.eccodes import load_message_from_file
import datetime
import os
import sys
########################dirroot##################################
def run_main_rain24_grid(time,fcstroot,obsroot,maskroot,outputroot,starttime_str,endtime_str,lonst,loned,latst,lated,half_size_str,FCST_path,grid_file,cdo_path):
    time         = int(time)
    half_size    = np.array(list(map(int, half_size_str.split(','))))
    starttime    = datetime.datetime(int(starttime_str[0:4]),int(starttime_str[4:6]),int(starttime_str[6:8]),time)   # YYYY-MM-DD-HH of starttime
    endtime      = datetime.datetime(int(endtime_str[0:4]),int(endtime_str[4:6]),int(endtime_str[6:8]),time)     # YYYY-MM-DD-HH of endtime
    lonst        = float(lonst)
    loned        = float(loned)
    latst        = float(latst)
    lated        = float(lated)
    print('开始时间：',starttime)
    print('结束时间：',endtime)
    domain=[latst,lated,lonst,loned]
    scales=half_size
    thresholds=[0.1,10,25,50,100,250]#[0.1,1,5,10,25,50,100]
    if time == 0:
        testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'024.grb'
    elif time == 12:
        testfile=fcstroot+'fcst'+str(starttime.strftime("%Y%m%d%H"))+'036.grb'
    ## get info from info_file
    info_file = FCST_path+'/info.grb'
    os.chdir(cdo_path)
    cmd1 = f"./cdo remapbil,{grid_file} {testfile} {info_file}"
    os.system(cmd1)
    try:
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
        elon = eccodes.codes_get(gid, 'longitudeOfLastGridPointInDegrees')
        #print('预报数据',slat,elat,slon,elon,domain)
        cdate=starttime
        while cdate<=endtime:
            obsdate=cdate-datetime.timedelta(hours=time)
            for i in range(24+time,240+24,24):
                ccdate=obsdate-datetime.timedelta(hours=i)
	#######################read fcst in the first time step#######################		        		
                fcstdate1=fcstroot+'fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grb"
                fcstdate_new = FCST_path+'/fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grb"
                os.chdir(cdo_path)
                cmd2 = f"./cdo remapbil,{grid_file} {fcstdate1} {fcstdate_new}"
                os.system(cmd2)

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
                            level=0,
                              )
                        fcst1=eccodes.codes_get_double_array(t, "values")
                    fcst1=fcst1.reshape([nj, ni])
                    if slat > elat:
                        sj = int((slat - domain[1]) / resolution)
                        ej = int((slat - domain[0]) / resolution)
                    else:
                        sj = int((domain[0] - slat) / resolution)
                        ej = int((domain[1] - slat) / resolution)
                    si=int((domain[2] - slon) / resolution)
                    ei=int((domain[3] - slon) / resolution)
                    print('>>>>>>>>>>>>>',nj,ni,'<<<<<<<<<<<<<<',sj,ej,si,ei)
	########### read fcst in the second time step#######################
				# fcstdate2=fcstroot+'fcst'+str(ccdate.strftime("%Y%m%d%H"))+str("%03d"%(i))+".grib"
                    fcst1[fcst1<0] = 0
                    fcsttmp=fcst1
                    fcst=fcsttmp[sj:ej+1,si:ei+1]
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
                        obs=obstmp[sj:ej+1,si:ei+1]

	########### read landmask #################################################
                        f = open(maskroot, "rb")
                        gid = eccodes.codes_grib_new_from_file(f)
                        if gid is None:
                            print("create handler error")
        # load matrix
                        values = eccodes.codes_get_values(gid)
                        masktmp = np.reshape(values, (nj, ni))
                        mask=masktmp[sj:ej+1,si:ei+1]
	#################calculation the scores####################################################

                        allmask=mask.copy()
                        fcst[allmask==0]=-999
                        obs[allmask==0]=-999

                        masknan=np.zeros(allmask.shape)
                        masknan[allmask==0.0]=1
                        outputdate=outputroot+str("%03d"%i)+"."+str(obsdate.strftime("%Y%m%d%H"))
                        f = open(outputdate, "w")
                        f.write("           AA      BB     CC      DD")
                        f.write(' \r\n')
                        for thr in thresholds:
                            aa=0
                            bb=0
                            cc=0
                            dd=0
                            for iin in range(0,ei-si+1):
                                for jjn in range(0,ej-sj+1):
                                    if fcst[jjn,iin]>=thr and obs[jjn,iin]>=thr:
                                        aa+=1
                                    if fcst[jjn,iin]>=thr and obs[jjn,iin]>=0 and obs[jjn,iin]<thr:
                                        bb+=1
                                    if obs[jjn,iin]>=thr and fcst[jjn,iin]>=0 and fcst[jjn,iin]<thr:
                                        cc+=1
                                    if fcst[jjn,iin]>=0 and fcst[jjn,iin]<thr and obs[jjn,iin]>=0 and obs[jjn,iin]<thr:
                                        dd+=1
                            f.write(str("%3g"%thr)+"  mm  "+str("%9d"%aa)+str("%9d"%bb)+str("%9d"%cc)+str("%9d"%dd))
                            f.write(' \r\n')
            cdate=cdate+datetime.timedelta(days=1)
    except Exception as e:
        if isinstance(e,KeyboardInterrupt):
            raise
        else:
            print(f"error is {e}")
    # except KeyboardInterrupt:
    #    print('user kill it!!!')

