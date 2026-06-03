import os
import time
import argparse
import subprocess

# Config paths
TYPHOON_MESS_PATH = "/vol8/home/kongjun/VERIFY/OBS_typhoon/typhoon_mess/"
JSON_OUT_PATH = "/vol8/home/kongjun/VERIFY/OBS_typhoon/tfb_json/"

CONFIG = {
    'ECMWF': {
        'GVT_code_dir': '/vol8/home/kongjun/VERIFY/OBS_typhoon/codes/typhoon_his/GVT_orig/EC_codes/',
        'GVT_sh_script': 'run_ec_test.sh',
        'ai_tracker': {
            'model_path': './ecmwf_tracker.pth',
            'forecast_dir': '/vol7/home/kongjun/OBS/ECMF/',
            'forecast_model': 'ecmwf'
        },
        'dynamic': {
            'solve_script': 'solve.py',
            'auto_path': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/',
            'auto_outpath': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/ECMWF/',
            'gvt_res_path': '/vol8/home/kongjun/VERIFY/GVT/GFDL_main/main_codes/output/ecfc_anvo/'
        }
    },
    'NCEP': {
        'GVT_code_dir': '/vol8/home/kongjun/VERIFY/OBS_typhoon/codes/typhoon_his/GVT_orig/NCEP_codes/',
        'GVT_sh_script': 'run_ncep_test.sh',
        'ai_tracker': {
            'model_path': './tc_tracker.pth',
            'forecast_dir': '/vol7/home/kongjun/OBS/KWBC/',
            'forecast_model': 'ncep'
        },
        'dynamic': {
            'solve_script': 'solve.py',
            'auto_path': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/',
            'auto_outpath': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/NCEP/',
            'gvt_res_path': '/vol8/home/kongjun/VERIFY/GVT/GFDL_main/main_codes/output/npfc_anvo/'
        }
    },
    'KT1279': {
        'GVT_code_dir': '/vol8/home/kongjun/VERIFY/OBS_typhoon/codes/typhoon_his/GVT_orig/KT1279_codes/',
        'GVT_sh_script': 'run_kt1279_test.sh',
        'ai_tracker': {
            'model_path': './ecmwf_tracker.pth',
            'forecast_dir': '/vol7/home/kongjun/KJ4Dproduct/ToPIC/', 
            'forecast_model': 'kt1279'
        },
        'dynamic': {
            'solve_script': 'solve_kt1279.py',
            'auto_path': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/',
            'auto_outpath': '/vol8/home/kongjun/VERIFY/dynamic-tc/dynamic-tc/KT1279/',
            'gvt_res_path': '/vol8/home/kongjun/VERIFY/GVT/GFDL_main/main_codes/output/ktfc_anvo/'
        }
    }
}

# Assume execution is from beijing-meteva directory. Sibling directories for ai_tracker and dynamic
# We use the relative paths dynamically, but fall back to absolute paths if moved
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CODE_DIR = os.path.join('/vol8/home/kongjun/VERIFY/OBS_typhoon/codes/typhoon_his/', 'ai_tracker')
DYN_CODE_DIR = os.path.join('/vol8/home/kongjun/VERIFY/OBS_typhoon/codes/', 'dynamic')

def run_ai_tracker(model, folder_name, json_path):
    print(f"[{model}] Running AI tracker...")
    cfg = CONFIG[model]['ai_tracker']
    
    date_n = folder_name[:8]
    hr_n = folder_name[8:10]
    hour_in = "00" if int(hr_n) < 12 else "12"

    cmd = [
        "python", "main.py",
        "--model_path", cfg['model_path'],
        "--forecast_dir", cfg['forecast_dir'],
        "--forecast_model", cfg['forecast_model'],
        "--fcst_init_day", date_n,
        "--fcst_init_hour", hour_in,
        "--json_path", json_path
    ]
    
    # Enable the proper conda environment for AI Tracker 
    # (assuming cola env based on example shell scripts)
    conda_act = "source /vol7/home/kongjun/SOFTWARES/anaconda3/envs/cola/bin/activate && "
    full_cmd = conda_act + " ".join(cmd)
    
    res = subprocess.run(full_cmd, shell=True, cwd=AI_CODE_DIR, executable='/bin/bash')
    return res.returncode == 0

def run_gvt(model, folder_name):
    print(f"[{model}] Running GVT...")
    cfg = CONFIG[model]
    print('cd ===>>>>>>',cfg['GVT_code_dir'])
    os.chdir(cfg['GVT_code_dir'])
    ### yhrun -p test -N 1 -x cn281 
    cmd_info = f"sh {cfg['GVT_sh_script']} {folder_name}"
    print('执行:',cmd_info)
    res = subprocess.run(cmd_info, shell=True, cwd=cfg['GVT_code_dir'], executable='/bin/bash')
    return res.returncode == 0

def run_dynamic(model, folder_name):
    print(f"[{model}] Running Dynamic Constraint...")
    cfg = CONFIG[model]['dynamic']
    
    date_n = folder_name[:8]
    hr_n = folder_name[8:10]
    
    # Calculate GVT output datetime mapping logic based on run_*_test.sh behavior
    # Often it falls back to 00/12 bounds based on the hour_n
    intime = f"{date_n}00" if int(hr_n) < 12 else f"{date_n}12" 
        
    res_path = os.path.join(cfg['gvt_res_path'], intime)
    if not os.path.exists(res_path):
        print(f"[{model}] Dynamic skipped: GVT result path not found {res_path}")
        return False
        
    success = True
    txt_files = [f for f in os.listdir(res_path) if f.endswith('.txt')]
    if len(txt_files) == 0:
         print(f"[{model}] Dynamic skipped: no .txt files in GVT result path.")
         return False
         
    for file in txt_files:
        gvt_result = os.path.join(res_path, file)
        cmd = [
            "python", cfg['solve_script'],
            "-f", gvt_result,
            "-d", intime,
            "-o", cfg['auto_outpath']
        ]
        
        # Enable the pyngl_env environment for dynamic algorithms as seen in bash scripts
        conda_act = "source /vol7/home/kongjun/SOFTWARES/anaconda3/envs/pyngl_env/bin/activate && "
        full_cmd = conda_act + " ".join(cmd)
        
        res = subprocess.run(full_cmd, shell=True, cwd=DYN_CODE_DIR, executable='/bin/bash')
        if res.returncode != 0:
            success = False
            
    return success

def process_typhoon_location(model):
    print(f"Starting Unified Orchestrator for {model}...")
    if not os.path.exists(TYPHOON_MESS_PATH):
        print(f"Missing message path: {TYPHOON_MESS_PATH}")
        return
        
    for folder_name in os.listdir(TYPHOON_MESS_PATH):
        mess_dir = os.path.join(TYPHOON_MESS_PATH, folder_name)
        if not os.path.isdir(mess_dir): continue
        
        ok_path = os.path.join(mess_dir, 'decoded.ok')
        if not os.path.exists(ok_path):
            continue # Message folder is not fully decoded yet
            
        json_path = os.path.join(JSON_OUT_PATH, f"{folder_name}.json")
        
        # Check and run algorithms sequentially. Dependency: dynamic requires GVT output.
#        tasks = [
#            ('ai_tracker', run_ai_tracker, [model, folder_name, json_path]),
#            ('GVT', run_gvt, [model, folder_name]),
#            ('dynamic', run_dynamic, [model, folder_name])
#        ]
        tasks = [
                ('GVT', run_gvt, [model, folder_name]),
                ]
        print(tasks)
        for method_name, func, args in tasks:
            method_ok = os.path.join(mess_dir, f"{model}_{method_name}.ok")
            if not os.path.exists(method_ok):
                successFalse = False
                try:
                    success = func(*args)
                except Exception as e:
                    print(f"[{model}] {method_name} raised exception: {str(e)}")
                    success = False
                    
                if success:
                    with open(method_ok, 'w') as f:
                        pass
                    
                    err_file = os.path.join(mess_dir, f"{model}_{method_name}.err")
                    if os.path.exists(err_file):
                        try:
                            os.remove(err_file)
                        except:
                            pass
                            
                    print(f"[{model}] {method_name} successfully finished for {folder_name}")
                else:
                    # GVT/dynamic 失败时，生成对应的日志文件 (.err)
                    err_file = os.path.join(mess_dir, f"{model}_{method_name}.err")
                    with open(err_file, 'a') as f:
                        f.write(f"Task failed or skipped at {time.ctime()}\\n")
                    print(f"[{model}] {method_name} failed for {folder_name}. Wrote .err file. Will retry next poll.")
                    # Stop further execution for this message time if dependency step fails
                    # 容错机制：GVT失败，直接 break，后续的 dynamic 当然也就不会去执行了！
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Typhoon Orchestrator (State-Machine Based)")
    parser.add_argument('--model', type=str, required=True, choices=['ECMWF', 'NCEP', 'KT1279'], help="Numerical Model Name")
    args = parser.parse_args()
    process_typhoon_location(args.model)
