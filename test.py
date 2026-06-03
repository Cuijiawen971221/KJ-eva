# -*- coding: utf-8 -*-
import time
import requests
import datetime as dt 

def test_airport():
    now = dt.datetime.strptime("2025050100","%Y%m%d%H")
    for i in range(1):
        params = {"startTime": now.strftime("%Y%m%d%H"),"fstc":"NCEP","para":"2t,2d,10u,10v,sp,mslp,vis,tcc,lcc,ch,rad"
            }
        start_time = time.time()  # 开始时间
        dd = requests.post("http://0.0.0.0:5400/airport_model_single", json=params)
        end_time = time.time()  # 结束时间
        print('返回:', dd.text)
        print("运行时长:" + str((end_time - start_time)))  # 结束时间-开始时间
        now = now + dt.timedelta(hours=12)

def test_data():
    now = dt.datetime.strptime("2025080700","%Y%m%d%H")
    params = {"startTime": now.strftime("%Y%m%d%H"),"fcst":"AUTO"
        }
    start_time = time.time()  # 开始时间
    dd = requests.post("http://127.0.0.1:5400/scan_orig_fcst", json=params)
    end_time = time.time()  # 结束时间
    print('返回:', dd.text)
    print("运行时长:" + str((end_time - start_time)))  # 结束时间-开始时间

def test_grid():
    now = dt.datetime.strptime("2025070100","%Y%m%d%H")
    for i in range(1):
        params = {"startTime":now.strftime("%Y%m%d%H"),"fstc":"AUTO","para":"u,v,gh"}
        start_time = time.time()  # 开始时间
        dd = requests.post("http://0.0.0.0:5400/grid_model", json=params)
        print(dd.text)
        now = now + dt.timedelta(hours=24)
        end_time = time.time()  # 结束时间
        print('返回:', dd.text)
        print("运行时长:" + str((end_time - start_time)))  # 结束时间-开始时间

def test_dm():
    now = dt.datetime.strptime("2025050100","%Y%m%d%H")
    for i in range(60):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
                "timedelta":"3",
                "area":"5,6,7,8,9",
                "para":"2t,2d,2r,wind,wdir,sp,mslp,rad,vis,tcc,lcc,ch",
                #"para":"wind",
                "ref":"AWS",
                "fstc":"KT1279",
                "length":"21"}
        dd = requests.post("http://0.0.0.0:5600/dm_single", json=params)
        print(dd.text)
        now = now + dt.timedelta(hours=12)

def test_dm_ll():
    now = dt.datetime.strptime("2025050506","%Y%m%d%H")
    for i in range(1):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
                "timedelta":"6",
                "area":"5,6,7,8,9",
                "para":"2t,2d,2r,wind,wdir,sp,mslp,rad,vis,tcc,lcc,ch",
                #"para":"wind",
                "ref":"AWS",
                "fstc":"CMA_GFS",
                "length":"41"}
        dd = requests.post("http://0.0.0.0:5200/dm_single_parallel", json=params)
        print(dd.text)
        now = now + dt.timedelta(hours=12)


def test_data1():
    now = dt.datetime.strptime("2025050500","%Y%m%d%H")
    for i in range(1):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
                "timedelta":"12",
                "area":"5,6,7,8,9",
                "para":"t,gh,r,wind,wdir",
                "ref":"BUFR",
                "fstc":"NCEP",
                "length":"21",
                }
        start_time = time.time()  # 开始时间
        
        dd = requests.post("http://0.0.0.0:5400/gk_single", json=params)

        end_time = time.time()  # 结束时间
        print('返回:', dd.text)
        print("运行时长:" + str((end_time - start_time)))  # 结束时间-开始时间
        now = now+dt.timedelta(hours=12)

def test_station():
    dd = requests.post("http://0.0.0.0:5400/save_station")
    print('返回:', dd.text)
    
def test_area():
    dd = requests.post("http://0.0.0.0:5400/save_area")
    print('返回:', dd.text)

def test_syno():
    now = dt.datetime.strptime("2025081500","%Y%m%d%H")
    for i in range(1):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
                "para": "r",
                "fstc": "AUTO",
                "level":"50000",
                "fh":"0,48"
        }
	
        start_time = time.time()  # 开始时间
        
        dd = requests.post("http://0.0.0.0:5400/syno",json=params)

        end_time = time.time()  # 结束时间


def test_gts():
    now = dt.datetime.strptime("2025050112","%Y%m%d%H")
    for i in range(10):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
        }
        start_time = time.time()  # 开始时间
        
        dd = requests.post("http://0.0.0.0:5400/gts_decoder", json=params)

        end_time = time.time()  # 结束时间
        print('返回:', dd.text)
        print("运行时长:" + str((end_time - start_time)))  # 结束时间-开始时间
        now = now+dt.timedelta(hours=24)

def test_syno_feature():
    now = dt.datetime.strptime("2025081500","%Y%m%d%H")
    for i in range(1):
        params={
                "startTime":now.strftime("%Y%m%d%H"),
                "para": "fugao",
                "fstc": "AUTO",
                "level":"50000",
                "fh":"0,120"
        }

        start_time = time.time()  # 开始时间

        dd = requests.post("http://0.0.0.0:5200/syno_feature",json=params)

        end_time = time.time()  # 结束时间

test_dm_ll()

