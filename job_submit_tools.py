import os
import numpy as np
import datetime as dt
import sys
import argparse
import glob
import config as cf

globalConf = cf.pparms("./pathconfig.yaml").param

parser = argparse.ArgumentParser(description="create job utils")

parser.add_argument("--startTime","-s",help="开始时间",required=True)
parser.add_argument("--endTime","-e",help="结束时间",required=True)
parser.add_argument("--delta","-dt",help="时间间隔",required=True)
parser.add_argument("--fcst","-fc",help="预报类型",required=True)
parser.add_argument("--force","-ff",action="store_true",default=False)
parser.add_argument("--kind","-k",help="retry_head",required=False)
parser.add_argument("--setok","-ok",action="store_true",default=False)
parser.add_argument("--query","-q",action="store_true",default=False)
parser.add_argument("--type","-t",help="是否为降水")

args= parser.parse_args()

startTime = dt.datetime.strptime(args.startTime,"%Y%m%d%H")
endTime = dt.datetime.strptime(args.endTime,"%Y%m%d%H")

dtt = int(args.delta)
lfcst = args.fcst.split(",")

kind = args.kind  if args.kind != None else ""
if args.type == "RAIN":
    filePath = globalConf.message_rain
else:
    filePath = globalConf.message

tgT = startTime
###########################################
if endTime<startTime:
    raise "startTime must less than endTime"
###########################################
if args.setok :
    todo = "ok"
else:
    todo = "retry"
##########################################

joblist=  {}
for fcst in lfcst:
    joblist[fcst]={}

###########################################
while(tgT<endTime and tgT< dt.datetime.now()):
    for fcst in lfcst:
        querytgT = tgT - dt.timedelta(hours=tgT.hour)
        if querytgT not in joblist[fcst].keys():
            joblist[fcst][querytgT]=[" " for jj in range(24//dtt)]
        if args.query:
            for filen in glob.glob(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.{todo}"):
                joblistTime = dt.datetime.strptime(filen.split("/")[-1],f"{kind}{fcst}_%Y%m%d%H.{todo}")
                jobHH = joblistTime.hour
                joblistTime = joblistTime-dt.timedelta(hours=jobHH)
                joblist[fcst][joblistTime][jobHH//dtt]="*"*4
            continue

        if not os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/"):
            os.makedirs(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/")
        if not os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.ok") and not args.force:
            with open(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.{todo}","w") as f:
                pass
        else:
            if args.force:
                if os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.ok"):
                    os.remove(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.ok")
                if os.path.exists(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.retry"):
                    os.remove(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.retry")
                with open(filePath+f"/{fcst}/{tgT.strftime('%Y%m%d')}/{kind}{fcst}_{tgT.strftime('%Y%m%d%H')}.{todo}","w") as f:
                    pass
            else:
                pass
        
                #print(tgT," is OK")

    tgT = tgT+dt.timedelta(hours=dtt)

if args.query:
    for fcst  in lfcst:
        print(f"↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓    {fcst}      ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓")    
        if args.setok:
            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            print("xxxxxxxxxxxxxxxxxxxxxxxxx  JOB FINISH  xxxxxxxxxxxxxxxxxxxx")
            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        else:
            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            print("xxxxxxxxxxxxxxxxxxxxxxxxx  JOB QUERY   xxxxxxxxxxxxxxxxxxxx")
            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        
        print("     JOB TIME       {:s}".format("".join(["|{:^8d}|".format(ii*dtt) for ii in range(24//dtt) ])))
        for job in joblist[fcst].keys():
            print(job,''.join(["|{:^8s}|".format(qj) for qj in  joblist[fcst][job]]))
        print("↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑")
