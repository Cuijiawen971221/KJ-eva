import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cartopy.crs as ccrs
from pyproj import Transformer

def add_graticule_to_web_mercator(input_image_path, output_image_path, bbox, dpi=100):
    """
    优化版：彻底消除白边并精确控制标签位置
    
    参数:
        input_image_path: 输入图片路径
        output_image_path: 输出图片路径
        bbox: 边界框 [minx, miny, maxx, maxy] (EPSG:3857 坐标)
        dpi: 输出图片的DPI
    """
    # 打开图片并获取精确尺寸
    img = Image.open(input_image_path)
    width, height = img.size
    
    # 创建图形（关键修改1：禁用所有边框）
    fig = plt.figure(
        figsize=(width/dpi, height/dpi),
        dpi=dpi,
        frameon=False  # 完全禁用图形边框
    )
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Mercator())
    ax.set_axis_off()  # 禁用坐标轴
    
    # 坐标转换
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326")
    min_lon, min_lat = transformer.transform(bbox[0], bbox[1])
    max_lon, max_lat = transformer.transform(bbox[2], bbox[3])
    
    # 设置地图范围（关键修改2：扩大0.5%避免边缘裁剪）
    buffer = 0.005  # 0.5%的缓冲
    ax.set_extent([
        min_lon - buffer, max_lon + buffer,
        min_lat - buffer, max_lat + buffer
    ], crs=ccrs.PlateCarree())
    
    # 添加底图（使用原始Web墨卡托坐标确保对齐）
    ax.imshow(img, extent=[min_lon, max_lon, min_lat, max_lat], 
             transform=ccrs.PlateCarree(), origin='upper', zorder=0)
    
    # 自动网格分辨率（5°或10°）
    def auto_step(span):
        return 10 if span > 30 else 5
    
    lon_step = auto_step(max_lon - min_lon)
    lat_step = auto_step(max_lat - min_lat)
    
    # 计算网格线位置（5/10的整数倍）
    lon_lines = np.arange(
        np.floor(min_lon/lon_step)*lon_step,
        np.ceil(max_lon/lon_step)*lon_step + lon_step,
        lon_step
    )
    lat_lines = np.arange(
        np.floor(min_lat/lat_step)*lat_step,
        np.ceil(max_lat/lat_step)*lat_step + lat_step,
        lat_step
    )
    
    # 添加网格线（不显示默认标签）
    ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=False,
        linewidth=0.5,
        color='gray',
        alpha=0.5,
        linestyle='--',
        xlocs=lon_lines,
        ylocs=lat_lines
    )
    
    # 关键修改3：智能标签位置控制
    def should_skip_label(val, min_val, max_val, step):
        """判断是否跳过靠近边界的标签"""
        margin = step * 0.3  # 30%步长作为边界阈值
        return val < min_val + margin or val > max_val - margin
    
    # 标签偏移设置（动态计算）
    label_lon_offset = (max_lon - min_lon) * 0.015  # 1.5%的水平偏移
    label_lat_offset = (max_lat - min_lat) * 0.015  # 1.5%的垂直偏移

    # 关键修改：透明标签样式
    label_style = {
        'fontsize': 8,
        'color': 'black',  # 黑色文字
        'alpha': 0.8,      # 80%透明度
    }
    
    # 添加经度标签（底部）
    for lon in lon_lines:
        if not should_skip_label(lon, min_lon, max_lon, lon_step):
            ax.text(
                lon + label_lon_offset,  # 向右偏移
                min_lat + label_lat_offset,
                f"{int(lon)}°E",
                **label_style,
                ha='center',
                va='bottom',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0),
                transform=ccrs.PlateCarree(),
            )
    
    # 添加纬度标签（左侧）
    for lat in lat_lines:
        if not should_skip_label(lat, min_lat, max_lat, lat_step):
            ax.text(
                min_lon + label_lon_offset,
                lat,
                f"{int(lat)}°N",
                **label_style,
                ha='left',
                va='center',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0),
                transform=ccrs.PlateCarree(),
            )
    
    # 关键修改4：像素级精确保存
    plt.savefig(
        output_image_path,
        dpi=dpi,
        bbox_inches='tight',
        pad_inches=0,
        transparent=True,
        facecolor='none'  # 确保无背景色
    )
    plt.close()

# 使用示例
if __name__ == "__main__":
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
    # 左上角 (59.831°E, 22.472°N)
    x1, y1 = transformer.transform(59.831, 22.472)
    
    # 右下角 (77.322°E, 8.277°N)
    x2, y2 = transformer.transform(77.322, 8.277)
    bbox = [min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)]
    add_graticule_to_web_mercator("map.png", "output.png", bbox)