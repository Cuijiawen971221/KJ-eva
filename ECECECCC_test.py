import os
import pygrib
import subprocess
from datetime import datetime
import sys

def extract_time_code(filename):
    """
    从文件名中提取时间编码部分（例如 '050100000501'）
    文件名格式示例：W_NAFP_C_ECMF_20250501050643_P_C1D05010000050100001.grib2
    """
    # 找到 'P_C1D' 后面的部分
    p_c1d_index = filename.find('P_C1D')
    if p_c1d_index == -1:
        raise ValueError("文件名中未找到 'P_C1D' 标识")

    # 提取 '05010000050100001' 部分（跳过 'P_C1D' 的5个字符）
    time_part = filename[p_c1d_index + 5:]

    # 去掉末尾的 '00001' 或类似编号，保留前12位作为时间编码
    time_code = time_part[:14]

    if len(time_code) != 14:
        raise ValueError("时间编码部分长度不足12位")
    yr = filename[14:18]
    time_start = yr+time_code[0:6]
    return time_code,time_start


def parse_time_diff(time_code):
    """
    解析时间编码（格式：mmddhh00mmddhh），计算时间差（小时）
    """
    print(time_code)
    # 提取起始时间（前6位）和截止时间（后6位，跳过中间的'00'）
    start_str = time_code[:6]  # mmddhh
    end_str = time_code[8:]  # mmddhh
    print(start_str,end_str)
    # 转换为 datetime 对象
    start_time = datetime.strptime(start_str, "%m%d%H")
    end_time = datetime.strptime(end_str, "%m%d%H")

    # 计算时间差（小时）
    delta = end_time - start_time
    return delta.total_seconds() / 3600



def grb2_to_grb_ec(inpath,input_file,cdo_path,outpath):
    # 1. 提取时间编码
    time_code,time_start = extract_time_code(input_file)
    hours_diff = parse_time_diff(time_code)
    path1 = os.getcwd()
    temp_dir = f"{path1}/temp_gribs"
    resampled_dir = f"{path1}/resampled_gribs"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(resampled_dir, exist_ok=True)

    # 定义目标网格文件 (mygrid)
    grid_file = f"{path1}/mygrid.txt"
    with open(grid_file, "w") as f:
        f.write("""# 0.25度全球网格
    gridtype = lonlat
    xsize    = 361
    ysize    = 281
    xfirst   = 0
    xinc     = 0.25
    yfirst   = -10
    yinc     = 0.25
    """)

    # 打开GRIB文件并提取要素
    grbs = pygrib.open(input_file)
    unique_parameters = [
        'Relative humidity', '10 metre V wind component', 'Specific humidity',
        '2 metre dewpoint temperature', 'Natural logarithm of pressure in Pa',
        'Geopotential Height', 'Sea surface temperature', 'V component of wind',
        'Surface pressure', '10 metre U wind component', '2 metre temperature',
        'Skin temperature', 'Mean sea level pressure', 'Total column water vapour',
        'Low cloud cover (', 'Divergence', 'Geopotential', 'Total cloud cover (',
        'Fraction of cloud cover', 'Vertical velocity', 'Potential vorticity',
        'Temperature', 'U component of wind'
    ]

    # 分要素保存为临时文件
    for param in unique_parameters:
        grbs.seek(0)
        selected_messages = grbs.select(parameterName=param)
        if not selected_messages:
            print(f"No data found for {param}, skipping.")
            continue

        # 处理特殊参数名
        clean_param = param.replace(' ', '_').replace('(', '').replace(')', '')
        output_file = os.path.join(temp_dir, f"{clean_param}.grb")

        with open(output_file, 'wb') as fout:
            for msg in selected_messages:
                fout.write(msg.tostring())
        print(f"Saved {param} to {output_file}")

    # 对每个文件进行重采样
    for param in unique_parameters:
        clean_param = param.replace(' ', '_').replace('(', '').replace(')', '')
        input_grib = os.path.join(temp_dir, f"{clean_param}.grb")
        output_grib = os.path.join(resampled_dir, f"{clean_param}_025.grb")

        if not os.path.exists(input_grib):
            continue
        os.chdir(cdo_path)
        cmd = f"./cdo remapbil,{grid_file} {input_grib} {output_grib}"
        subprocess.run(cmd, shell=True, check=True)

    min_lj = str(int(hours_diff)*60).zfill(5)
    # 合并所有重采样后的文件
    merged_file = f"{outpath}/ecfc.0p15.region.{timestart}.f{min_lj}"###"merged_resampled.grb"    intime,min_lj
    resampled_files = [os.path.join(resampled_dir, f) for f in os.listdir(resampled_dir) if f.endswith(".grb")]
    if resampled_files:
        cmd = f"./cdo mergetime {' '.join(resampled_files)} {merged_file}"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Merged files to {merged_file}")

    # 清理临时文件 (可选)
    cleanup = True
    if cleanup:
        import shutil

        shutil.rmtree(temp_dir)
        shutil.rmtree(resampled_dir)
        os.remove(grid_file)
        print("Temporary files deleted.")

    print("Processing complete!")

if __name__=="__main__":
    inpath = sys.argv[1]#'/home/cuijiawen/cuijiawen/'
    outpath = sys.argv[2]#'/home/cuijiawen/cuijiawen/grb/'
    input_filename = 'W_NAFP_C_ECMF_20250501050643_P_C1D05010000050100001'
    cdo_path = '/home/soft/cdo/bin'
    grb2_to_grb_ec(inpath, input_filename, cdo_path, outpath)




