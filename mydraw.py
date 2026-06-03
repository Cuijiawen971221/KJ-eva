import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cartopy.crs as ccrs
from pyproj import Transformer

def add_graticule_to_web_mercator(input_image_path, output_image_path, bbox, dpi=100):
    """
    将经纬度标签完全绘制在地图区域内部的函数
    
    参数:
        input_image_path: 输入图片路径
        output_image_path: 输出图片路径
        bbox: 边界框 [minx, miny, maxx, maxy] (EPSG:3857 坐标)
        dpi: 输出图片的DPI
    """
    # 打开图片
    img = Image.open(input_image_path)
    width, height = img.size
    
    # 创建图形（完全匹配图片尺寸）
    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Mercator())
    
    # 隐藏所有边框和空白
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    
    # 坐标转换
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326")
    min_lon, min_lat = transformer.transform(bbox[0], bbox[1])
    max_lon, max_lat = transformer.transform(bbox[2], bbox[3])
    
    # 设置地图范围
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    
    # 添加底图（确保完全填充）
    ax.imshow(img, extent=[min_lon, max_lon, min_lat, max_lat], transform=ccrs.PlateCarree(), origin='upper', zorder=0)
    
    # 计算经纬网间隔
    lat_step = max(0.5, round((max_lat - min_lat)/5, 1))
    lon_step = max(0.5, round((max_lon - min_lon)/10, 1))
    
    # 生成网格线位置（确保在范围内）
    lon_lines = np.arange(np.floor(min_lon/lon_step)*lon_step, 
                         np.ceil(max_lon/lon_step)*lon_step + lon_step, 
                         lon_step)
    lat_lines = np.arange(np.floor(min_lat/lat_step)*lat_step,
                         np.ceil(max_lat/lat_step)*lat_step + lat_step,
                         lat_step)
    
    # 添加网格线（不显示默认标签）
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=False,
        linewidth=0.5,
        color='gray',
        alpha=0.5,
        linestyle='--',
        xlocs=lon_lines,
        ylocs=lat_lines
    )
    
    # 手动添加标签到地图内部
    label_offset = 0.02  # 标签与边界的偏移量（度）
    
    # 添加经度标签（底部）
    for lon in lon_lines:
        if min_lon <= lon <= max_lon:
            ax.text(lon, min_lat + label_offset, f"{lon:.1f}°E",
                   ha='center', va='bottom', fontsize=8,
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.5),
                   transform=ccrs.PlateCarree())
    
    # 添加纬度标签（左侧）
    for lat in lat_lines:
        if min_lat <= lat <= max_lat:
            ax.text(min_lon + label_offset, lat, f"{lat:.1f}°N",
                   ha='left', va='center', fontsize=8,
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.5),
                   transform=ccrs.PlateCarree())
    
    # 保存图片（完全无白边）
    plt.savefig(output_image_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
    plt.close()

if __name__ == "__main__":
    # 坐标转换（注意顺序：经度,纬度）
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
    
    # 左上角 (59.831°E, 22.472°N)
    x1, y1 = transformer.transform(59.831, 22.472)
    
    # 右下角 (77.322°E, 8.277°N)
    x2, y2 = transformer.transform(77.322, 8.277)
    
    # bbox顺序：[minx, miny, maxx, maxy]
    bbox = [min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)]
    
    add_graticule_to_web_mercator("map.png", "output.png", bbox)