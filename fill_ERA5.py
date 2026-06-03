import subprocess 
import numpy as np
import argparse
import xarray as xr 
import shutil
import config
import os 
import glob 
import datetime 


parser = argparse.ArgumentParser(description="ERA5 utils")
#
parser.add_argument("--input","-i",help="input file",required=True)
parser.add_argument("--output","-o",help="output file",required=True)
parser.add_argument("--type","-t",help="type, == plev or sfc",required=True)
#
args = parser.parse_args()
path = config.ymlConf.era5fcstpath+"/ERA5/"+args.type
tmpPath = path+"/tmp__/"

if args.type == "plev":
    fnmod = "ERA5_plev_{:s}000.grib"
elif args.type == "sfc":
    fnmod = "ERA5_sfc_{:s}000.grib"
#
if os.path.exists(tmpPath):
    shutil.rmtree(tmpPath)

os.makedirs(tmpPath) 
##### split time ######
subprocess.check_call("cdo splitsel,1 {:s} {:s}".format(args.input,tmpPath+args.output),shell = True)
##### remove file and move to right place##################
filel = glob.glob(tmpPath+args.output+"*.grb")
for fl in filel:
    if args.type=="sfc":
        data = xr.open_dataset( fl,    backend_kwargs={  "filter_by_keys": {    "shortName": "2t"}})
    else:    
        data = xr.open_dataset(fl)
    time = datetime.datetime.utcfromtimestamp(data.time.values.astype(int)/10e8)
    os.makedirs(path+"/{:s}/".format(time.strftime("%Y%m%d")),exist_ok=True)
    shutil.move(fl, path+"/{:s}/".format(time.strftime("%Y%m%d"))+"/"+fnmod.format(time.strftime("%Y%m%d%H")))
  
if os.path.exists(tmpPath):
    shutil.rmtree(tmpPath)
    
