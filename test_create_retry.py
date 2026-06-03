import os
import numpy as np
import datetime as dt
import sys
import argparse

parser = argparse.ArgumentParser(description="create job utils")

parser.add_argument("--startTime","-s",help="开始时间",required=True)
parser.add_argument("--endTime","-e",help="结束时间",required=True)
parser.add_argument("--delta","-dt",help="时间间隔",required=True)
parser.add_argument("--fcst","-fc",help="预报类型",required=True)
parser.add_argument("--force","-ff",action="store_true",default=False)

args= parser.parse_args()
startTime = dt.datetime.strptime(args.startTime,"%Y%m%d%H")
endTime = dt.datetime.strptime(args.endTime,"%Y%m%d%H")
dtt = int(args.delta)
fcst = args.fcst
filePath = "/vol8/home/kongjun/VERIFY/met/met_backend/mess/"
tgT = startTime
if endTime<startTime:
    raise "startTime must less than endTime"

while(tgT<endTime and tgT< dt.datetime.now()):
    tgT = tgT+dt.timedelta(hours=dtt)
    if not os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/"):
        os.makedirs(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/")
    if not os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{fcst}_{tgT.strftime('%Y%m%d%H')}.ok"):
        with open(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{fcst}_{tgT.strftime('%Y%m%d%H')}.retry","w") as f:
            pass
    else:
        if args.force:
            os.remove(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{fcst}_{tgT.strftime('%Y%m%d%H')}.ok")
            with open(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{fcst}_{tgT.strftime('%Y%m%d%H')}.retry","w") as f:
                pass
        else:
            print(tgT," is OK")
