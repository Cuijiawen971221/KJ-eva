import numpy as np
import os
import subprocess
import sys
from datetime import datetime, timedelta
from read_fss import *
from yunyao_met import *
import base64
from rain_fss_ts_function import *
from mode_function import *

#stime = '20250502'
#etime = '20250512'
#area_ = '6'
#area   = area_.split(",")
#rain_scale = int('24')
#ref = 'ERA5'
#expn = 'NCEP'
#length = int('10')
#cycl = '00'
#half_size = '1,3,5,15,20'
#
#status,mess,fss_result = run_main_fss_(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size)

#status,mess,fss_result = run_main_fss_all(rain_scale,expn,cycl,stime,etime,length,ref,area,half_size)


stime = '20250501'#rain.startTime
area      = '6'#rain.area.split(",")          #: str = Field(descrption="ae990b190a7c4ce9809730ac24428286,xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")  # 区域，以，分割
level     = '6'#rain.level                    #: str = Field(descrption="3,6,12,24")  # 3h累计降水，6h累计降水，...（单选）
ref       = 'ERA5'#rain.ref                      #: str = Field(descrption="ERA5/CMPAS/CLDAS")  # 真值，单选
fstc      = 'NCEP'#rain.fstc                     #: str = Field(descrption="KT1279/NCEP/EC/CMAGFS")  # 预报，单选
cycl      = '00'#rain.cycl                     #: str = Field(descrption="00,06,12,18")  # 起报时间（先设置单选）
h_delta   = '6'#rain.h_delta                  #: str = Field(descrption="6,12,18")  # 预报时效（自行选择，6,12,18....）
smooth    = int('5')              #: str = Field(descrption="1/2/3/4/5")  # 平滑系数
threshold = float('5.5')           #: str = Field(descrption="1/2/3/4/5")  # 阈值
minsize   = int('5')            #: str = Field(descrption="1/2/3/4/5")  # 最小面积
status,mess,mode_result = run_main_mode_(stime, cycl, fstc, ref, level, h_delta, area, smooth, threshold, minsize)
    



