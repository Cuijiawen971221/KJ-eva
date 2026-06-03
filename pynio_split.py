import typing as T
import numpy as np
import pandas as pd
import xarray as xr
from cfgrib import xarray_to_grib
import datetime as dt
import dask
import glob
import grib_dict
import xesmf as xe


#    ds_out_05 = xr.Dataset(
#        {
#            "latitude": (["latitude"], np.arange(-90, 90.5,0.5)),
#            "longitude": (["longitude"], np.arange(0, 360, 0.5)),
#        }
#    )
#    ds_out_15 = xr.Dataset(
#        {
#            "latitude": (["latitude"], np.arange(90, -90.5, -1.5)),
#            "longitude": (["longitude"], np.arange(0, 360, 1.5)),
#        }
#    )


# 将pynio读取的数据转化为grib2文件
# 参数：

# pynioDataset: pynio读取的数据
# outPath: 输出路径
# keyDict: 数据名称与grib2关键字对应字典
# gribDict: 数据名称与grib2参数对应字典
# Pscale: 压力缩放因子


def dataset_to_grib(pynioDataset,keyDict,gribDict,Pscale=1.0):
    # 创建一个空的xr.Dataset
    tmpDataSet = xr.Dataset()
    ## 


    # 遍历pynioDataset中的每个数据
    for pynioDataName in pynioDataset:
        # 初始化scale和operator
        scale = 0
        operator = None
        # 如果数据名称不在keyDict中，则跳过
        if pynioDataName not in keyDict.keys():
            continue
        else:
            if type(keyDict[pynioDataName]) == list: 
                keyDictKey = keyDict[pynioDataName][0]
                operator = keyDict[pynioDataName][1]
                scale = keyDict[pynioDataName][2]
            else:
                keyDictKey = keyDict[pynioDataName]

            toGribKeys = [keyDictKey, gribDict[keyDictKey]]

        # 获取数据
        param = pynioDataset[pynioDataName]

        # 获取数据维度
        paramDims = pynioDataset[pynioDataName].dims
        tmpCoords = [[] for _ in range(len(paramDims))]
        tmpDims = [[] for _ in range(len(paramDims))]
        # 遍历数据维度
        
        for dim in param.dims:
            # 如果维度是纬度
            if "lat" in dim or "LAT"  in dim:
                lat = param[dim]
                tmpCoords[-2]=lat.values
                tmpDims[-2]="latitude"
            if "lon" in dim or "LON" in dim:
                lon = param[dim]
                tmpCoords[-1]=lon.values
                tmpDims[-1]="longitude"
            # 如果维度是等压面
            if "ISB" in dim:
                # 使用sel提取子集
          
                param = param.sel({dim:[int(PP*Pscale) for PP in [925,850,700,500,200]]})
                ISB = param[dim]
                ISB_VALUE = ISB.values /Pscale
                tmpCoords[-3]=ISB_VALUE.tolist()
                tmpDims[-3]="isobaricInhPa"
                        # 如果维度是等压面
            if "tmppress" in dim:
                print(param[dim])
                param = param.sel({dim:[int(PP*Pscale) for PP in [925,850,700,500,200]]})
                pres = np.array(param[dim].values)
                pres /= Pscale
                tmpCoords[-3] = pres.tolist()
                tmpDims[-3]="isobaricInhPa"
            if "pressure" in dim:
                print(param[dim])
                param = param.sel({dim:[int(PP*Pscale) for PP in [925,850,700,500,200]]})
                pres = param[dim]
                
                print('01-debug==>>>>',pres)
                
                try:
                    pres.values /= Pscale
                    tmpCoords[-3] = pres.values.tolist()
                except:
                    pres_values = np.array(pres)
                    pres_values /= Pscale
                    tmpCoords[-3] = pres_values.tolist()  
                tmpDims[-3]="isobaricInhPa"
            # 如果维度是高度
            if "lv_HTGL7" in dim:
                param = param.sel(lv_HTGL7=[10])
                HGT = param[dim]
                tmpCoords[-3]=HGT.values.tolist()
                tmpDims[-3]="heightAboveGround"
            # 如果维度是高度
            if "lv_HTGL2" in dim:
                param = param.sel(lv_HTGL2=[2.0])
                HGT = param[dim]
                tmpCoords[-3]=HGT.data.tolist()
                tmpDims[-3]="surface"
        # 对数据进行scale和operator操作
        # 如果operator不为空，则进行scale和operator操作
        # 主要是为了将数据转换为grib2文件的单位
        if operator is not None:
            if operator == "+":
                param.values = param.values+scale
            elif operator == "/":
                param.values = param.values/scale   
            elif operator == "*":
                param.values = param.values*scale
            elif operator == "-":
                param.values = param.values-scale
        # 将数据转换为xr.DataArray
        tmpDataArray=xr.DataArray(
            param.values, coords=tmpCoords, dims = tmpDims
        )
        # 遍历grib2关键字
        for attr in toGribKeys[1].keys():
            tmpDataArray.attrs[attr] = toGribKeys[1][attr]

        # 设置预报时间
        if "initial_time" in param.attrs: 
            tmpDataArray.coords["time"] = dt.datetime.strptime(param.attrs["initial_time"],"%m/%d/%Y (%H:%M)")
        # 合并数据
        tmpDataSet = xr.merge([tmpDataSet,tmpDataArray.to_dataset(name=keyDictKey)],compat='override')

    # 创建一个xr.Dataset
    outGrib = xr.Dataset(tmpDataSet)
    outGrib.attrs["GRIB_centre"]="rjtd"
    outGrib.attrs["edition"]=2
    # 将xr.Dataset转换为grib2文件
    return outGrib
    #xarray_to_grib.canonical_dataset_to_grib(outGrib,outPath)


#pynio_data = xr.open_mfdataset("/home/devopler/workshop/met_backend/orig/KT1279/2025042000/KTR2*G2025042000-006.grb",engine="pynio") # 
#data  = dataset_to_grib(pynio_data,grib_dict.KT1279ParamDict,grib_dict.Grib2KeyDict)
#xarray_to_grib.to_grib(data,"aaaaaa.grib")


#pynio_data = xr.open_dataset("/home/devopler/workshop/met_backend/orig/ERA5/plev/ERA5_plev.grib"+".grib",engine="pynio")
#data= dataset_to_grib(pynio_data,grib_dict.ERA5ISBLParamDict,grib_dict.Grib2KeyDict,1)
#xarray_to_grib.to_grib(data,"aaaaaa.grib")

#pynio_data = xr.open_dataset("/home/devopler/workshop/met_backend/orig/NCEP/20250501/W_NAFP_C_KWBC_20250501233010_P_gfs.t18z.pgrb2.0p50.f153.bin.grib",engine="pynio")

#data = dataset_to_grib(pynio_data,grib_dict.NCEPParamDict,grib_dict.Grib2KeyDict,100)
#xarray_to_grib.to_grib(data,"ncep_test.grib")


#pynio_data = xr.open_dataset("/home/devopler/workshop/met_backend/orig/ECMWF/2025050100/W_NAFP_C_ECMF_20250501050643_P_C1D05010000050100001.grib",engine="pynio")
#dataset_to_grib(pynio_data,"ecmwf.grib",grib_dict.ECMWFISBLParamDict,grib_dict.Grib2KeyDict)


#pynio_data = xr.open_mfdataset("/home/devopler/workshop/met_backend/orig/CLDAS/20250501/Z_NAFP_C_BABJ_*HOR-*-2025050123.GRB2",engine="pynio") # 
#print(pynio_data)
#dataset_to_grib(pynio_data,"cldas.grib",grib_dict.CLDASParamDict,grib_dict.Grib2KeyDict)
