import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cartopy.crs as ccrs
from pyproj import Transformer
from PIL import Image

def add_graticule_to_web_mercator(input_image_path, output_image_path, bbox, dpi=None):
    """
    最终修正版：严格保持输入输出图片尺寸一致
    
    参数变化：
        dpi: 改为可选参数，默认使用输入图片的DPI
    注意：如果经度是 160-220这种，  给他减去180运算， 然后显示经度label是做个标签变换
    """

    # 打开图片并获取原始DPI
    img = Image.open(input_image_path)
    width, height = img.size
    if dpi is None:
        dpi = img.info.get('dpi', (100, 100))[0]  # 获取原始DPI，默认100
    
    # 创建图形（关键修改1：使用物理尺寸确保1:1像素匹配）
    fig = plt.figure(
        figsize=(width/dpi, height/dpi),
        dpi=dpi,
        frameon=False
    )
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Mercator())
    ax.set_axis_off()
    
    # 坐标转换
   
    min_lat,min_lon  =(bbox[1] , bbox[0])
    max_lat,max_lon = (bbox[3],  bbox[2])
    print (f'min_lon:{min_lon},   max_lon:{max_lon},min_lat:{min_lat}, max_lat:{max_lat}')
    converted = False 
    if min_lon < 180 and max_lon > 180:
        converted=True
        min_lon =min_lon -180
        max_lon =max_lon -180
        
    
    
    # 设置地图范围（使用原始bbox确保比例正确）
    ax.set_extent([
        min_lon, max_lon,
        min_lat, max_lat
    ], crs=ccrs.PlateCarree())
    
#    ax.imshow(
#        img, 
#        extent=[bbox[0], bbox[2], bbox[1], bbox[3]],  # 使用Web Mercator坐标
#        transform=ccrs.Mercator(),  # 指定图像数据使用Web Mercator投影
#        origin='upper', 
#        zorder=0,
#        interpolation='none'
#    )    
    


    
    # 自动网格分辨率（5°或10°）
    def auto_step (span):
        """根据经纬度跨度自动选择合适的间隔"""
        if span > 60: # 跨度大于 60° 时使用 20° 间隔
            return 20
        elif span > 30: # 跨度 30°-60° 时使用 10° 间隔
            return 10
        else: # 跨度小于等于 30° 时使用 5° 间隔
            return 5
    
    lon_step = auto_step(max_lon - min_lon)
    lat_step = auto_step(max_lat - min_lat)
    
    # 计算网格线位置
    lon_lines = np.arange(
        np.floor(min_lon/lon_step)*lon_step,
        np.ceil(max_lon/lon_step)*lon_step + lon_step,
        lon_step
    )
    lon_lines = [x - 360 if x > 180 else x for x in lon_lines]
    print(lon_lines)
    
    lat_lines = np.arange(
        np.floor(min_lat/lat_step)*lat_step,
        np.ceil(max_lat/lat_step)*lat_step + lat_step,
        lat_step
    )
    print(lat_lines)
    # 添加网格线
    gl=ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=False,
        linewidth=0.5,
        color='gray',
        alpha=0.5,
        linestyle='-.',
        xlocs=lon_lines,
        ylocs=lat_lines
    )
    gl.xlim = (min_lon, max_lon)  # 限制经线范围
    gl.ylim = (min_lat, max_lat)  # 限制纬线范围
    
    # 标签位置控制
    label_lon_offset = (max_lon - min_lon) * 0.015
    label_lat_offset = (max_lat - min_lat) * 0.015
    
    # 添加标签（透明背景）
    for lon in lon_lines:
        if min_lon + lon_step/10 <= lon <= max_lon - lon_step/10:
            lon_dir = 'E' if lon+180 <= 180 else 'W'
            lon_label = f"{abs(int(lon+180 if lon+180<=180 else 360- (lon+180) ))}°{lon_dir}"        
            ax.text(
                lon + label_lon_offset,
                min_lat + label_lat_offset,
                lon_label,
                fontsize=8,
                color='black',
                alpha=0.8,
                ha='center',
                va='bottom',
                transform=ccrs.PlateCarree(),
                zorder=10
            )
    
    for lat in lat_lines:
   
        if min_lat + lat_step/10 <= lat <= max_lat - lat_step/10:
            lat_dir = 'N' if lat >= 0 else 'S'
            lat_label = f"{abs(int(lat))}°{lat_dir}"         
            ax.text(
                min_lon + label_lon_offset,
                lat,
                lat_label,
                fontsize=8,
                color='black',
                alpha=0.8,
                ha='left',
                va='center',
                transform=ccrs.PlateCarree(),
                zorder=10
            )
    
    # 关键修改3：严格尺寸保存
    plt.savefig(
        output_image_path,
        dpi=dpi,
        bbox_inches='tight',  # 禁用自动调整
        pad_inches=0,
        transparent=True,

    )
    plt.close()
    # 用PIL打开并强制调整尺寸
    output_img = Image.open(output_image_path)
    if output_img.size != (width, height):

            output_img = output_img.resize((width, height), Image.LANCZOS)
            output_img = output_img.crop((0, 0, width, height-1))  # 精确剪掉底部1像素
            output_img = output_img.resize((width, height), Image.LANCZOS)
#            output_img.save(output_image_path)
#            return
            top_img = output_img.convert("RGBA")
            
            bottom_img = img.convert("RGBA")
            
            # 合成图片
            composite_img = Image.alpha_composite(bottom_img, top_img)
            composite_img.save(output_image_path)


# 使用示例
if __name__ == "__main__":
    #transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
   

    y1,x1 = (60,160)  # 左上角 必须先纬度后经度
    y2,x2 = (40,220)   # 右下角
  
    
    print(x1, y1) 
    bbox = [min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)]
    #bbox = [min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)]
   # bbox = [ x1, y2,  x2,y1]  # 左, 下, 右, 上
    add_graticule_to_web_mercator("map-cross2.png", "output.png", bbox)