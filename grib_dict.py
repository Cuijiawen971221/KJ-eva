# grib2关键字字典 
# 参数：
# GRIB_paramId: grib2参数id
# GRIB_name: grib2参数名称
# GRIB_unit: grib2参数单位
# GRIB_level: grib2参数层次
# GRIB_time: grib2参数时间
# GRIB_levelType: grib2参数层次类型
# GRIB_levelValue: grib2参数层次值          
# 返回值：
# grib2关键字字典

Grib2KeyDict={
    "tp":{"GRIB_paramId":3059},           #总降水
    "2t":{"GRIB_paramId":167,},           #2m温度
    "2d":{"GRIB_paramId":168,},           #2m露点温度
    "2r":{"GRIB_paramId":260242,},        #2m相对湿度
    "10v":{"GRIB_paramId":166,},          #10m v风速
    "10u":{"GRIB_paramId":165,},          #10m u风速
    "vis":{"GRIB_paramId":3020,},         #能见度
    "sp":{"GRIB_paramId":134}   ,         #海平面气压
    "mslp":{"GRIB_paramId":151},          #海平面气压
    "rad":{"GRIB_paramId":260087},        #地面辐射
    "lcc":{"GRIB_paramId":3073},          #低云量
    "tcc":{"GRIB_paramId":228164},        #总云量
    "ch":{"GRIB_paramId":260011} ,        #云底高
    "t":{"GRIB_paramId":130},             # 等压面温度
    "r":{"GRIB_paramId":157},             # 等压面相对湿度
    "u":{"GRIB_paramId":131},             # 等压面 u风速
    "v":{"GRIB_paramId":132},             # 等压面 v风速
    "gh":{"GRIB_paramId":156},            # 等压面高度
    "q":{"GRIB_paramId":133},             # 等压面比湿

}

# KT1279预报数据字典
KT1279ParamDict={
    "A_PCP_3_SFC":"tp",                   #总降水
    "DPT_3_HTGL":"2d",                    #2m露点温度
    "TMP_3_HTGL":"2t",                    #2m温度
    "U_GRD_3_HTGL":"10u",                 #10m u风速
    "PRMSL_3_MSL":["mslp","/",100],                 #海平面气压
    "V_GRD_3_HTGL":"10v",                 #10m v风速
    "TMP_3_ISBL":"t",                     #等压面温度
    "V_GRD_3_ISBL":"v",                   #等压面 v风速
    "U_GRD_3_ISBL":"u",                   #等压面 u风速 
    "R_H_3_ISBL":"r",                     #等压面相对湿度
    "HGT_3_ISBL":"gh",                    #等压面高度
    "PRES_3_SFC":["sp","/",100],                    #海平面气压
    "R_H_3_HTGL":"2r",                    #2m相对湿度
    "L_CDC_3_SFC":["lcc","*",10],
    "T_CDC_3_SFC":["tcc","*",10],
    "SNO_C_3_SFC":"ch",
    "VIS_3_SFC":"vis",
}

KT1279CLOUDParamDict={
    "L_CDC_3_SFC":"lcc",
    "T_CDC_3_SFC":"tcc",
    "SNO_C_3_SFC":"ch",
}
VISFCSTParamDict={
    "VIS_3_SFC":["vis","*",1000],
}
# NCEP预报数据字典
NCEPParamDict={
    "TMP_P0_L100_GLL0":"t", # 等压面温度
    "PRES_P0_L1_GLL0":["sp","/",100], # 地表气压
    "HGT_P0_L100_GLL0":"gh", # 等压面高度
    "VIS_P0_L1_GLL0":"vis", # 能见度
    "UGRD_P0_L100_GLL0":"u", # 等压面 u风速
    "VGRD_P0_L100_GLL0":"v", # 等压面 v风速
    "RH_P0_L100_GLL0":"r",  # 等压面相对湿度
    "MSLET_P0_L101_GLL0":["mslp","/",100], # 海平面气压
    "UGRD_P0_L103_GLL0": "10u", # 10m u风速
    "VGRD_P0_L103_GLL0": "10v", # 10m v风速
    "TMP_P0_L103_GLL0": "2t", # 2m温度
    "DPT_P0_L103_GLL0": "2d", # 2m露点温度
    "RH_P0_L103_GLL0" :"2r", # 2m相对湿度
    "TCDC_P0_L10_GLL0": ["tcc","/",10], # 总云量
    "LCDC_P0_L214_GLL0":["lcc","/",10], # 低云量
    "DSWRF_P8_L1_GLL0_avg3h":"rad", # 地面辐射
}

# ERA5预报数据字典
ERA5SFCParamDict={
    "SP_GDS0_SFC":["sp","/",100], # 海平面气压
    "MSL_GDS0_SFC":["mslp","/",100], # 海平面气压
    "TCC_GDS0_SFC":"tcc", # 总云量
    "LCC_GDS0_SFC":"lcc", # 低云量
    "10U_GDS0_SFC":"10u", # 10m u风速
    "10V_GDS0_SFC":"10v", # 10m v风速
    "2T_GDS0_SFC":"2t", # 2m温度
    "2D_GDS0_SFC":"2d", # 2m露点温度
    "SSRD_GDS0_SFC_acc1h":["rad","/",3600], # 地面辐射
    "CBH_GDS0_SFC":"ch", # 云底高
}
ERA5ISBLParamDict={
    "T_GDS0_ISBL":"t", # 等压面温度
    "U_GDS0_ISBL":"u", # 等压面 u风速
    "V_GDS0_ISBL":"v", # 等压面 v风速
    "Q_GDS0_ISBL":"q", # 等压面比湿
    "R_GDS0_ISBL":"r", # 等压面相对湿度
    "Z_GDS0_ISBL":["gh","/",9.8] # 等压面高度
}

# ECMWF地面数据字典
ECMWFSFCParamDict={
    "MSL_GDS0_SFC":["mslp","/",100], # 海平面气压
    "SP_GDS0_SFC":["sp","/",100], # 海平面气压
    "TCC_GDS0_SFC":["tcc","*",10], # 总云量
    "LCC_GDS0_SFC":["lcc","*",10], # 低云量
    "2T_GDS0_SFC":"2t", # 2m温度
    "2D_GDS0_SFC":"2d", # 2m露点温度
    "10U_GDS0_SFC":"10u", # 10m u风速
    "10V_GDS0_SFC":"10v", # 10m v风速
}

# ECMWF等压面数据字典
ECMWFISBLParamDict={
    "GH_GDS0_ISBL":"gh", # 等压面高度
    "R_GDS0_ISBL":"r", # 等压面相对湿度
    "T_GDS0_ISBL":"t", # 等压面温度
    "U_GDS0_ISBL":"u", # 等压面 u风速
    "V_GDS0_ISBL":"v", # 等压面 v风速
    "Q_GDS0_ISBL":"q", # 等压面比湿
}

# CLDAS数据字典
CLDASParamDict={
#    "SWDN":"rad", # 2m相对湿度
    "TAIR":"2t", # 2m温度
    "UWIN":"10u", # 10m u风速
    "VWIN":"10v", # 10m v风速
    "DAIR":"2d", # 2m 露点温度
    "PAIR":["sp","/",100], # 地表气压
    
}

# REGION数据字典
REGIONParamDict={
#    "SWDN":"rad", # 2m相对湿度
    "CBH":"ch", 
    "LCC": ["lcc","/",10],
    "RH2":"2r", 
    "RHU":"r", 
    "SRP":["mslp","/",100], # 地表气压
    "T2M": ["2t","+", 273.15],
    "TD2": ["2d","+", 273.15],
    "TEM": ["t","+",273.15],
    "UWND": "u",
    "VWND": "v",
    "VIS": "vis",
    "GPH": "gh",
    "10U":"10u",
    "10V":"10v",
    #"D10": "wdir",
    #"W10": "wind",
}

# regionH数据字典（参考REGION，去掉SRP）
KJRHParamDict={
    "CBH":"ch",
    "LCC": ["lcc","/",10],
    "RH2":"2r",
    "RHU":"r",
    "T2M": "2t",
    "TD2": "2d",
    "TEM": "t",
    "UWND": "u",
    "VWND": "v",
    "VIS": "vis",
    "GPH": "gh",
    "10U":"10u",
    "10V":"10v",
}

# REGION2数据字典
REGIONTMPParamDict={

    #"CBH":"ch", 
    "L_CDC_3_SFC": ["lcc","*",10],
    "R_H_3_HTGL":"2r", 
    "R_H_3_ISBL":"r", 
    #"PRES_3_SFC": ["sp","/",100],
    "PRMSL_3_MSL":["mslp","/",100], # 地表气压
    "TMP_3_HTGL": "2t",
    "DPT_3_HTGL": ["2d","+", 273.15],
    "TMP_3_ISBL": "t",
    "U_GRD_3_ISBL": "u",
    "V_GRD_3_ISBL": "v",
    "VIS_3_SFC": ["vis","*",1000.0],
    "HGT_3_ISBL": "gh",
    "U_GRD_3_HTGL":"10u",
    "V_GRD_3_HTGL":"10v",
    #"D10": "wdir",
    #"W10": "wind",
}

################
AUTOParamDict={
    "VIS_GDS0_SFC":"vis",
    "MSLMA_GDS0_ISBL":["gh","/",9.8],
    "NBDSF_GDS0_SFC":"2d",
    "ICNG_GDS0_SFC":["lcc","*",10],
    "COVTZ_GDS0_SFC":["mslp","/",100],
    "S_X_GDS0_SFC":["sp","/",100],
    "CAPE_GDS0_ISBL":"r",
    #"NDDSF_GDS0_SFC":"rad",
    "VDDSF_GDS0_SFC":"2t",
    "CFNSF_GDS0_SFC":["tcc","*",10],
    "MSLET_GDS0_ISBL":"t",
    "CFNLF_GDS0_SFC":"10u",
    "LFT_X_GDS0_ISBL":"u",
    "VBDSF_GDS0_SFC":"10v",
    "4LFTX_GDS0_ISBL":"v",
    "RDSP3_GDS0_SFC": "ch"
}

CMAGFSParamDict={
    "TMP_P0_L100_GLL0": "t",
    "TMP_P0_L103_GLL0": "2t",
    "RH_P0_L100_GLL0":"r",
    "RH_P0_L103_GLL0": "2r",
    "UGRD_P0_L100_GLL0":"u",
    "UGRD_P0_L103_GLL0":"10u",
    "VGRD_P0_L100_GLL0":"v",
    "VGRD_P0_L103_GLL0":"10v",
    "PRES_P0_L1_GLL0": ["sp","/",100],
    "PRMSL_P0_L101_GLL0": ["mslp","/",100],
    "HGT_P0_L100_GLL0": "gh",
}

CLIMATEParamDict={
    "TREFHT":"2t",
    "U10":"10u",
    "V10":"10v",
    "PS":["sp","/",100],
} 


######################
grib2io_ground_shortName={
#   para  grib2io_param grib2io_param_level ,gribio_typeoffirstfixedsurface
    "2t":["TMP","2 m above ground", 103],
    "2d":["DPT","2 m above ground", 103],
    "2r":["RH","2 m above ground", 103],
    "10u":["UGRD","10 m above ground", 103],
    "10v":["VGRD","10 m above ground", 103],
    "wind":["WIND","10 m abover ground",103],
    "wdir":["WDIR","10 m abover ground",103],
    "vis":["VIS","surface",1],
    "sp":["PRES","surface",1],
    "mslp":["PRES","mean sea level",101],
    "tcc":["TCDC","reserved",1],
    "lcc":["LCDC","surface",1],
    "ch":["SNOC","surface",1],
    "rad":["DSWRF","surface",1],
    "gh":["HGT","isobaric surface",100],
    "u":["UGRD","isobaric surface",100],
    "v":["UGRD","isobaric surface",100],
    "t":["TMP","isobaric surface",100],
    "r":["RH","isobaric surface",100],
    "rain24":["PRATE","surface",1],
}
