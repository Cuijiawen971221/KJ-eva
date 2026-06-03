import numpy as np

import pandas as pd

def grid_data_by_lat_lon(station_data, lat_col, lon_col, value_col, lon_grid, lat_grid, grid_resolution):
    """
    将站点数据根据经纬度填入网格，同一网格内的点取均值
    
    参数:
    station_data: DataFrame, 包含经纬度和数值的站点数据
    lat_col: str, 纬度列名
    lon_col: str, 经度列名
    value_col: str, 数值列名
    grid_resolution: float, 网格分辨率（度）
    
    返回:
    grid_data: 2D numpy array, 网格化数据
    grid_info: dict, 网格信息
    """
    
    # 获取经纬度范围
    min_lat = lat_grid.min()
    max_lat = lat_grid.max()
    min_lon = lon_grid.min()
    max_lon = lon_grid.max()
    
    # 计算网格行列数
    n_rows = len(lat_grid)   #int(np.ceil((max_lat - min_lat) / grid_resolution)) + 1
    n_cols = len(lon_grid)   #int(np.ceil((max_lon - min_lon) / grid_resolution)) + 1
    
    # 初始化网格数据存储结构（使用普通字典）
    grid_dict = {}
    
    # 将每个站点数据放入对应的网格
    for _, row in station_data.iterrows():
        lat = row[lat_col]
        lon = row[lon_col]
        value = row[value_col]
        
        # 计算网格索引
        row_idx = int((float(lat) - float(min_lat)) / grid_resolution)
        col_idx = int((float(lon) - float(min_lon)) / grid_resolution)
        
        # 存储到对应网格
        key = (row_idx, col_idx)
        if key not in grid_dict:
            grid_dict[key] = []
        grid_dict[key].append(value)
    
    # 创建结果网格
    grid_data = np.full((n_rows, n_cols), np.nan)
    
    # 填充网格数据，多个点取均值
    for (row_idx, col_idx), values in grid_dict.items():
        if values:  # 如果网格内有数据
            grid_data[row_idx, col_idx] = np.mean(values)
    
    # 网格信息
 #   grid_info = {
 #       'min_lat': min_lat,
 #       'max_lat': max_lat,
 #       'min_lon': min_lon,
 #       'max_lon': max_lon,
 #       'grid_resolution': grid_resolution,
 #       'n_rows': n_rows,
 #       'n_cols': n_cols
 #   }
    
    return grid_data        #, grid_info


def get_grid_coordinates(grid_info):
    """
    获取网格的经纬度坐标
    
    参数:
    grid_info: 网格信息字典
    
    返回:
    lat_coords: 纬度坐标数组
    lon_coords: 经度坐标数组
    """
    min_lat = grid_info['min_lat']
    min_lon = grid_info['min_lon']
    grid_resolution = grid_info['grid_resolution']
    n_rows = grid_info['n_rows']
    n_cols = grid_info['n_cols']
    
    lat_coords = [min_lat + i * grid_resolution for i in range(n_rows)]
    lon_coords = [min_lon + j * grid_resolution for j in range(n_cols)]
    
    return lat_coords, lon_coords


# 创建示例数据
#np.random.seed(42)
#n_stations = 100

# 生成随机站点数据
#data = {
#    'lat': np.random.uniform(30, 40, n_stations),
#    'lon': np.random.uniform(110, 120, n_stations),
#    'value': np.random.normal(25, 5, n_stations)
#}
#station_df = pd.DataFrame(data)

# 网格化处理
#grid_resolution = 0.5  # 0.5度网格
#grid_data = grid_data_by_lat_lon(
#    station_df, 
#    lat_col='lat', 
#    lon_col='lon', 
#    value_col='value', 
#    grid_resolution=grid_resolution
#)
