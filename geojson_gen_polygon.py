import os
import numpy as np
import ujson
from geojson import Feature, FeatureCollection, Polygon
from netCDF4 import Dataset
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.colors import LinearSegmentedColormap
import time
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid
from shapely.ops import unary_union


# 全局配置（保持核心优化参数）
VALID_LAT_MIN = -85.1
VALID_LAT_MAX = 85.1
FILTER_NEG90_THRESHOLD = -89.9
WEB_MERC_MIN_LAT = round(-85.05112877980659, 2)
WEB_MERC_MAX_LAT = round(85.05112877980659, 2)
SIMPLIFY_TOLERANCE = 0.02  # 简化精度  數值越小文件越小  太大的話交叉出會重合或者有縫隙

MIN_POLYGON_AREA = 0
COORD_PRECISION = 2


def clip_to_web_merc_lat(lon_1d, lat_1d, data_2d):
    valid_lat_mask = (lat_1d >= WEB_MERC_MIN_LAT) & (lat_1d <= WEB_MERC_MAX_LAT)
    valid_lat_indices = np.where(valid_lat_mask)[0]
    
    if len(valid_lat_indices) == 0:
        raise ValueError(f"无有效纬度数据！Web Mercator仅支持 {WEB_MERC_MIN_LAT:.2f} ~ {WEB_MERC_MAX_LAT:.2f}")
    
    clipped_lat = lat_1d[valid_lat_indices]
    clipped_data = data_2d[valid_lat_indices, :]
    
    print(f"\nWeb Mercator纬度裁剪完成：")
    print(f"  原始纬度范围：{lat_1d.min():.2f} ~ {lat_1d.max():.2f}")
    print(f"  裁剪后纬度范围：{clipped_lat.min():.2f} ~ {clipped_lat.max():.2f}")
    print(f"  原始数据形状：{data_2d.shape}（lat × lon）")
    print(f"  裁剪后数据形状：{clipped_data.shape}（lat × lon）")
    
    return lon_1d, clipped_lat, clipped_data

# 替换原有read_nc_file函数
def read_grib_file(file_path, variable_name="apcp"):
    try:
        import xarray as xr
        # 使用xarray读取grib文件
        ds = xr.open_dataset(file_path, engine="cfgrib",backend_kwargs={"filter_by_keys":{"shortName":"tp"}})
        print(ds)
        print(variable_name)
        # 获取指定变量
        var = ds[variable_name]
        print(f"变量 {variable_name} 维度: {var.dims}，形状: {var.shape}")
        
        # 转换数据为numpy数组
        data = var.values.astype(np.float32)
        data = np.where(np.isnan(data), -999, data)
        print(data)
        #data = np.floor(data).astype(np.int32)
        #print(data)
        
        # 获取经纬度（假设为regular grid）
        raw_lon = var.longitude.values.astype(np.float32)
        lat_1d = var.latitude.values.astype(np.float32)
        lon_1d = np.where(raw_lon > 180, raw_lon - 360, raw_lon)
        lon_1d = np.round(lon_1d, COORD_PRECISION).astype(np.float32)
            
        # 经度排序与数据对齐
        sorted_indices = np.argsort(lon_1d)
        lon_1d = lon_1d[sorted_indices]
        if data.ndim == 3:
            data = data[..., sorted_indices]
        elif data.ndim == 2:
            data = data[:, sorted_indices]
            
        # 补充-180°数据
        idx_180 = np.argmin(np.abs(lon_1d - 180.0))
        if not np.isclose(lon_1d[0], -180.0, atol=1e-2):
            print(f"\n检测到无-180°数据，复制180°数据补充到-180°...")
            data_col_180 = data[..., idx_180:idx_180+1] if data.ndim == 3 else data[:, idx_180:idx_180+1]
            lon_minus_180 = round(-180.0, COORD_PRECISION)
            lon_1d = np.insert(lon_1d, 0, lon_minus_180)
            data = np.concatenate([data_col_180, data], axis=-1)
            print(f"  补充后经度首尾值：{lon_1d[0]:.2f}（首，-180°）、{lon_1d[-1]:.2f}（尾，180°）")
            print(f"  补充后数据形状：{data.shape}")
        else:
            print(f"\n已存在-180°数据，无需重复补充")
            
        print(f"\n原始经度范围（转换前）：{raw_lon.min():.2f} ~ {raw_lon.max():.2f}°")
        print(f"最终经度范围：{lon_1d.min():.2f} ~ {lon_1d.max():.2f}°")

        
        # 时间处理
        time = var.time.values
        if isinstance(time, np.datetime64):
            times = [time.astype('datetime64[s]').astype(int)]
        else:
            times = [t.astype('datetime64[s]').astype(int) for t in time]
        
        # 转置数据维度（grib通常为lon在前）
        if var.dims.index('longitude') < var.dims.index('latitude'):
            data = data.T
        
        return data, lon_1d, lat_1d, times, "hours since 1970-01-01 00:00:00"
    except Exception as e:
        print(f"GRIB文件读取错误: {e}")
        return None, None, None, None, None

def read_nc_file(file_path, variable_name="apcp"):
    try:
        with Dataset(file_path, 'r') as nc:
            if variable_name not in nc.variables:
                raise KeyError(f"NC文件中无变量 {variable_name}，可用变量：{list(nc.variables.keys())}")
            
            var = nc.variables[variable_name]
            print(f"变量 {variable_name} 维度: {var.dimensions}，形状: {var.shape}")
            
            var.set_auto_mask(True)
            data = var[:].astype(np.float32)  # 降精度为float32
            if np.ma.is_masked(data):
                data = data.data
                data[np.ma.getmaskarray(var[:])] = -999
            
            # 经纬度读取与标准化（均转为float32）
            raw_lon = nc.variables['longitude'][:] if 'longitude' in nc.variables else nc.variables['lon'][:]
            raw_lon = np.round(raw_lon, COORD_PRECISION).astype(np.float32)
            lat_1d = nc.variables['latitude'][:] if 'latitude' in nc.variables else nc.variables['lat'][:]
            lat_1d = np.round(lat_1d, COORD_PRECISION).astype(np.float32)
            
            lon_1d = np.where(raw_lon > 180, raw_lon - 360, raw_lon)
            lon_1d = np.round(lon_1d, COORD_PRECISION).astype(np.float32)
            
            # 经度排序与数据对齐
            sorted_indices = np.argsort(lon_1d)
            lon_1d = lon_1d[sorted_indices]
            if data.ndim == 3:
                data = data[..., sorted_indices]
            elif data.ndim == 2:
                data = data[:, sorted_indices]
            
            # 补充-180°数据
            idx_180 = np.argmin(np.abs(lon_1d - 180.0))
            if not np.isclose(lon_1d[0], -180.0, atol=1e-2):
                print(f"\n检测到无-180°数据，复制180°数据补充到-180°...")
                data_col_180 = data[..., idx_180:idx_180+1] if data.ndim == 3 else data[:, idx_180:idx_180+1]
                lon_minus_180 = round(-180.0, COORD_PRECISION)
                lon_1d = np.insert(lon_1d, 0, lon_minus_180)
                data = np.concatenate([data_col_180, data], axis=-1)
                print(f"  补充后经度首尾值：{lon_1d[0]:.2f}（首，-180°）、{lon_1d[-1]:.2f}（尾，180°）")
                print(f"  补充后数据形状：{data.shape}")
            else:
                print(f"\n已存在-180°数据，无需重复补充")
            
            print(f"\n原始经度范围（转换前）：{raw_lon.min():.2f} ~ {raw_lon.max():.2f}°")
            print(f"最终经度范围：{lon_1d.min():.2f} ~ {lon_1d.max():.2f}°")
            
            times = nc.variables['time'][:] if 'time' in nc.variables else np.arange(data.shape[0])
            time_units = nc.variables['time'].units if 'time' in nc.variables else None
        
        return data, lon_1d, lat_1d, times, time_units
    except Exception as e:
        print(f"NC文件读取错误: {e}")
        return None, None, None, None, None


def calculate_contours_with_boundary(lon_1d, lat_1d, data_2d, levels=None):
    plt.ioff()
    data_clean = np.where(data_2d == -999, np.nan, data_2d).astype(np.float32)
    X, Y = np.meshgrid(lon_1d, lat_1d)
    
    # 自动生成或使用自定义等值线层级
    if levels is None:
        valid_data = data_clean[~np.isnan(data_clean)]
        if len(valid_data) == 0:
            return None, []
        
        precip_min = max(0, np.min(valid_data))
        precip_max = np.max(valid_data)
        
        if precip_min == precip_max:
            levels = [precip_min, precip_min + 0.1]
        else:
            levels = np.percentile(valid_data, [0.1, 1, 10, 25, 50, 75, 90, 95, 100])
            levels = np.unique(levels)
        
        print(f"等值线层级: {levels.round(2)}")
    else:
        print(f"使用自定义等值线层级: {levels}（共 {len(levels)-1} 个区间）")
    
    # 生成等值线
    num_intervals = len(levels) - 1
    colors = ['#e0f7fa', '#80deea', '#4db6ac', '#81c784', '#dce775', '#ffb74d', '#ff8a65', '#ef5350']
    if len(colors) != num_intervals:
        colors = (colors * (num_intervals // len(colors) + 1))[:num_intervals]
    
    cmap = LinearSegmentedColormap.from_list('precip_cmap', colors, N=num_intervals)
    start_contour = time.perf_counter()

    contour = plt.contourf(X, Y, data_clean, levels=levels, cmap=cmap, alpha=0.8)
    end_contour = time.perf_counter()
    print(f"生成等值线时间: {end_contour - start_contour} 秒")

    plt.close()
    return contour, levels


# 辅助函数：处理单个Shapely多边形
def process_sub_poly(shapely_poly, lower, upper, time_str, features, filter_reason, vertex_stats):
    poly_area = shapely_poly.area
    if poly_area < MIN_POLYGON_AREA:
        filter_reason["area"] += 1
        return
    
    # 坐标提取与精度降低
    coords = np.round(np.array(shapely_poly.exterior.coords), COORD_PRECISION)
    lons = coords[:, 0]
    lats = coords[:, 1]
    
    # 经纬度范围过滤
    if all(lat > VALID_LAT_MAX + 1e-3 for lat in lats) or all(lat < VALID_LAT_MIN - 1e-3 for lat in lats):
        filter_reason["lat_range"] += 1
        return
    if any(lat <= FILTER_NEG90_THRESHOLD for lat in lats):
        filter_reason["neg90"] += 1
        return
    if np.max(lons) > 180 + 1e-3 or np.min(lons) < -180 - 1e-3:
        filter_reason["lon_range"] += 1
        return
    
    # 顶点数过滤
    simplified_vertices = len(coords)
    original_vertices = len(np.array(shapely_poly.exterior.coords))
    if simplified_vertices < 3:
        filter_reason["vertex_count"] += 1
        return
    
    # 记录统计信息
    vertex_stats["original"].append(original_vertices)
    vertex_stats["simplified"].append(simplified_vertices)
    
    # 处理内环（洞）
    interiors = []
    for interior in shapely_poly.interiors:
        interior_coords = np.round(np.array(interior.coords), COORD_PRECISION)
        if len(interior_coords) >= 3:
            interiors.append(interior_coords.tolist())
    
    # 生成GeoJSON Feature
    geojson_poly = [coords.tolist()] + interiors
    features.append(Feature(
        geometry=Polygon(geojson_poly),
        properties={"lower": lower, "upper": upper, "time": time_str}
    ))


def contour_to_geojson(contour, levels, time_str, output):
    #os.makedirs(output_dir, exist_ok=True)
    #output_file = os.path.join(output_dir, f"contour_{time_str}.geojson")
    
    features = []
    filter_reason = {"vertex_count": 0, "lat_range": 0, "lon_range": 0, "neg90": 0, "area": 0}
    vertex_stats = {"original": [], "simplified": []}
    
    for i, collection in enumerate(contour.collections):
        if i + 1 >= len(levels) or not collection.get_paths():  # 提前过滤空集合
            continue
        
        lower = round(levels[i], 2)
        upper = round(levels[i+1], 2)
        
        for path in collection.get_paths():
            polygons = path.to_polygons()
            if not polygons:
                continue
            
            # 解析外环与内环
            exterior = polygons[0]
            interiors = polygons[1:] if len(polygons) > 1 else []
            
            # 过滤顶点数不足的外环
            if len(exterior) < 3:
                filter_reason["vertex_count"] += 1
                continue
            
            # 闭合外环
            if not np.allclose(exterior[0], exterior[-1], atol=1e-2):
                exterior = np.vstack([exterior, exterior[0]])
            
            # 处理内环（过滤无效内环）
            shapely_interiors = []
            for interior in interiors:
                if len(interior) < 3:
                    continue
                if not np.allclose(interior[0], interior[-1], atol=1e-2):
                    interior = np.vstack([interior, interior[0]])
                shapely_interiors.append(interior)
            
            # Shapely处理几何（简化+验证）
            try:
                shapely_poly = ShapelyPolygon(exterior, shapely_interiors)
                if not shapely_poly.is_valid:
                    shapely_poly = make_valid(shapely_poly)
                
                # 处理MultiPolygon
                if shapely_poly.geom_type == "MultiPolygon":
                    merged_poly = unary_union(shapely_poly)
                    if merged_poly.geom_type == "MultiPolygon":
                        for sub_poly in merged_poly.geoms:
                            process_sub_poly(sub_poly, lower, upper, time_str, features, filter_reason, vertex_stats)
                        continue
                    shapely_poly = merged_poly
                
                # 简化多边形
                shapely_poly_simplified = shapely_poly.simplify(
                    SIMPLIFY_TOLERANCE, 
                    preserve_topology=True
                )
                
                if shapely_poly_simplified.is_empty:
                    filter_reason["vertex_count"] += 1
                    continue
                
                # 处理单个有效多边形
                process_sub_poly(shapely_poly_simplified, lower, upper, time_str, features, filter_reason, vertex_stats)
            
            except Exception as e:
                filter_reason["vertex_count"] += 1
                continue
    # ujson写入GeoJSON
    with open(output, 'w', encoding='utf-8') as f:
        ujson.dump(FeatureCollection(features), f, indent=2)
    
    # 打印统计信息
    total_filtered = sum(filter_reason.values())
    print(f"\n=== GeoJSON生成完成 ===")
    print(f"  文件路径：{output}")
    print(f"  保留多边形数量：{len(features)}")
    print(f"  总过滤多边形数量：{total_filtered}")
    print(f"  过滤原因分布：")
    for reason, count in filter_reason.items():
        print(f"    - {reason}: {count}个（{count/total_filtered*100:.1f}%）" if total_filtered > 0 else f"    - {reason}: {count}个")
    print(f"  顶点数统计：")
    print(f"    - 原始多边形顶点数：平均{np.mean(vertex_stats['original']):.1f}个，最小{np.min(vertex_stats['original']):.0f}个")
    print(f"    - 简化后多边形顶点数：平均{np.mean(vertex_stats['simplified']):.1f}个，最小{np.min(vertex_stats['simplified']):.0f}个")
    
    return output


def convert_time_to_string(time_val, time_units):
    if not time_units or 'since' not in time_units:
        return f"t{int(time_val)}"
    
    try:
        base_str = time_units.split('since')[-1].strip()
        base_date = datetime.strptime(base_str, "%Y-%m-%d %H:%M:%S")
        unit = time_units.split('since')[0].strip().lower()
        
        # 简化时间delta计算
        delta = timedelta(hours=int(time_val)) if 'hour' in unit else timedelta(minutes=int(time_val))
        return (base_date + delta).strftime("%Y%m%d%H%M")
    except Exception as e:
        print(f"时间转换错误: {e}")
        return f"t{int(time_val)}"


def process_rain(grib_file_path, output, variable_name="apcp", custom_levels=[0.1, 1, 10, 25, 50, 75, 90, 95, 100]):
    # 可修改为处理多个时间步（如 range(0, 5) 处理前5个时间步）
    target_time_indices = [0]  
    
    # 读取NC文件
    start_read_nc =time.perf_counter()

    data_3d, lon_1d, lat_1d, times, time_units = read_grib_file(grib_file_path, variable_name)
    end_read_nc = time.perf_counter()
    print(f"读取NC文件时间: {end_read_nc - start_read_nc} 秒")


    if data_3d is None:
        return
    
    # 单进程循环处理目标时间步（核心：取消多进程，改用for循环）
    for time_idx in target_time_indices:
        data_2d = data_3d
        time_str = convert_time_to_string(times[time_idx], time_units)
        print(f"\n=== 处理时间步 {time_idx}（{time_str}）===")
        print(f"原始2D数据形状：{data_2d.shape}（lat × lon）")
        
        # 纬度裁剪
        try:
            lon_clipped, lat_clipped, data_clipped = clip_to_web_merc_lat(lon_1d, lat_1d, data_2d)
        except ValueError as e:
            print(f"时间步 {time_idx} 裁剪失败：{e}")
            continue
        
        # 生成等值线
        contour, levels = calculate_contours_with_boundary(lon_clipped, lat_clipped, data_clipped, custom_levels)
        if contour is None:
            print(f"时间步 {time_idx} 无有效数据生成等值线")
            continue
        
        # 转换为GeoJSON
        start_geojson = time.perf_counter()
        print(output)
        contour_to_geojson(contour, levels, time_str, output)
        end_geojson = time.perf_counter()
        print(f"生成GeoJSON时间: {end_geojson - start_geojson} 秒")