from re import X
from termios import FF1
from webbrowser import get
import matplotlib.pyplot as plt 
from matplotlib.path import Path
import numpy as np
from matplotlib import collections as mc
import ujson
import geojson
import xarray as xr
import grib_dict
from skimage import data, filters
import cartopy.crs as ccrs
import os
from geojson import Feature, FeatureCollection, LineString
import datetime
import json
from typeguard import typechecked
from typing import List, Dict, Tuple, Optional
from grid_proc import config_path 
import glob
from shapely.geometry import Polygon as ShapelyPolygon  # 用于面积计算
from shapely.validation import make_valid  # 处理无效几何
from config import ymlConf
from scipy.ndimage import gaussian_filter
import pygrib
import logging
from clickhouse_util import clickclient 
import pandas as pd
#import geojson_gen_polygon
import geojsoncontour
import geojson_gen_polygon_high
from scipy import interpolate

# 全局配置（新增闭环过滤参数）
WEB_MERC_MIN_LAT = -85.05112877980659
WEB_MERC_MAX_LAT = 85.05112877980659
COORD_PRECISION = 2  # 坐标精度，保留小数点后两位
MIN_CLOSED_AREA = 0.01  # 最小闭环面积阈值（单位：平方度），小于此值的闭环会被过滤
VALID_LAT_MIN = -85.1
VALID_LAT_MAX = 85.1

paramLevels={
    "gh":{50000:np.arange(0,6000,40),
          92500:np.arange(0,1200,20),
          85000:np.arange(0,3000,40),
          70000:np.arange(0,6000,40),
          20000:np.arange(6000,13000,80),
    },
    "t":{
        20000:np.arange(-100,40,1),
        50000:np.arange(-100,40,1),
        70000:np.arange(-100,40,1),
        85000:np.arange(-100,40,1),
        92500:np.arange(-100,40,1),
        99999:np.arange(-100,40,1),
    },
    "r":{
        20000:np.arange(0,125,10),
        50000:np.arange(0,125,10),
        70000:np.arange(0,125,10),
        85000:np.arange(0,125,10),
        92500:np.arange(0,125,10),
        99999:np.arange(0,125,10),
    },
    "mslp":{
        99999:np.arange(900,1050,5),
    }
,
    "rain24":{
        99999:[0.1, 10.0, 25.0, 50.0, 100.0, 250.0, 1000.0],
    }
}

def generate_sample_data(filename,level,var):

    """生成示例数据用于等值线提取"""
    gribparam = grib_dict.grib2io_ground_shortName
 #   data = xr.open_dataset(filename,engine="cfgrib",backend_kwargs={"filter_by_keys":{"typeOfLevel":"isobaricInhPa"}})
    print({"shortName":gribparam[var][0],"typeOfFirstFixedSurface":gribparam[var][2]},level)
    if level != 99999:
        data = xr.open_dataset(filename,engine="grib2io",filters={"shortName":gribparam[var][0],"typeOfFirstFixedSurface":gribparam[var][2]})
        #ata = xr.open_dataset(filename,engine="cfgrib",indexpath="",backend_kwargs={"filter_by_keys":{"shortName":var}})
    else:
        if var =="t": var="2t"
        if var == "r": var="2r"
        #data = xr.open_dataset(filename,engine="cfgrib",indexpath="",backend_kwargs={"filter_by_keys":{"shortName":var}})
        print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",var,gribparam[var][0],gribparam[var][2])
        data = xr.open_dataset(filename,engine="grib2io",filters={"shortName":gribparam[var][0],"typeOfFirstFixedSurface":gribparam[var][2]})
    print(data)
    x = data["longitude"].values if "longitude" in data.coords else data["lon"].values
    y = data["latitude"].values if "latitude" in data.coords else data["lat"].values
#    X,Y = np.meshgrid(x,y)
    X,Y = x,y
    print(x)
    print(y)
    #X, Y = np.meshgrid(x,y)
    # 生成一个类似地球数据的示例函数
    #dx = X[0,1]-X[0,0]
    #dy = Y[1,0]-Y[0,0]


    X = np.concatenate((X,X[:,:1]+360),axis=1)
    Y = np.concatenate((Y,Y[:,:1]),axis=1)
    print("XXXXXXXXXXXXX",X[:,0],Y[0,:])
#   X = np.concatenate((X[:,-20:-1]-360,X,X[:,:10]+360),axis=1)
#   Y = np.concatenate((Y,Y,Y),axis=1)
    if var == "mslp" or level==99999:
        Z = data[gribparam[var][0]].values
        if "ECMWF" in filename:
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            Z = np.flip(Z, axis=0)
    else:
        Z = data[gribparam[var][0]].sel(valueOfFirstFixedSurface = level).values
        #Z = data[var].sel({"isobaricInhPa": level/100}).values
        
    if var in ["t","2t"]:
        Z = Z -273.15
    Z = np.concatenate((Z,Z[:,:1]),axis=1)
    Z = xr.DataArray(data = Z,coords={"lat":Y[:,0],"lon":X[0,]},dims=("lat","lon"))
    xx = np.arange(0,361,0.5)
    yy = np.arange(90,-90,-0.5)
    XX,YY = np.meshgrid(xx,yy)

    Z = Z.interp(lat = yy,lon=xx)
    Z = Z.values
    Z = filters.gaussian(Z,sigma=1)
    Z = np.ma.masked_where(np.isnan(Z),Z)
    print("fugao interpolated shape is ",Z.shape)
    return XX, YY, Z

def process_line_segment(vertices, temp_value, time_str, level_idx, filter_stats):
    """处理单条线段，过滤小闭环"""
    # 坐标精度处理
    vertices = np.round(vertices, COORD_PRECISION)
    coords = vertices.tolist()
    
    # 判断是否为闭合路径
    is_closed = False
    if len(vertices) >= 3 and np.allclose(vertices[0], vertices[-1], atol=1e-2):
        is_closed = True
        # 转换为Shapely多边形计算面积
        try:
            poly = ShapelyPolygon(vertices[:-1])  # 移除重复的最后一个点
            if not poly.is_valid:
                poly = make_valid(poly)
            area = poly.area
            
            # 过滤小面积闭环
            if area < MIN_CLOSED_AREA:
                filter_stats["small_closed"] += 1
                return None
            
            # 过滤超出有效纬度范围的闭环
            lats = vertices[:, 1]
            if all(lat > VALID_LAT_MAX for lat in lats) or all(lat < VALID_LAT_MIN for lat in lats):
                filter_stats["lat_range"] += 1
                return None
            
        except Exception as e:
            filter_stats["invalid_geom"] += 1
            return None
    
    # 生成LineString特征
    return Feature(
        geometry=LineString(coords),
        properties={
            "value": round(float(temp_value), 2),
            "time": time_str,
            "contour_level": level_idx + 1,
            "is_closed": is_closed
        }
    )

def contour_to_geojson(cs,output):

    #geojson = {
    #    "type": "FeatureCollection",
    #    "features": []
    #}
    #paths = []
    #for i in range(len(cs.collections)):
    #    paths.extend(cs.collections[i].get_paths())

    #z_value = cs.levels
    #print(len(paths))
    #for i, pp in enumerate(paths):
    #    code = pp.codes
    #    vertices = pp.vertices
    #    zz = z_value[i]
    #    subpath=[[]]
    #    pointPath = subpath[-1]
    #    for ci in range(len(code)):
    #        outputVert = [vertices[ci][0],vertices[ci][1]]
    #        if True:
    #            if code[ci] == 1:
    #                subpath.append([outputVert])
    #                pointPath = subpath[-1]
    #            else:
    #                pointPath.append(outputVert)
    #    for subpp in subpath:
    #        if len(subpp)>0:
    #            feature = {
    #                "type":"Feature",
    #                "geometry":{
    #                    "type":"LineString",
    #                    "coordinates":subpp
    #                },
    #                "properties":{
    #                    "value":float(zz),
    #                    "level_index":i
    #                }
    #            }

    #            geojson["features"].append(feature)

    geojson = geojsoncontour.contour_to_geojson( contour=cs,ndigits=3)
    with open(output, "w") as f:
        f.write(geojson)

# 获取路径信息
def getContourLine(filename,output,level,var,gpm=None):
    
    X,Y,Z = generate_sample_data(filename,level,var)
    # 绘制轮
    if gpm == None:
        z_max,z_min = Z.max(),Z.min()
        valid_levels = [l for l in paramLevels[var][level] if z_min<=l <=z_max]
    else:
        valid_levels = gpm
    
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    cs = ax.contour(X, Y, Z, levels=valid_levels)
    #plt.show()
    # contour_to_geojson(cs,"aaaaa")
   
     
    contour_to_geojson(cs,output)

##################冷涡识别接口#####################
@typechecked
##################冷涡识别接口#####################
def LENGWO(startTime: datetime, endTime: datetime, ifcst: str, ipara: list, 
           ifh: list, ilevel: list, itimedelta: int) -> tuple:
    """
    冷涡识别接口函数
    
    Args:
        startTime: 开始时间
        endTime: 结束时间  
        ifcst: 预报模式名称
        ipara: 参数列表（对于冷涡识别，这里可以忽略）
        ifh: 预报时效范围 [起始时效, 结束时效]
        ilevel: 气压层列表（对于冷涡识别，固定使用500hPa）
        itimedelta: 时效间隔
        
    Returns:
        tuple: (status, message) - 处理状态和消息
    """
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    def read_grib_data(file_path: str, model: str = 'AUTO') -> Optional[xr.Dataset]:
        """读取GRIB文件数据"""
        try:
            if model == 'NCEP':
                ds = xr.open_dataset(file_path, engine='cfgrib',
                                    backend_kwargs={
                                        'indexpath': '',
                                        'read_keys': [],
                                        'errors': 'ignore',
                                        'filter_by_keys': {'typeOfLevel': 'isobaricInhPa'}
                                    })
                # logger.info(f"NCEP模式: 使用等压面层过滤器读取文件 {file_path}")
            else:
                ds = xr.open_dataset(file_path, engine='cfgrib',
                                    backend_kwargs={
                                        'indexpath': '',
                                        'read_keys': [],
                                        'errors': 'ignore',
                                    })
            return ds
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None
    
    def extract_500hpa_data(ds: xr.Dataset, model: str = 'AUTO') -> Tuple[Optional[np.ndarray], Optional[np.ndarray], 
                                                          Optional[np.ndarray], Optional[np.ndarray]]:
        """提取500hPa的位势高度和温度数据"""
        try:
            if 'gh' not in ds.data_vars or 't' not in ds.data_vars:
                logger.warning("数据中缺少位势高度(gh)或温度(t)变量")
                return None, None, None, None
            
            # 根据模式确定压力层坐标和目标值
            if model == 'NCEP':
                target_pressure = 50000
                pressure_coord = 'isobaricInhPa'
                
                if 'isobaricInhPa' in ds.dims:
                    pressure_coord = 'isobaricInhPa'
                elif 'isobaric' in ds.dims:
                    pressure_coord = 'isobaric'
                elif 'level' in ds.dims:
                    pressure_coord = 'level'
                elif 'plev' in ds.dims:
                    pressure_coord = 'plev'
                else:
                    logger.warning("NCEP模式: 未找到压力层坐标")
                    gh_500 = ds['gh']
                    t_500 = ds['t']
                
                if pressure_coord in ds.dims:
                    gh_500 = ds['gh'].sel({pressure_coord: target_pressure})
                    t_500 = ds['t'].sel({pressure_coord: target_pressure})
            else:
                target_pressure = 500
                
                if 'isobaricInhPa' in ds.dims:
                    gh_500 = ds['gh'].sel(isobaricInhPa=target_pressure)
                    t_500 = ds['t'].sel(isobaricInhPa=target_pressure)
                elif 'isobaric' in ds.dims:
                    gh_500 = ds['gh'].sel(isobaric=target_pressure)
                    t_500 = ds['t'].sel(isobaric=target_pressure)
                elif 'level' in ds.dims:
                    gh_500 = ds['gh'].sel(level=target_pressure)
                    t_500 = ds['t'].sel(level=target_pressure)
                elif 'plev' in ds.dims:
                    gh_500 = ds['gh'].sel(plev=target_pressure)
                    t_500 = ds['t'].sel(plev=target_pressure)
                else:
                    logger.warning(f"{model}模式: 未找到压力层坐标，假设数据已经是500hPa")
                    gh_500 = ds['gh']
                    t_500 = ds['t']
            
            # 获取坐标
            if 'latitude' in ds.coords:
                lat = ds['latitude'].values
                lon = ds['longitude'].values
            elif 'lat' in ds.coords:
                lat = ds['lat'].values
                lon = ds['lon'].values
            else:
                logger.error("找不到纬度经度坐标")
                return None, None, None, None
            
            return gh_500.values, t_500.values, lat, lon
            
        except Exception as e:
            logger.error(f"提取500hPa数据失败: {e}")
            return None, None, None, None
    
    def crop_to_region(gh: np.ndarray, t: np.ndarray, lat: np.ndarray, 
                      lon: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """裁剪数据到东北和华北地区范围"""

        lat_min, lat_max = 35, 60
        lon_min, lon_max = 110, 145
        
        lat_mask = (lat >= lat_min) & (lat <= lat_max)
        lon_mask = (lon >= lon_min) & (lon <= lon_max)
        
        lat_indices = np.where(lat_mask)[0]
        lon_indices = np.where(lon_mask)[0]
        
        if len(lat_indices) == 0 or len(lon_indices) == 0:
            logger.warning("数据范围与东北和华北地区无重叠")
            return gh, t, lat, lon
        
        lat_cropped = lat[lat_indices]
        lon_cropped = lon[lon_indices]
        
        if gh.ndim == 2:
            gh_cropped = gh[np.ix_(lat_indices, lon_indices)]
            t_cropped = t[np.ix_(lat_indices, lon_indices)]
        else:
            logger.warning("数据维度不是2D，跳过裁剪")
            return gh, t, lat, lon
        
        return gh_cropped, t_cropped, lat_cropped, lon_cropped
    
    def find_low_vortex_centers(gh: np.ndarray, lat: np.ndarray, 
                               lon: np.ndarray) -> List[Tuple[int, int, float]]:
        """使用8点法识别低涡中心"""
        centers = []
        rows, cols = gh.shape
        
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), 
                     (0, 1), (1, -1), (1, 0), (1, 1)]
        
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                center_value = gh[i, j]
                
                is_minimum = True
                for di, dj in directions:
                    neighbor_value = gh[i + di, j + dj]
                    if center_value >= neighbor_value:
                        is_minimum = False
                        break
                
                if is_minimum:
                    centers.append((i, j, center_value))
        
        return centers
    
    def calculate_temperature_second_derivative(t: np.ndarray) -> np.ndarray:
        """计算温度的二阶导数（拉普拉斯算子）"""
        rows, cols = t.shape
        laplacian = np.zeros_like(t)
        
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                d2_dx2 = t[i, j-1] - 2*t[i, j] + t[i, j+1]
                d2_dy2 = t[i-1, j] - 2*t[i, j] + t[i+1, j]
                laplacian[i, j] = d2_dx2 + d2_dy2
        
        return laplacian
    
    def check_cold_center(center_i: int, center_j: int, t: np.ndarray, 
                         lat: np.ndarray, lon: np.ndarray) -> bool:
        """检查低涡中心是否为冷中心"""
        temp_laplacian = calculate_temperature_second_derivative(t)
        
        lat_range = 10.0
        lon_range = 10.0
        
        if len(lat) > 1:
            lat_res = abs(lat[1] - lat[0])
        else:
            lat_res = 1.0
            
        if len(lon) > 1:
            lon_res = abs(lon[1] - lon[0])
        else:
            lon_res = 1.0
        
        lat_radius = int(lat_range / (2 * lat_res))
        lon_radius = int(lon_range / (2 * lon_res))
        
        rows, cols = t.shape
        
        i_min = max(0, center_i - lat_radius)
        i_max = min(rows, center_i + lat_radius + 1)
        j_min = max(0, center_j - lon_radius)
        j_max = min(cols, center_j + lon_radius + 1)
        
        for i in range(i_min, i_max):
            for j in range(j_min, min(j_max - 4, cols - 4)):
                consecutive_positive = True
                for k in range(5):
                    if j + k < cols and temp_laplacian[i, j + k] < 0:
                        consecutive_positive = False
                        break
                
                if consecutive_positive:
                    return True
        
        return False
    
    def merge_nearby_centers(cold_centers: List[Tuple[int, int, float]], 
                           lat: np.ndarray, lon: np.ndarray) -> List[Tuple[int, int, float]]:
        """合并5°×5°范围内的多个冷涡中心，保留位势高度最低的"""
        if len(cold_centers) <= 1:
            return cold_centers
        
        centers_with_coords = []
        for i, j, gh_value in cold_centers:
            center_lat = lat[i]
            center_lon = lon[j]
            centers_with_coords.append((i, j, gh_value, center_lat, center_lon))
        
        n = len(centers_with_coords)
        merge_threshold = 5.0
        
        adjacent = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                _, _, _, lat1, lon1 = centers_with_coords[i]
                _, _, _, lat2, lon2 = centers_with_coords[j]
                
                lat_diff = abs(lat1 - lat2)
                lon_diff = abs(lon1 - lon2)
                
                if lat_diff < merge_threshold and lon_diff < merge_threshold:
                    adjacent[i].append(j)
                    adjacent[j].append(i)
        
        visited = [False] * n
        merged_centers = []
        
        def dfs(start, component):
            visited[start] = True
            component.append(start)
            for neighbor in adjacent[start]:
                if not visited[neighbor]:
                    dfs(neighbor, component)
        
        for i in range(n):
            if not visited[i]:
                component = []
                dfs(i, component)
                
                best_idx = min(component, key=lambda idx: centers_with_coords[idx][2])
                best_center = centers_with_coords[best_idx]
                merged_centers.append((best_center[0], best_center[1], best_center[2]))
        
        return merged_centers
    
    def detect_cold_vortex(file_path: str, model: str = 'AUTO') -> Tuple[List[Dict], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """检测单个文件中的冷涡，并返回全球数据用于等值线绘制"""
        ds = read_grib_data(file_path, model)
        if ds is None:
            return [], None, None, None, None
        
        gh, t, lat, lon = extract_500hpa_data(ds, model)
        if gh is None:
            return [], None, None, None, None
        
        gh_crop, t_crop, lat_crop, lon_crop = crop_to_region(gh, t, lat, lon)
        
        low_centers = find_low_vortex_centers(gh_crop, lat_crop, lon_crop)
        if not low_centers:
            return [], t, gh, lat, lon
        
        cold_centers = []
        for center_i, center_j, gh_value in low_centers:
            if check_cold_center(center_i, center_j, t_crop, lat_crop, lon_crop):
                cold_centers.append((center_i, center_j, gh_value))
        
        if not cold_centers:
            return [], t, gh, lat, lon
        
        final_centers = merge_nearby_centers(cold_centers, lat_crop, lon_crop)
        
        results = []
        for center_i, center_j, gh_value in final_centers:
            center_lat = lat_crop[center_i]
            center_lon = lon_crop[center_j]
            
            result = {
                'latitude': round(float(center_lat), 1),
                'longitude': round(float(center_lon), 1),
                'geopotential_height': round(float(gh_value), 2),
                'grid_i': int(center_i),
                'grid_j': int(center_j)
            }
            results.append(result)
        
        return results, t, gh, lat, lon
    
    def create_circle_coordinates(center_lon: float, center_lat: float, radius_km: float = 50) -> List[List[float]]:
        """创建圆形的坐标数组"""
        import math
        
        earth_radius = 6371.0
        radius_deg = radius_km / earth_radius * (180 / math.pi)
        
        coordinates = []
        for i in range(37):
            angle = i * 10 * math.pi / 180
            
            lon = center_lon + radius_deg * math.cos(angle) / math.cos(center_lat * math.pi / 180)
            lat = center_lat + radius_deg * math.sin(angle)
            
            coordinates.append([lon, lat])
        
        return coordinates
    
    def calculate_contours(data: np.ndarray, lat: np.ndarray, lon: np.ndarray, 
                          interval: float, start_value: float = None) -> List[Dict]:
        """计算等值线数据"""
        import matplotlib.pyplot as plt
        
        # 确定等值线范围
        data_min, data_max = np.nanmin(data), np.nanmax(data)
        if start_value is None:
            start_value = int(np.floor(data_min / interval) * interval)
        
        # 向上取整到interval的倍数
        end_level = int(np.ceil(data_max / interval) * interval)
        
        # 生成等值线值：严格每隔interval
        levels = np.arange(start_value, end_level + interval, interval)
        
        contours = []
        if len(levels) > 0:
            # 经纬度网格
            Lon, Lat = np.meshgrid(lon, lat)
            
            # 绘制等值线
            fig, ax = plt.subplots()
            contour_set = ax.contour(Lon, Lat, data, levels=levels)
            plt.close(fig)
            
            # 提取等值线路径
            for i, level in enumerate(levels):
                contour_paths = contour_set.allsegs[i]
                for contour_path in contour_paths:
                    if len(contour_path) > 1:
                        lon_coords = contour_path[:, 0].tolist()
                        lat_coords = contour_path[:, 1].tolist()
                        
                        # 转换为坐标对列表
                        coordinates = list(zip(lon_coords, lat_coords))
                        
                        # 确保遵循右手法则（逆时针方向）
                        def ensure_counter_clockwise(coords):
                            """确保坐标按逆时针方向排列（右手法则）"""
                            if len(coords) < 3:
                                return coords
                            
                            # 计算多边形的有向面积
                            area = 0.0
                            n = len(coords)
                            for i in range(n):
                                j = (i + 1) % n
                                area += coords[i][0] * coords[j][1]
                                area -= coords[j][0] * coords[i][1]
                            
                            # 如果面积为正，说明是顺时针，需要反转
                            if area > 0:
                                return coords[::-1]
                            return coords
                        
                        coordinates = ensure_counter_clockwise(coordinates)
                        
                        contours.append({
                            "level": round(float(level), 2),
                            "coordinates": [[round(coord[0], 1), round(coord[1], 1)] for coord in coordinates]
                        })
        
        return contours
    
    def create_geojson(model: str, forecast_data: Dict, vortex_centers: List[Dict], 
                      temperature_data: np.ndarray = None, geopotential_data: np.ndarray = None,
                      lat: np.ndarray = None, lon: np.ndarray = None) -> Dict:
        """创建GeoJSON格式的输出（包含冷涡中心和等值线）"""
        features = []
        
        # 添加冷涡中心点
        for i, center in enumerate(vortex_centers):
            gh_value = center['geopotential_height']
            
            if gh_value < 5400:
                intensity = "强"
            elif gh_value < 5500:
                intensity = "中"
            else:
                intensity = "弱"
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [center['longitude'], center['latitude']]
                },
                "properties": {
                    "model": model,
                    "geopotential_height": center['geopotential_height'],
                    "grid_i": center['grid_i'],
                    "grid_j": center['grid_j'],
                    "center_id": i + 1,
                    "intensity": intensity,
                    "longitude": center['longitude'],
                    "latitude": center['latitude'],
                    "feature_type": "cold_vortex_center"
                }
            }
            features.append(feature)
        
        # 添加温度等值线（红色虚线，间隔4度摄氏度）
        if temperature_data is not None and lat is not None and lon is not None:
            # 将开尔文温度转换为摄氏度
            temp_celsius = temperature_data - 273.15
            temp_contours = calculate_contours(temp_celsius, lat, lon, 4.0)
            for contour in temp_contours:
                coords = contour["coordinates"]
                if len(coords) > 1:
                    # 用LineString格式
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString", 
                            "coordinates": coords
                        },
                        "properties": {
                            "type": "ISOTHERM",
                            "temperature_C": contour["level"],
                            "model": model,
                            "description": f"{contour['level']}°C等温线",
                            "color": "red",
                            "line_style": "dashed",
                            "interval": 4.0,
                            "feature_type": "temperature_contour"
                        }
                    }
                    features.append(feature)
        
        # 添加位势高度等值线（蓝色实线，间隔40gpm）
        if geopotential_data is not None and lat is not None and lon is not None:
            # 绘制所有等压线，间隔40gpm
            gh_contours = calculate_contours(geopotential_data, lat, lon, 40.0)
            for contour in gh_contours:
                coords = contour["coordinates"]
                if len(coords) > 1:
                    # 用LineString格式
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString", 
                            "coordinates": coords
                        },
                        "properties": {
                            "type": "ISOBAR",
                            "geopotential_gpm": contour["level"],
                            "model": model,
                            "description": f"{contour['level']}gpm等高线",
                            "color": "blue",
                            "line_style": "solid",
                            "interval": 40.0,
                            "feature_type": "geopotential_contour"
                        }
                    }
                    features.append(feature)
        
        # 创建符合GeoJSON规范的FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        if features:
            # 在第一个feature的properties中添加元数据
            features[0]["properties"]["metadata"] = {
                "model": model,
                "forecast_hour": forecast_data['forecast_hour'],
                "total_vortex_centers": len([f for f in features if f['properties']['feature_type'] == 'cold_vortex_center']),
                "total_temperature_contours": len([f for f in features if f['properties']['feature_type'] == 'temperature_contour']),
                "total_geopotential_contours": len([f for f in features if f['properties']['feature_type'] == 'geopotential_contour']),
                "description": "冷涡中心位置、温度等值线和位势高度等值线数据",
                "legend": {
                    "强冷涡": {"condition": "位势高度 < 5400 gpm", "color": "point"},
                    "中等冷涡": {"condition": "5400 ≤ 位势高度 < 5500 gpm", "color": "point"},
                    "弱冷涡": {"condition": "位势高度 ≥ 5500 gpm", "color": "point"},
                    "温度等值线": {"interval": "4°C", "color": "red", "line_style": "dashed"},
                    "位势高度等值线": {"interval": "40gpm", "color": "blue", "line_style": "solid"}
                }
            }
        
        return geojson
    
    def save_single_forecast_result(model: str, forecast_data: Dict, output_dir: str):
        """保存单个预报时刻的检测结果"""
        filename = os.path.basename(forecast_data['file_path'])
        try:
            datetime_str = filename[3:13]
            forecast_hour_str = filename[13:16]
            
            date_part = datetime_str[:8]
            hour_part = datetime_str[8:10]
            forecast_hour = int(forecast_hour_str)
            
            element_type = "lengwo"
            pressure_level = "50000"
            
            syno_output_dir = os.path.join(output_dir, "syno", model, date_part, element_type)
            os.makedirs(syno_output_dir, exist_ok=True)
            
            geojson_filename = f"{element_type}_{pressure_level}_{datetime_str}{forecast_hour:03d}.json"
            
        except Exception as e:
            logger.warning(f"提取文件名信息失败: {e}，使用默认格式")
            syno_output_dir = os.path.join(output_dir, "syno", model, "unknown_date", "lengwo")
            os.makedirs(syno_output_dir, exist_ok=True)
            geojson_filename = f"lengwo_50000_{model}_forecast_{forecast_data['forecast_hour']:03d}.json"
        
        # 创建包含等值线的GeoJSON数据
        geojson_data = create_geojson(
            model, 
            forecast_data, 
            forecast_data['vortex_centers'],
            forecast_data.get('temperature_data'),
            forecast_data.get('geopotential_data'),
            forecast_data.get('lat'),
            forecast_data.get('lon')
        )
        geojson_file = os.path.join(syno_output_dir, geojson_filename)
        
        with open(geojson_file, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        
    
    # ================ 主逻辑开始 ================
    status = True
    mess = ""
    
    try:
        # 获取每个模式的配置信息
        outputroot, fcstroot, toolspath, weight = config_path(ifcst)
        
        # # 临时测试用的路径定义
        # outputroot = r"E:\company\project_model_evaluation\CV_Identify\my_test\cold_vortex_results_250928_contour"
        # fcstroot = r"E:\company\project_model_evaluation\CV_Identify\my_test\fcst"
        # toolspath = ""
        # weight = 1.0
        
        # 格式化时间信息
        YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
        YYYYMMDD = startTime.strftime("%Y%m%d")
        HH = startTime.strftime("%H")
        
        VAR = ipara
        fcst = ifcst
        
        # 处理每个气压层（虽然冷涡识别固定用500hPa，但保持接口一致性）
        for lev in ilevel:           
            # 处理预报时效范围
            processed_count = 0
            for i in range(ifh[0], ifh[1] + 1, itimedelta):
                # 构建文件搜索模式
                file_pattern = fcstroot + "/{:s}/normal/{:s}/prs{:s}*{:03d}.grib".format(
                    fcst, YYYYMMDD, YYYYMMDDHH, i)
                
                # 搜索文件
                filename_list = glob.glob(file_pattern)
                
                if len(filename_list) > 0:
                    filename = filename_list[0]
                    
                    # 执行冷涡识别
                    vortex_centers, temp_data, gh_data, lat_data, lon_data = detect_cold_vortex(filename, fcst)
                    
                    # 构建预报数据结构
                    forecast_data = {
                        'forecast_hour': i,
                        'file_path': filename,
                        'vortex_centers': vortex_centers,
                        'temperature_data': temp_data,  # 温度数据
                        'geopotential_data': gh_data,   # 位势高度数据
                        'lat': lat_data,                # 纬度数据
                        'lon': lon_data                 # 经度数据
                    }
                    
                    # 保存结果
                    save_single_forecast_result(fcst, forecast_data, outputroot)
                    processed_count += 1
                else:
                    logger.warning(f"未找到预报时效 {i}小时的文件: {file_pattern}")
            
            # logger.info(f"气压层 {lev}hPa 处理完成，共处理 {processed_count} 个预报时效")
        
        # 构建输出路径信息（与保存路径一致）
        outputPath = ymlConf.synoOutput + "/syno/{:s}/{:s}/{:s}/".format(fcst, YYYYMMDD, "lengwo")
        
        # # 临时测试用的路径定义
        # outputPath = outputroot + "/syno/{:s}/{:s}/{:s}/".format(fcst, YYYYMMDD, "lengwo")
        # logger.info(f"冷涡识别结果保存路径: {outputPath}")
        
        mess = f"冷涡识别成功完成，模式: {fcst}, 起始时间: {YYYYMMDDHH}"
        
    except Exception as e:
        status = False
        mess = f"冷涡识别处理失败: {str(e)}"
        logger.error(mess)
    
    return status, mess

@typechecked
# === FUGAO 函数 ===
def GAODIYA(startTime: datetime.datetime, endTime: datetime.datetime, ifcst: str, ipara: list, ifh: list, itimedelta: int) -> tuple:
    status = True
    mess = ""
    
    outputroot,fcstroot,toolspath,weight = config_path(ifcst) 
    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = ipara
    fcst = ifcst

    smooth_sigma =  0.8
    tile_size =  55
    relative_diff_hpa = 2
    merge_distance =  20
    contour_interval_hpa = 5


    def write_geojson(highs, lows, lat, lon, data, output_geojson, mode, fixed_radius=0.1, num_points=30):
        features = []

        def round_coords(coords, ndigits=2):
            if isinstance(coords[0], (float, int)):
                return [round(c, ndigits) for c in coords]
            return [round_coords(c, ndigits) for c in coords]

        # 添加高低压中心点
        for y, x in highs:
            features.append(geojson.Feature(
                geometry=geojson.Point((
                    round(float(lon[x]), 2),
                    round(float(lat[y]), 2)
                )),
                properties={
                    "type": "GAOYA",
                    "pressure_hPa": round(float(data[y, x]), 2),
                    "model": mode,
                    "description": f"{float(data[y, x]):.1f}hPa"
                }
            ))
        for y, x in lows:
            features.append(geojson.Feature(
                geometry=geojson.Point((
                    round(float(lon[x]), 2),
                    round(float(lat[y]), 2)
                )),
                properties={
                    "type": "DIYA",
                    "pressure_hPa": round(float(data[y, x]), 2),
                    "model": mode,
                    "description": f"{float(data[y, x]):.1f}hPa"
                }
            ))

        # ---------------- 等压线部分 ----------------
        contour_interval_hpa = 5
        min_val = float(np.nanmin(data))
        max_val = float(np.nanmax(data))

        start_level = int(np.floor(min_val / contour_interval_hpa) * contour_interval_hpa)
        end_level = int(np.ceil(max_val / contour_interval_hpa) * contour_interval_hpa)
        levels = np.arange(start_level, end_level + contour_interval_hpa, contour_interval_hpa)

        if len(levels) > 0:
            Lon, Lat = np.meshgrid(lon, lat)

            # 绘制等压线
            fig, ax = plt.subplots()
            contour_set = ax.contour(Lon, Lat, data, levels=levels)
            plt.close(fig)

            # 提取等压线路径
            for i, level in enumerate(levels):
                contours = contour_set.allsegs[i]
                for contour in contours:
                    if len(contour) > 1:
                        lon_coords = contour[:, 0].tolist()
                        lat_coords = contour[:, 1].tolist()

                        # 坐标保留一位小数
                        coords = round_coords(list(zip(lon_coords, lat_coords)), ndigits=1)

                        geometry = geojson.LineString(coords)
                        feature_type = "ISOBAR"

                        features.append(geojson.Feature(
                            geometry=geometry,
                            properties={
                                "type": feature_type,
                                "pressure_hPa": round(float(level), 2),
                                "model": mode,
                                "description": f"MSLP {float(level):.1f}hPa"
                            }
                        ))

        # ---------------- 输出 GeoJSON ----------------
        collection = geojson.FeatureCollection(features)
        os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
        with open(output_geojson, 'w') as f:
            geojson.dump(collection, f, ensure_ascii=False, indent=2)


    # === 极值识别函数 ===
    def detect_centers(data, tile_size=300, diff_threshold_hpa=0.25):
        h, w = data.shape
        highs, lows = [], []
        for y0 in range(0, h, tile_size):
            for x0 in range(0, w, tile_size):
                y1 = min(y0 + tile_size, h)
                x1 = min(x0 + tile_size, w)
                tile = data[y0:y1, x0:x1]
                if tile.size == 0 or tile.shape[0] < 10 or tile.shape[1] < 10:
                    continue
                local_min = np.min(tile)
                local_max = np.max(tile)
                avg = np.mean(tile)
                if (avg - local_min) >= diff_threshold_hpa:
                    y_min, x_min = np.unravel_index(np.argmin(tile), tile.shape)
                    lows.append((y0 + y_min, x0 + x_min))
                if (local_max - avg) >= diff_threshold_hpa:
                    y_max, x_max = np.unravel_index(np.argmax(tile), tile.shape)
                    highs.append((y0 + y_max, x0 + x_max))
        return highs, lows

    def merge_close_points(points, data, min_dist=30, mode='high', edge_margin=5):
        h, w = data.shape
        points = [(y, x) for (y, x) in points if edge_margin <= y < h - edge_margin and edge_margin <= x < w - edge_margin]
        kept = []
        used = np.zeros(len(points), dtype=bool)
        for i, (y1, x1) in enumerate(points):
            if used[i]:
                continue
            group = [(i, y1, x1)]
            for j, (y2, x2) in enumerate(points):
                if i != j and not used[j]:
                    if np.hypot(y2 - y1, x2 - x1) < min_dist:
                        group.append((j, y2, x2))
                        used[j] = True
            if mode == 'high':
                best = max(group, key=lambda x: data[x[1], x[2]])
            else:
                best = min(group, key=lambda x: data[x[1], x[2]])
            kept.append((best[1], best[2]))
        return kept

    for i in range(ifh[0], ifh[1] + 1, itimedelta):
        file_pattern = fcstroot + "/{:s}/normal/{:s}/prs{:s}*{:03d}.grib".format(
                    fcst, YYYYMMDD, YYYYMMDDHH, i)
        filename = glob.glob(file_pattern)

        if len(filename) > 0:
            filename = filename[0]
            outputPath = ymlConf.synoOutput+"/{:s}/{:s}/{:s}/".format(fcst,YYYYMMDD,"GAODIYA")

            ds = xr.open_dataset(filename, engine="cfgrib", indexpath=None,backend_kwargs={"filter_by_keys": {"shortName" :"msl"}})
            data = ds['msl'].values

            lat = ds['latitude'].values
            lon = ds['longitude'].values  
            
            data_smooth = gaussian_filter(data, sigma=smooth_sigma)

            # 高低压中心识别
            raw_highs, raw_lows = detect_centers(data_smooth, tile_size, relative_diff_hpa)
            highs = merge_close_points(raw_highs, data_smooth, merge_distance, mode='high')
            lows = merge_close_points(raw_lows, data_smooth, merge_distance, mode='low')

            # 保存 GeoJSON
            grib_filename = os.path.basename(filename).replace('.grib', '')[3:]
            json_file = os.path.join(outputPath, f"GAODIYA_99999_{grib_filename}.json")
            write_geojson(highs, lows, lat, lon, data, json_file, mode=fcst)

    return status, mess


@typechecked
def FUGAO(startTime:datetime.datetime,endTime:datetime.datetime, ifcst:str, ipara:list,ifh:list,ilevel:list,itimedelta:int)->tuple:
    status = True
    mess = ""
    outputroot,fcstroot,toolspath,weight = config_path(ifcst)
    print(outputroot,fcstroot,toolspath,weight)
    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = ipara
    fcst = ifcst
    
    tmpdf = {"mode_type": [], "meteorological_element_type": [],"height": [],"forecast_time":[],"forecast_hour":[],"forecast_interval":[],\
        "area_index":[],"intensity_index":[],"western_ridge_point":[]}
    resdf = pd.DataFrame(tmpdf)
    for var in VAR:
        for lev in ilevel:
            
            for i in range(ifh[0],ifh[1]+1,itimedelta):
                intensity = 0
                area = 0
                elon = 0
                flag = 1
                filename = glob.glob(fcstroot+ "/{:s}/normal/{:s}/prs{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))

                if len(filename) >0:
                    
                    filename = filename[0]
                    print(filename)
                    outputPath = ymlConf.synoOutput+"/{:s}/{:s}/{:s}/".format(fcst,YYYYMMDD,"fugao")
                    os.makedirs(outputPath, exist_ok = True)
                    getContourLine(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format("fugao",str(50000),YYYYMMDDHH,i),50000,"gh",[5880])

                    #data = xr.open_dataset(filename,engine="grib2io",filters={"shortName":"HGT","typeOfFirstFixedSurface":100})
                    #data = data.sel(valueOfFirstFixedSurface = 50000)
                    data = xr.open_dataset(filename,engine="cfgrib",indexpath="",backend_kwargs={"filter_by_keys":{"shortName":"gh"}})
                    data = data.sel(isobaricInhPa=500)
                    #gh500 = xr.DataArray( data = gh500.values, dims=["y","x"],coords=[("y",gh500.latitude.data[:,0]),("x",gh500.longitude.data[0,:])])
                    #print(gh500)
                    lon_new = np.arange(0,360,2.5)
                    lat_new = np.arange(90,-90.25,-2.5)
                    data_interp = data.interp(latitude = lat_new, longitude= lon_new, method='linear')
                    
                    gh500 = data_interp.sel( latitude = slice(90,10 ))
                    gh500 = gh500.sel( longitude = slice(110,180))

                    shape = gh500["gh"].values.shape
                    ff = gh500["gh"].values/10
                    for jj in range(shape[0]):
                        for ii in range(shape[1]):
                            if ff[jj,ii]>588 and ff[jj,ii]<610:
                                intensity = intensity + int(ff[jj,ii]-588)+1
                    
                    gh500 = data_interp.sel(latitude=slice(90,0))
                    ff = gh500["gh"].values/10
                    for ii in range(37,73):
                        for jj in range(0,36):
                            if(ff[jj,ii]>588 and flag ==1):
                                print(gh500["longitude"][ii])
                                print(ff[jj,ii],jj,ii)
                                elon = (ii)*2.5
                                flag = 0
 #
                    gh500 = data_interp.sel( latitude = slice(90,10))
                    gh500 = gh500.sel( longitude = slice(110,180))
                    ff = gh500["gh"].values/10
                    shape = gh500["gh"].values.shape
                    for jj in range(shape[0]):
                        for ii in range(shape[1]):
                            if(ff[jj,ii]>588 and ff[jj,ii]<610):
                                area = area+1
                    resdf.loc[len(resdf)] = {"mode_type": fcst, "meteorological_element_type": var,"height": "500","forecast_time":startTime,"forecast_hour":HH,"forecast_interval":i,\
                        "area_index":area,"intensity_index":intensity,"western_ridge_point":elon}

    t1 = datetime.datetime.now()
    print(resdf)
    if len(resdf) > 0:
        delete_sql = f"""
    ALTER TABLE weather_verification_result 
    DELETE WHERE 
        mode_type = '{fcst}' AND
        meteorological_element_type = '{var}' AND
        height = '500' AND
        forecast_time = '{startTime.strftime("%Y-%m-%d")}' AND
        forecast_hour = '{HH}'
    """
        print(delete_sql)
        clickclient.command(delete_sql)
    batch_size = 10000
    for i in range(0, len(resdf), batch_size):
        batch = resdf.iloc[i:i + batch_size]
        clickclient.insert_df("weather_verification_result", batch)
    print(datetime.datetime.now() - t1)        
    return status,mess

 

@typechecked
def yunyao_synoptic(startTime:datetime.datetime,endTime:datetime.datetime, ifcst:str, ipara:list,ifh:list,ilevel:list,itimedelta:int)->tuple:

    status = True
    mess = ""
    outputroot,fcstroot,toolspath,weight = config_path(ifcst)

    YYYYMMDDHH = startTime.strftime("%Y%m%d%H")
    YYYYMMDD = startTime.strftime("%Y%m%d")
    HH = startTime.strftime("%H")
    VAR = ipara
    fcst = ifcst

    for var in VAR:
        for lev in ilevel:
            for i in range(ifh[0],ifh[1]+1,itimedelta):
                filename = glob.glob(fcstroot+ "/{:s}/normal/{:s}/prs{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))

                print("aaaa",var,fcstroot+ "/{:s}/normal/{:s}/prs{:s}*{:0>3d}.grib".format(fcst,YYYYMMDD, YYYYMMDDHH, i))
                if var == "rain24" or var == "rain3" or var == "rain6" or var == "rain12":
                    if fcst=="ERA5":
                        filename = glob.glob(fcstroot+"/{:s}/rain/{:s}/obs.{:s}.grb1".format(fcst,var,YYYYMMDDHH))
                        print("era5 rain file:", var, fcstroot+"/{:s}/rain/{:s}/obs.{:s}.grb1".format(fcst,var,YYYYMMDDHH))
                    else:
                        filename = glob.glob(fcstroot+ "/{:s}/rain/{:s}/fcst{:s}*{:0>3d}.grb".format(fcst,var, YYYYMMDDHH, i))
                        print("rain file:", var, fcstroot+ "/{:s}/rain/{:s}/fcst{:s}*{:0>3d}.grb".format(fcst,var, YYYYMMDDHH, i))
                #print(fcstroot+ "/{:s}/rain/{:s}/fcst{:s}*{:0>3d}.grb".format(fcst, var, YYYYMMDDHH, i))
                #print(filename)
                if len(filename) >0:
                    filename = filename[0]
                    print(filename)
                    outputPath = ymlConf.synoOutput+"/{:s}/{:s}/{:s}/".format(fcst,YYYYMMDD,var)
                    print(outputPath)
                    os.makedirs(outputPath,exist_ok=True)
                    if var =="mslp":
                        getContourLine(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format(var,"99999",YYYYMMDDHH,i),int(99999),var)
                    elif var == "wind":
                        era5_data = None
                        if fcst!="ERA5":
                            era5_filename = get_era5_filename(startTime, i)
                            if len(era5_filename) > 0:
                                era5_data = read_wind_data(era5_filename, int(lev))
                        getWind(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format(var,lev,YYYYMMDDHH,i),int(lev),era5_data)
                    elif var == "rain24" or var == "rain3" or var == "rain6" or var == "rain12":
                        if fcst != "ERA5":
                            getRain24(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format(var,lev,YYYYMMDDHH,i))
                        else:
                            getContourLine(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format(var,lev,YYYYMMDDHH,i),int(lev),var)
                    else:
                        getContourLine(filename,outputPath+"{:s}_{:s}_{:s}{:0>3d}.json".format(var,lev,YYYYMMDDHH,i),int(lev),var)
                else:
                    status = False
                    mess = "no such file"

    return status,mess

def getRain24(filename, output):
    custom_levels = [0.1, 10.0, 25.0, 50.0, 100.0, 250.0, 1000.0]
    #custom_levels = [0.1, 1, 10]
    variable_name="tp"
    #geojson_gen_polygon.process_rain(filename, output, variable_name, custom_levels)
    geojson_gen_polygon_high.process_rain(filename, output, custom_levels)

def get_era5_filename(startTime:datetime.datetime, delt:int, ifcst:str="ERA5"):
    #era5只有00时刻，要先算出实况的时间
    real_time = startTime + datetime.timedelta(hours=delt)
    outputroot,fcstroot,toolspath,weight = config_path(ifcst)
    YYYYMMDDHH = real_time.strftime("%Y%m%d%H")
    YYYYMMDD = real_time.strftime("%Y%m%d")
    filename = glob.glob(fcstroot+ "/{:s}/normal/{:s}/prs{:s}*{:0>3d}.grib".format(ifcst,YYYYMMDD, YYYYMMDDHH, 0))
    if len(filename) > 0:
        filename = filename[0]
    else:
        filename = ""
    return filename
    
def getWind(filename,output,level,era5_data=None):
    result = read_wind_data(filename, level)
    result,bias_result = match_era5_wind(result, era5_data)
    with open(output, 'w') as f:
        ujson.dump(result, f, indent=2)
    if era5_data is not None and len(bias_result) > 0:
        file_name, suffix = output.rsplit('.', 1)
        bias_file = f"{file_name}_bias.{suffix}" 
        with open(bias_file, 'w') as f:
            ujson.dump(bias_result, f, indent=2)    

def match_era5_wind(wind_data, era5_data):
    result = []
    bias_result= []
    # 直接按索引匹配（经纬度顺序完全一致）
    for i in range(len(wind_data)):
        forecast_point = wind_data[i]
        if forecast_point["u"] is None or forecast_point["v"] is None:
            continue
        if era5_data is not None:
            era5_point = era5_data[i]
            # 验证经纬度是否匹配
            if (abs(forecast_point["lon"] - era5_point["lon"]) > 0.01 or 
                abs(forecast_point["lat"] - era5_point["lat"]) > 0.01):
                print(f"经纬度不匹配: 预报({forecast_point['lon']}, {forecast_point['lat']}) vs ERA5({era5_point['lon']}, {era5_point['lat']})")
                continue
            # 计算预报风速大小
            forecast_speed = np.sqrt(forecast_point["u"]**2 + forecast_point["v"]**2)
            # 计算ERA5风速大小
            era5_speed = np.sqrt(era5_point["u"]**2 + era5_point["v"]**2)

            # 计算偏差
            speed_bias = forecast_speed - era5_speed
        else:
            speed_bias = None
        result.append(forecast_point)
        # 创建新的数据点，包含原始数据和偏差信息
        result_point = forecast_point.copy()
        if speed_bias is not None:
            result_point.update({
                "bias": round(speed_bias, 3)
            })       
        bias_result.append(result_point)
    return result,bias_result


def read_wind_data(filename, level):
    print("wind file_name:", filename)
    if level == 99999:
        # 地面风场，通常是10米高度
        filter_params = {'typeOfLevel': 'heightAboveGround', 'level': 10}
        u_name, v_name = 'u10', 'v10'
    else:
        # 等压面风场，如500hPa、850hPa等
        level = level / 100
        filter_params = {'typeOfLevel': 'isobaricInhPa', 'level': level}
        u_name, v_name = 'u', 'v'
    ds = xr.open_dataset(filename, engine='cfgrib', 
                            backend_kwargs={'filter_by_keys': filter_params})
    u_data = ds[u_name]
    v_data = ds[v_name]
    lons = u_data.longitude.values
    lats = u_data.latitude.values
    result = []
    for i in range(len(lats)):
        for j in range(len(lons)):
            # 获取当前点的u和v值
            u_val = float(u_data.values[i, j])
            v_val = float(v_data.values[i, j])
            result.append({
                "lon": float(lons[j]),
                "lat": float(lats[i]),
                "u": None if np.isnan(u_val) else round(u_val, 3),
                "v": None if np.isnan(v_val) else round(v_val, 3)
            })
    return result



###################测试接口###################
def main():
 # 定义测试参数
    startTime = datetime.datetime(2025, 5, 2, 0, 0)  # 设置起始时间
    endTime = datetime.datetime(2025, 5, 2, 0, 0)  # 设置结束时间

    # 需要根据你的文件路径和要素来设置
    ifcst = 'ERA5'  # 预报种类
    ipara =  ['rain24']  # 变量名称
    ifh = [0,0]  # 时间步
    itimedelta = 12  # 每小时的时间步
    level = ["99999"]

    # 调用 GAODIYA 函数
    #status, mess = GAODIYA(startTime, endTime, ifcst, ipara, ifh, itimedelta)
    status, mess = yunyao_synoptic(startTime, endTime, ifcst, ipara, ifh, level,itimedelta)

    # 打印返回结果
    print("状态:", status)
    print("消息:", mess)

     
#    print(f"\nLENGWO接口函数执行结果:")
#    print(f"状态: {'成功' if status else '失败'}")
#    print(f"消息: {message}")
#    
#    print(f"\n输出格式说明:")
#    print(f"存储路径: ./syno/{{预报种类}}/{{YYYYMMDD}}/lengwo/lengwo_50000_YYYYMMDDHHFFF.json")
#    print(f"示例路径: ./syno/ECMWF/20250815/lengwo/lengwo_50000_2025081500006.json")
#    print(f"预报种类: KT1279, AUTO, NCEP, ECMWF等")
#    print(f"要素类型: lengwo（冷涡）")
#    print(f"气压层: 50000（500hPa）")
#    
#    print(f"\n接口函数参数说明:")
#    print(f"  startTime: {startTime} (开始时间)")
#    print(f"  endTime: {endTime} (结束时间，当前版本暂未使用)")
#    print(f"  ifcst: {ifcst} (预报模式: AUTO、ECMWF、KT1279、NCEP)")
#    print(f"  ipara: {ipara} (参数列表，冷涡识别固定为['lengwo'])")
#    print(f"  ifh: {ifh} (预报时效范围[起始,结束]小时)")
#    print(f"  ilevel: {ilevel} (气压层，冷涡识别固定为[500])")
#    print(f"  itimedelta: {itimedelta} (时效间隔小时)")

if __name__ == "__main__":
    main() 



#if __name__ == "__main__":
#    #fcst = "AUTO"
#    #YYYYMMDD = "20250815"
#    #var = "gh"
#    #YYYYMMDDHH="2025081500"
#    #i = 0
#    #lev = 85000
#    #outputPath = ymlConf.synoOutput+"/{:s}/{:s}/{:s}/".format(fcst,YYYYMMDD,var)
#    #
#    #outputFile = outputPath+"{:s}_{:d}_{:s}{:0>3d}.json".format(var,lev,YYYYMMDDHH,i)
#    #os.makedirs(outputPath,exist_ok=True)
#    #getContourLine("/home/devopler/workshop/met_backend/fcst/AUTO/normal/20250815/prs2025081500240.grib",outputFile,lev,var)
#    #
#    startTime = datetime.datetime.strptime("2025081500","%Y%m%d%H")
#    
#    GAODIYA(startTime,startTime,"AUTO",["mslp"],[0,240],[50000],12)
