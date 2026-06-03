import xarray as xr
import json
import datetime
import glob
from grid_proc import config_path
import traceback 


def read_wind_from_grib(fcst, startTime, timedelta=12, level_type="surface", level_value=10, output_json_path=None):

    """
    读取指定模式、起报时间和时效的GRIB文件中的风场数据，并转换为JSON格式
    
    参数:
    fcst (str): 模式名称，如'AUTO'
    startTime (datetime.datetime): 起报时间，包含日期和批次
    timedelta (int): 时效，从0开始的小时数，默认12
    level_type (str): 层次类型，可选："surface"(地面), "pressure"(等压面)
    level_value (int): 层次值，对于地面是高度(米)，对于等压面是气压值(百帕)
    output_json_path (str): 输出JSON文件路径，如果为None则不保存文件
    
    返回:
    list: 包含风场数据的字典列表
    """
    status = True
    mess = ""
    result = []

    try:
        outputroot,fcstroot,toolspath,weight = config_path(fcst)
        # 解析起报时间
        YYYYMMDD = startTime.strftime("%Y%m%d")
        HH = startTime.strftime("%H")
        # 时效格式化为3位数字
        fhh = f"{timedelta:03d}"
        # 构建文件路径
        file_pattern = f"{fcstroot}/{fcst}/normal/{YYYYMMDD}/prs{YYYYMMDD}{HH}{fhh}.grib"
        
        # 查找匹配的GRIB文件
        grib_files = glob.glob(file_pattern)
        if not grib_files:
            mess = f"未找到匹配的GRIB文件: {file_pattern}"
            status = False
            return status,mess,result
        
        # 根据层次类型设置过滤条件
        filter_params = {}
        if level_type == "surface":
            # 地面风场，通常是10米高度
            filter_params = {'typeOfLevel': 'heightAboveGround', 'level': level_value}
            u_name, v_name = 'u10', 'v10'
        elif level_type == "pressure":
            # 等压面风场，如500hPa、850hPa等
            filter_params = {'typeOfLevel': 'isobaricInhPa', 'level': level_value}
            u_name, v_name = 'u', 'v'
        else:
            mess = f"不支持的层次类型: {level_type}"
            status = False
            return status,mess,result
        
        # 打开GRIB文件并过滤指定层次
        ds = xr.open_dataset(grib_files[0], engine='cfgrib', 
                            backend_kwargs={'filter_by_keys': filter_params})
        
        # 提取u和v数据
        try:
            u_data = ds[u_name]
            v_data = ds[v_name]
        except KeyError as e:
            mess = f"在GRIB文件中找不到变量: {e}"
            status = False
            return status,mess,result
        
        # 获取经纬度坐标
        lons = u_data.longitude.values
        lats = u_data.latitude.values
        
        # 遍历所有网格点
        for i in range(len(lats)):
            for j in range(len(lons)):
                # 获取当前点的u和v值
                u_val = float(u_data.values[i, j])
                v_val = float(v_data.values[i, j])
                
                # 添加到结果列表
                result.append({
                    "lon": float(lons[j]),
                    "lat": float(lats[i]),
                    "u": u_val,
                    "v": v_val
                })
        
        # 如果指定了输出路径，保存为JSON文件
        if output_json_path:
            with open(output_json_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"成功转换数据并保存到: {output_json_path}")
        
        return status,mess,result

        
    except Exception as e:
        traceback.print_exc()
        print(f"处理过程中出错: {str(e)}")
        status = False
        mess = str(e)
        return status,mess,[]

# 使用示例
if __name__ == "__main__":
    # 设置参数
    fcst = "AUTO"
    startTime = datetime.datetime(2025, 8, 15, 0)  # 2025年8月15日00时
    timedelta = 12  # 12小时时效
    
    # 读取地面10米风场
    print("读取地面10米风场:")
    surface_wind = read_wind_from_grib(fcst, startTime, timedelta, "surface", 10, "surface_wind.json")

    print(f"共读取 {len(surface_wind)} 个点的数据")
    
    # 读取500hPa等压面风场
    print("\n读取500hPa等压面风场:")
    pressure_wind = read_wind_from_grib(fcst, startTime, timedelta, "pressure", 500, "pressure_500_wind.json")

    print(f"共读取 {len(pressure_wind)} 个点的数据")
    
