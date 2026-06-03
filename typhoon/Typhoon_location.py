import os
import subprocess
import json


def read_json(filen):
    with open(filen,'r',encoding='utf-8') as f:
        result = json.load(f)
    return result

def process_typhoon_location(config_dir,typhoon_mess_path):
    """
    执行台风定位程序
    根据TFB_info.txt中的记录，处理mess_typhoon下的retry文件
ti
    某个方法执行出错时跳过，继续执行下一个方法
    执行完成后更新文件状态和TFB_info.txt
    """
    # 信息文件路径
    info_file = os.path.join(config_dir, 'TFB_info.txt')
    temp_file = os.path.join(config_dir, 'TFB_info_temp.txt')  # 临时文件用于原子更新
    
    # 检查信息文件是否存在
    if not os.path.exists(info_file):
        print(f"配置文件 {info_file} 不存在，无需处理")
        return
    
    # 方法列表，按顺序执行
    methods = ['GVT']#['AI', 'MS', 'DA', 'GVT', 'ML', 'GRAD', 'AUTO']
    # TFB_info.txt
    if True:
        with open(info_file, 'r', encoding='utf-8') as infile, \
             open(temp_file, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                line = line.strip()
                if not line:
                    outfile.write('\n')
                    continue
                
                # 检查是否已完成所有方法（以+++结尾）
                if not line.endswith('+++'):
                    outfile.write(line + '\n')
                    continue
                
                # 解析行内容（格式：文件名, 修改时间, ***）
                parts = [p.strip() for p in line.split(',')]
                print(parts[-1])
                if parts[-1] != '+++':# or (len(parts)==4 and parts[3]=='---'):
                    outfile.write(line + '\n')
                    continue
                print('*****************************************************')
                txt_file = parts[1] # 
                # 提取前10个字符作为文件夹名称
                if len(txt_file) < 10:
                    print(f"文件名 {txt_file} 长度不足10字符，跳过处理")
                    outfile.write(line + '\n')
                    continue
                
                folder_name = txt_file       #[:10]
                mess_path = os.path.join(typhoon_mess_path, folder_name)
                # 检查文件夹是否存在
                #if not os.path.exists(mess_path):
                #    print(f"路径 {mess_path} 不存在，跳过处理 {txt_file}")
                #    outfile.write(line + '\n')
                #    continue
                
                # 跟踪是否所有方法都已执行（无论成功失败）
                all_processed = True
                # 跟踪是否有方法执行成功
                has_successful = False
                
                # 按顺序执行每个方法
                for method in methods:
                    retry_file  = f"{method}.retry"
                    ok_file     = f"{method}.ok"
                    retry_filen = os.path.join(mess_path, retry_file)
                    ok_filen    = os.path.join(mess_path, ok_file)
                    print(retry_filen,ok_filen)
                    # 检查是否需要执行（存在retry文件且不存在ok文件）
                    if True:#os.path.exists(retry_filen) and not os.path.exists(ok_filen):
                        #try:
                        if True:
                            # 执行定位脚本，参数为文件夹名称（yyyymmddhh）和方法名
                            print(f"执行 {method} 方法处理 {txt_file}...{folder_name}")
                            #print(folder_name)
                            ## 执行GVT定位
                            os.chdir('/vol8/home/kongjun/VERIFY/typhoon_his/GVT_orig/EC_codes/')
                            cmd_info = f'yhrun -p test -N 1 sh run_ec_test.sh {folder_name}'
                            os.system(cmd_info)
                            
                            
                            
                            
                            
                            #result = subprocess.run(
                            #    ['yhrun -p test -N 1','sh', '/vol8/home/kongjun/VERIFY/typhoon_his/GVT_orig/EC_codes/run_ec_test.sh', folder_name],
                            #    capture_output=True,
                            #    text=True,
                            #    check=True
                            #)
                            
                            # 执行成功，将retry文件改为ok文件
                            #if not os.path.exists(ok_filen) and os.path.exists(retry_filen):
                            #    os.rename(retry_filen, ok_filen)
                            #print(f"{method} 方法处理 {txt_file} 成功")
                            has_successful = True
                            
                        #except subprocess.CalledProcessError as e:
                        #    print(f"{method} 方法处理 {txt_file} 失败: {e.stderr}")
                            # 出错时跳过当前方法，继续执行下一个
                        #    continue
                    elif os.path.exists(ok_filen):
                        # 已成功执行过的方法
                        has_successful = True
                    else:
                        # 既没有retry也没有ok文件，视为未处理
                        all_processed = False
                
                # 更新信息文件记录
                if all_processed:
                    # 所有方法都已处理（无论成功失败），追加+++
                    new_line = f"{parts[0]}, {parts[1]}, {parts[2]}, +++, fff"
                    outfile.write(new_line + '\n')
                    print(f"所有方法已处理 {txt_file} (部分可能失败)")
                else:
                    # 未完成所有方法处理，保持原记录
                    outfile.write(line + '\n')
        
        # 用临时文件替换原文件（原子操作）
        os.replace(temp_file, info_file)
        print("台风定位处理完成")
        
    #except Exception as e:
    #    print(f"处理过程中发生错误: {str(e)}")
    #    # 清理临时文件
    #    if os.path.exists(temp_file):
    #        os.remove(temp_file)

if __name__ == "__main__":
    # 配置目录
    config_dir = "/vol8/home/kongjun/VERIFY/OBS/tfb_mess/"
    typhoon_mess_path = "/vol8/home/kongjun/VERIFY/OBS/typhoon_mess/"
    process_typhoon_location(config_dir,typhoon_mess_path)
    
