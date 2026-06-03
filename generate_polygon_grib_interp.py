import os
import numpy as np
import ujson
from geojson import Feature, FeatureCollection, Polygon
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.colors import LinearSegmentedColormap
import time
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid
from shapely.ops import unary_union
import xarray as xr
# 新增：用于2D插值的库
from scipy.interpolate import RegularGridInterpolator  # 高效网格插值
import pygrib

# 全局配置（新增插值倍数参数）
VALID_LAT_MIN = -85.1
VALID_LAT_MAX = 85.1
FILTER_NEG90_THRESHOLD = -89.9
WEB_MERC_MIN_LAT = round(-85.05112877980659, 2)
WEB_MERC_MAX_LAT = round(85.05112877980659, 2)
SIMPLIFY_TOLERANCE = 0.02
MIN_POLYGON_AREA = 1
COORD_PRECISION = 4
INTERP_SCALE = 2  # 分辨率放大倍数（1=原分辨率，2=2倍，3=3倍）


def interpolate_resolution(lon_1d, lat_1d, data_2d, scale=INTERP_SCALE):
    """新增：分辨率放大插值函数
    功能：将原2D数据（lat×lon）的经纬度网格点数放大N倍，用插值填充新数据点
    参数：
        lon_1d: 原经度数组（1D）
        lat_1d: 原纬度数组（1D）
        data_2d: 原2D数据（lat×lon）
        scale: 放大倍数（默认2倍）
    返回：
        new_lon: 放大后的经度数组
        new_lat: 放大后的纬度数组
        new_data: 放大后的2D数据（lat×scale × lon×scale）
    """
    if scale <= 1:
        print("插值倍数≤1，无需插值，返回原数据")
        return lon_1d, lat_1d, data_2d

    print(f"\n=== 开始分辨率放大（{scale}倍）===")
    print(f"原数据形状：{data_2d.shape}（lat×lon），原经纬度点数：lat={len(lat_1d)}, lon={len(lon_1d)}")

    # 1. 生成新的高分辨率经纬度网格（保持原范围，仅增加点数）
    # 经度：原范围[-180, 180]，点数=原点数×scale
    new_lon = np.linspace(lon_1d.min(), lon_1d.max(), len(lon_1d) * scale)
    # 纬度：原范围[lat_min, lat_max]，点数=原点数×scale（保持纬度从高到低/低到高的顺序）
    new_lat = np.linspace(lat_1d.min(), lat_1d.max(), len(lat_1d) * scale)
    # 若原纬度是从高到低（如90°→-90°），调整新纬度顺序一致
    if lat_1d[0] > lat_1d[-1]:
        new_lat = new_lat[::-1]

    # 2. 准备插值函数（使用双线性插值，平衡精度和速度）
    # RegularGridInterpolator要求输入网格为“从低到高”，需确保原经纬度顺序正确
    # 处理纬度顺序：若原纬度从高到低，反转后用于插值（内部计算需低→高）
    lat_for_interp = lat_1d if lat_1d[0] < lat_1d[-1] else lat_1d[::-1]
    data_for_interp = data_2d if lat_1d[0] < lat_1d[-1] else data_2d[::-1, :]  # 同步反转数据

    # 创建插值器（method='linear'=双线性插值，fill_value=np.nan=缺失值处填NaN）
    interp = RegularGridInterpolator(
        points=(lat_for_interp, lon_1d),  # 插值网格（lat, lon）
        values=data_for_interp,           # 插值数据（需与points顺序一致）
        method='linear',
        bounds_error=False,               # 超出原范围的点不报错
        fill_value=np.nan                 # 超出范围的点填NaN
    )

    # 3. 生成新网格的坐标对（所有(lat, lon)组合）
    new_lat_grid, new_lon_grid = np.meshgrid(new_lat, new_lon, indexing='ij')  # indexing='ij'确保(lat, lon)顺序
    points = np.stack([new_lat_grid.ravel(), new_lon_grid.ravel()], axis=1)  # 展平为N×2的坐标对

    # 4. 执行插值（生成新数据）
    start_interp = time.perf_counter()
    new_data = interp(points).reshape(new_lat_grid.shape)  # 重塑为新网格形状（lat×lon）
    end_interp = time.perf_counter()

    # 5. 后处理：确保新数据无负数值（降水非负），保留原数据精度
    new_data = np.where(np.isnan(new_data) | (new_data < 0), np.nan, new_data).astype(np.float32)
    new_lon = np.round(new_lon, COORD_PRECISION).astype(np.float32)
    new_lat = np.round(new_lat, COORD_PRECISION).astype(np.float32)

    print(f"插值完成！耗时：{end_interp - start_interp:.2f}秒")
    print(f"新数据形状：{new_data.shape}（lat×lon），新经纬度点数：lat={len(new_lat)}, lon={len(new_lon)}")
    return new_lon, new_lat, new_data


def clip_to_web_merc_lat(lon_1d, lat_1d, data_2d):
    """原逻辑不变（适配插值后的高分辨率数据）"""
    valid_lat_mask = (lat_1d >= WEB_MERC_MIN_LAT) & (lat_1d <= WEB_MERC_MAX_LAT)
    valid_lat_indices = np.where(valid_lat_mask)[0]
    
    if len(valid_lat_indices) == 0:
        raise ValueError(f"无有效纬度数据！Web Mercator仅支持 {WEB_MERC_MIN_LAT:.2f} ~ {WEB_MERC_MAX_LAT:.2f}")
    
    clipped_lat = lat_1d[valid_lat_indices]
    clipped_data = data_2d[valid_lat_indices, :]
    
    print(f"\nWeb Mercator纬度裁剪完成：")
    print(f"  原始纬度范围：{lat_1d.min():.2f} ~ {lat_1d.max():.2f}")
    print(f"  裁剪后纬度范围：{clipped_lat.min():.2f} ~ {clipped_lat.max():.2f}")
    print(f"  裁剪前数据形状：{data_2d.shape}（lat × lon）")
    print(f"  裁剪后数据形状：{clipped_data.shape}（lat × lon）")
    
    return lon_1d, clipped_lat, clipped_data


def read_grib_file(file_path):##, variable_name="tp"):
    """原逻辑不变（读取后的数据将传入插值函数）"""
    try:
   # if True:
       # print(file_path)
       # grbs = pygrib.open(file_path)
       # for grb in grbs:
       #     print(grb)
       # if grb.shortName == 'tp':
       #     latlon_   = pygrib.open(file_path).select(shortName = 'tp')[0].latlons()
       #     grb_value = pygrib.open(file_path).select(shortName = 'tp')[0].values
       # elif grb.shortName == 'prate':
       #     latlon_   = pygrib.open(file_path).select(shortName = 'prate')[0].latlons()
       #     grb_value = pygrib.open(file_path).select(shortName = 'prate')[0].values
       # print(grb)
        
        ds = xr.open_dataset(
            file_path,
            engine="cfgrib",
            decode_times=True
            )
       # print(f"GRIB文件读取成功！变量 {variable_name} 信息：")
       # print(f"  数据维度：{ds[variable_name].dims}")
       # print(f"  数据形状：{ds[variable_name].shape}")
        if 'prate' in ds.variables.keys():
            variable_name = 'prate'
        else:
            variable_name = 'tp'
        print('variable_name=',variable_name)
        data_2d = ds[variable_name].values.astype(np.float32)
        data_2d = np.where(np.isnan(data_2d) | (data_2d < 0), np.nan, data_2d)
        #lat_1d = latlon_[0][:,0]# if "latitude" in ds.coords else ds["lat"].values
        #lon_1d = latlon_[1][0,:]# if "longitude" in ds.coords else ds["lon"].value

        lat_1d = ds["latitude"].values if "latitude" in ds.coords else ds["lat"].values
        lon_1d = ds["longitude"].values if "longitude" in ds.coords else ds["lon"].values
        
        lon_1d = np.where(lon_1d > 180, lon_1d - 360, lon_1d)
        lat_1d = np.round(lat_1d, COORD_PRECISION).astype(np.float32)
        lon_1d = np.round(lon_1d, COORD_PRECISION).astype(np.float32)

        sorted_lon_idx = np.argsort(lon_1d)
        lon_1d = lon_1d[sorted_lon_idx]
        data_2d = data_2d[:, sorted_lon_idx]

        if not np.isclose(lon_1d[0], -180.0, atol=1e-2):
            print(f"\n检测到无-180°数据，复制180°数据补充...")
            idx_180 = np.argmin(np.abs(lon_1d - 180.0))
            data_col_180 = data_2d[:, idx_180:idx_180+1]
            lon_1d = np.insert(lon_1d, 0, round(-180.0, COORD_PRECISION))
            data_2d = np.concatenate([data_col_180, data_2d], axis=-1)
            print(f"  补充后经度范围：{lon_1d.min():.2f} ~ {lon_1d.max():.2f}")
            print(f"  补充后数据形状：{data_2d.shape}（lat × lon）")

        times = None
        time_units = None
        if "time" in ds.coords:
            times = np.atleast_1d(ds["time"].values)
            time_units = f"hours since {ds['time'].attrs.get('units', '1900-01-01 00:00:00')}"
            print(f"  数据时间：{times[0]}")
        else:
            print(f"  提示：GRIB文件无内置时间维度，从文件名提取时间")
            import re
            time_match = re.search(r'(\d{10})', file_path)
            if time_match:
                times = np.array([np.datetime64(time_match.group(1)[:8] + 'T' + time_match.group(1)[8:10] + ':00')])
                time_units = "hours since 1970-01-01 00:00:00"
                print(f"  从文件名提取时间：{times[0]}")
            else:
                current_time = datetime.utcnow().strftime("%Y%m%d%H%M")
                times = np.array([np.datetime64(current_time[:8] + 'T' + current_time[8:10] + ':00')])
                print(f"  无法提取时间，使用当前UTC时间：{times[0]}")

        ds.close()
        return data_2d, lon_1d, lat_1d, times, time_units

    except Exception as e:
        print(f"GRIB文件读取错误: {str(e)}")
        print("提示：1. 检查GRIB文件路径；2. 确认变量名（如ECMWF降水为'tp'）；3. 确保已安装ecCodes")
        return None, None, None, None, None


def calculate_contours_with_boundary(lon_1d, lat_1d, data_2d, levels=None):
    """原逻辑不变（适配高分辨率数据，等值线更平滑）"""
    plt.ioff()
    data_clean = np.where(np.isnan(data_2d), np.nan, data_2d).astype(np.float32)
    X, Y = np.meshgrid(lon_1d, lat_1d)

    if levels is None:
        valid_data = data_clean[~np.isnan(data_clean)]
        if len(valid_data) == 0:
            print("无有效数据，无法生成等值线")
            return None, []
        
        precip_min = max(0, np.min(valid_data))
        precip_max = np.max(valid_data)
        
        if precip_min == precip_max:
            levels = [precip_min, precip_min + 0.1]
        else:
            # 插值后数据更密集，可增加层级细分（如0~50mm分15段）
            levels = np.linspace(precip_min, min(precip_max, 100), 15)  # 重点覆盖低降水区间
            levels = np.unique(np.round(levels, 2))
        print(f"自动生成等值线层级: {levels}")
    else:
        print(f"使用自定义等值线层级: {levels}（共 {len(levels)-1} 个区间）")

    num_intervals = len(levels) - 1
    colors = ['#e0f7fa', '#80deea', '#4db6ac', '#81c784', '#dce775', '#ffb74d', '#ff8a65', '#ef5350', '#b71c1c']
    if len(colors) < num_intervals:
        colors = colors * (num_intervals // len(colors) + 1)[:num_intervals]

    cmap = LinearSegmentedColormap.from_list('precip_cmap', colors, N=num_intervals)
    start_contour = time.perf_counter()
    # 高分辨率数据可增加antialiased=True（抗锯齿），让等值线更平滑
    contour = plt.contourf(X, Y, data_clean, levels=levels, cmap=cmap, alpha=0.8, antialiased=True)
    end_contour = time.perf_counter()
    print(f"等值线生成耗时: {end_contour - start_contour:.2f} 秒")

    plt.close()
    return contour, levels


# process_sub_poly、contour_to_geojson、convert_time_to_string 函数原逻辑不变
def process_sub_poly(shapely_poly, lower, upper, time_str, features, filter_reason, vertex_stats):
    poly_area = shapely_poly.area
    print('area:', area)
    if poly_area < MIN_POLYGON_AREA:
        filter_reason["area"] += 1
        return

    coords = np.round(np.array(shapely_poly.exterior.coords), COORD_PRECISION)
    lons, lats = coords[:, 0], coords[:, 1]

    if all(lat > VALID_LAT_MAX + 1e-3 for lat in lats) or all(lat < VALID_LAT_MIN - 1e-3 for lat in lats):
        filter_reason["lat_range"] += 1
        return
    if any(lat <= FILTER_NEG90_THRESHOLD for lat in lats):
        filter_reason["neg90"] += 1
        return
    if np.max(lons) > 180 + 1e-3 or np.min(lons) < -180 - 1e-3:
        filter_reason["lon_range"] += 1
        return

    simplified_vertices = len(coords)
    original_vertices = len(np.array(shapely_poly.exterior.coords))
    if simplified_vertices < 3:
        filter_reason["vertex_count"] += 1
        return

    vertex_stats["original"].append(original_vertices)
    vertex_stats["simplified"].append(simplified_vertices)

    interiors = []
    for interior in shapely_poly.interiors:
        interior_coords = np.round(np.array(interior.coords), COORD_PRECISION)
        if len(interior_coords) >= 3:
            interiors.append(interior_coords.tolist())

    geojson_poly = [coords.tolist()] + interiors
    features.append(Feature(
        geometry=Polygon(geojson_poly),
        #properties={"lower": lower, "upper": upper, "time": time_str, "unit": "mm"}
        properties={"val": lower}
    ))


def contour_to_geojson(contour, levels, time_str, output_dir="contour_grib_interp"):
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"contour_{time_str}.geojson")
    
    features = []
    filter_reason = {"vertex_count": 0, "lat_range": 0, "lon_range": 0, "neg90": 0, "area": 0}
    vertex_stats = {"original": [], "simplified": []}
    
    for i, collection in enumerate(contour.collections):
        if i + 1 >= len(levels) or not collection.get_paths():
            continue
        
        lower = round(levels[i], 2)
        upper = round(levels[i+1], 2)
        
        for path in collection.get_paths():
            polygons = path.to_polygons()
            if not polygons:
                continue
            
            exterior = polygons[0]
            interiors = polygons[1:] if len(polygons) > 1 else []
            
            if len(exterior) < 3:
                filter_reason["vertex_count"] += 1
                continue
            
            if not np.allclose(exterior[0], exterior[-1], atol=1e-2):
                exterior = np.vstack([exterior, exterior[0]])
            
            shapely_interiors = []
            for interior in interiors:
                if len(interior) < 3:
                    continue
                if not np.allclose(interior[0], interior[-1], atol=1e-2):
                    interior = np.vstack([interior, interior[0]])
                shapely_interiors.append(interior)
            
            try:
                shapely_poly = ShapelyPolygon(exterior, shapely_interiors)
                if not shapely_poly.is_valid:
                    shapely_poly = make_valid(shapely_poly)
                
                if shapely_poly.geom_type == "MultiPolygon":
                    merged_poly = unary_union(shapely_poly)
                    if merged_poly.geom_type == "MultiPolygon":
                        for sub_poly in merged_poly.geoms:
                            process_sub_poly(sub_poly, lower, upper, time_str, features, filter_reason, vertex_stats)
                        continue
                    shapely_poly = merged_poly
                
                shapely_poly_simplified = shapely_poly.simplify(
                    SIMPLIFY_TOLERANCE,
                    preserve_topology=True
                )
                
                if shapely_poly_simplified.is_empty:
                    filter_reason["vertex_count"] += 1
                    continue
                
                process_sub_poly(shapely_poly_simplified, lower, upper, time_str, features, filter_reason, vertex_stats)
            
            except Exception as e:
                filter_reason["vertex_count"] += 1
                continue
    
    with open(output_file, 'w', encoding='utf-8') as f:
        ujson.dump(FeatureCollection(features), f, ensure_ascii=False)
    
    total_filtered = sum(filter_reason.values())
    print(f"\n=== GeoJSON生成完成 ===")
    print(f"  文件路径：{output_file}")
    print(f"  保留多边形数量：{len(features)}")
    print(f"  总过滤多边形数量：{total_filtered}")
    if total_filtered > 0:
        for reason, count in filter_reason.items():
            print(f"    - {reason}: {count}个（{count/total_filtered*100:.1f}%）")
    print(f"  顶点数统计：")
    if vertex_stats["original"]:
        print(f"    - 原始顶点数：平均{np.mean(vertex_stats['original']):.1f}个，最小{np.min(vertex_stats['original']):.0f}个")
        print(f"    - 简化后顶点数：平均{np.mean(vertex_stats['simplified']):.1f}个，最小{np.min(vertex_stats['simplified']):.0f}个")
    
    return output_file


def convert_time_to_string(time_val, time_units):
    if isinstance(time_val, np.datetime64):
        dt = datetime.utcfromtimestamp((time_val - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's'))
        return dt.strftime("%Y%m%d%H%M")
    
    if not time_units or 'since' not in time_units:
        return f"t{int(time_val)}"
    
    try:
        base_str = time_units.split('since')[-1].strip()
        base_date = datetime.strptime(base_str, "%Y-%m-%d %H:%M:%S")
        unit = time_units.split('since')[0].strip().lower()
        
        delta = timedelta(hours=int(time_val)) if 'hour' in unit else timedelta(minutes=int(time_val))
        return (base_date + delta).strftime("%Y%m%d%H%M")
    except Exception as e:
        print(f"时间转换错误: {e}")
        return f"t{int(time_val)}"


def main():
    """主函数：新增插值步骤（读取数据后→插值→裁剪→等值线）"""
    # 用户需调整的参数
   #grib_file_path = "fcst2025050100024.grb"  # 你的GRIB文件路径
    grib_file_path ="/home/user/workshop/met/met_backend/fcst/KT1279/rain/rain24/fcst2025090100024.grb"
    #variable_name = "prate"  # 变量名（降水：tp；2米气温：t2m）
    # 自定义层级：重点细分/0~50mm（插值后数据足够密集，支持更多层级）
    custom_levels = [0.1, 10, 25, 50, 100, 250, 1000] 

    # 1. 读取GRIB文件（2D数据）
    start_read = time.perf_counter()
    data_2d, lon_1d, lat_1d, times, time_units = read_grib_file(grib_file_path)#, variable_name)
    end_read = time.perf_counter()
    print(f"\nGRIB文件读取耗时: {end_read - start_read:.2f} 秒")

    if data_2d is None:
        print("程序终止：GRIB文件读取失败")
        return
    print('lon_1d',len(lon_1d))
    #if len(lon_1d) > 721 :
        #INTERP_SCALE = 1
    # 2. 新增：分辨率放大插值（关键步骤）
    lon_interp, lat_interp, data_interp = interpolate_resolution(lon_1d, lat_1d, data_2d, scale=INTERP_SCALE)

    # 3. 处理时间字符串
    time_str = convert_time_to_string(times[0], time_units)
    print(f"\n=== 开始处理数据（时间：{time_str}）===")
    print(f"插值后数据形状：{data_interp.shape}（lat × lon）")

    # 4. 纬度裁剪（使用插值后的高分辨率数据）
    try:
        lon_clipped, lat_clipped, data_clipped = clip_to_web_merc_lat(lon_interp, lat_interp, data_interp)
    except ValueError as e:
        print(f"数据裁剪失败：{e}")
        return

    # 5. 生成等值线（高分辨率数据让等值线更连续）
    contour, levels = calculate_contours_with_boundary(lon_clipped, lat_clipped, data_clipped, custom_levels)
    if contour is None:
        print("无有效等值线数据")
        return

    # 6. 转换为GeoJSON
    start_geojson = time.perf_counter()
    contour_to_geojson(contour, levels, time_str)
    end_geojson = time.perf_counter()
    print(f"GeoJSON生成耗时: {end_geojson - start_geojson:.2f} 秒")


if __name__ == "__main__":
    total_start = time.perf_counter()
    main()
    total_end = time.perf_counter()
    print(f"\n=== 程序总耗时: {total_end - total_start:.2f} 秒 ===")
