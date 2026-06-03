
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
import datetime as dt
import multiprocessing
import uniform_decoder
import mh_decoder
import jd_decoder
import numpy as np



class Plev(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "2025010100") # 开始时间
    timedelta: str = Field(descrption = "12")# time step
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    para: str = Field(descrption="u,v,t,r,q,gh,wind,wdir") # 变量，以，分割
    ref : str = Field(descrption="ERA5/SELF/BUFR")  # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    length: str = Field(descrption="21, 21*12=240")#  
     
class Model(BaseModel): # 
    startTime : str =Field(descrption="2025010100")
    para: str =Field(descrption="u,v,gh,r,wind,wdir")
    fstc: str=Field(descrption="KT1279/NCEP/EC/CMAGFS")
    
class Scan(BaseModel): # 
    startTime: str=Field(descrption="2025010100")
    fcst: str=Field(descrption="KT1279/NCEP/EC/CMAGFS")

class Obs(BaseModel):
    startTime: str=Field(descrption="2025010100")

class ObsAir(BaseModel):
    startTime: str=Field(descrption="20250101")
    
class rain_grid_FSS(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "20250101")        # 开始时间
    endTime: str = Field(descrption = "20250103")          # 开始时间
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    level: str = Field(descrption="3,6,12,24")             # 3h累计降水，6h累计降水，...（单选）
    ref : str = Field(descrption="ERA5/CMPAS/CLDAS")       # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    length: str = Field(descrption="10")                  # 评估时间长度
    cycl: str = Field(descrption="00,06,12,18")            # 起报时间（先设置单选）
    half_size: str = Field(descrption="1,2,3,4,5")

class rain_grid_MODE(BaseModel):  # 定义一个类用作参数
    startTime: str = Field(descrption = "20250101")        # 开始时间
    area: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")   # 区域，以，分割
    level: str = Field(descrption="3,6,12,24")             # 3h累计降水，6h累计降水，...（单选）
    ref : str = Field(descrption="ERA5/CMPAS/CLDAS")       # 真值，单选
    fstc: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
    cycl: str = Field(descrption="00,06,12,18")            # 起报时间（先设置单选）
    h_delta: str = Field(descrption="6,12,18")             # 预报时效（自行选择，6,12,18....）
    smooth: str = Field(descrption="1/2/3/4/5")            # 平滑系数
    threshold: str= Field(descrption="1/2/3/4/5")          # 阈值
    minsize: str = Field(descrption="1/2/3/4/5")           # 最小面积


app = FastAPI()


@app.post("/mh_decoder")
async def mh_to_database(obs:ObsAir):
    status = True
    mess = ""
    #stime = dt.datetime.strptime(obs.startTime,"%Y%m%d")
    status,mess = mh_decoder.decoder_main(obs.startTime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }   

@app.post("/jd_decoder")
async def jd_to_database(obs:ObsAir):
    status = True
    mess = ""
    #stime = dt.datetime.strptime(obs.startTime,"%Y%m%d")
    status,mess = jd_decoder.decoder_main(obs.startTime)
    return {
        "method": 'post',
        "status": status,
        "mess": mess
    }  

if __name__ == '__main__':
    import sys
    port = 5300
    cpu_count = 8
    if len(sys.argv) >=2:
        port = int(sys.argv[1])
        print(port)
    config = uvicorn.Config("main-bak:app", workers=cpu_count * 2, limit_concurrency=1000, port=port, host="0.0.0.0")
    server = uvicorn.Server(config)
    server.run()
#    uvicorn.run(app=app, host="0.0.0.0", port=port)
