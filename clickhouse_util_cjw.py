import clickhouse_connect
import config_cjw as cf
import hashlib
import os
import pickle
import numpy as np

globalConf = cf.pparms("/vol8/home/kongjun/VERIFY/met/met_backend/pathconfig.yaml").param

class clickFilesystem_HPC():
    def __init__(self):
        pass
    def insert_df(self,part,data):
        
        hashstr = hashlib.sha256(data.to_json().encode("utf-8")).hexdigest() 
        print(hashstr)
        with open(globalConf.clickTofile+f"/HPC_insert_df_{hashstr}","wb") as f:
            pickle.dump((part,data),f)
        if globalConf.debug_txt:
            mode_type = np.unique(data["mode_type"])[0]
            try:
                ref = np.unique(data["reference_data_type"])[0]
            except:
                ref = "airport"
            formatted_txt = data.to_string(col_space=[10] * len(data.columns))
            with open(globalConf.clickTofile+f"/{part}_{mode_type}_{ref}_HPC_insert_df_{hashstr}.csv","w") as f:
                f.write(formatted_txt)
        with open(globalConf.clickTofile+f"/HPC_insert_df_{hashstr}.OK","w") as f:
            pass
        
    def query_df(self,sql):
        
        hashstr = hashlib.sha256(sql.replace(" ","").encode("utf-8")).hexdigest()
        print(sql)
        print(hashstr)
        if os.path.exists(globalConf.clickTofile+f"/MET_insert_df_{hashstr}") and \
           os.path.exists(globalConf.clickTofile+f"/MET_insert_df_{hashstr}.OK"):
            with open(globalConf.clickTofile+f"/MET_insert_df_{hashstr}","rb") as f:
               data = pickle.load(f)
            #os.remove(globalConf.clickTofile+f"/MET_insert_df_{hashstr}")
            #os.remove(globalConf.clickTofile+f"/MET_insert_df_{hashstr}.OK")
        else:
            data = [] 
        return data    

# 检验端的clickhouse 文件系统服务。

class clickFilesystem_MET():
    def __init__(self):
        pass
    def insert_df(self,sql,data):
        hashstr = hashlib.sha256(sql.replace(" ","").encode("utf-8")).hexdigest()
        with open(globalConf.clickTofile+f"/MET_insert_df_{hashstr}","wb") as f:
            data = pickle.dump(data,f)
        with open(globalConf.clickTofile+f"/MET_insert_df_{hashstr}.OK","w") as f:
            pass
# 从文件夹中提取文件并写入数据库，
# 从HPC到检验服务器
# 记得删除.OK文件
    def insert_df_from_HPC_MET(self,filename,client):
        with open(filename,"rb") as f:
            data = pickle.load(f)
            client.insert_df(data[0],data[1])
            os.remove(filename)
            os.remove(filename+".OK")
       

if not globalConf.use_DB: 
    clickclient = clickFilesystem_HPC()
    clickclient_file = None
else:
    clickclient = clickhouse_connect.get_client(
         host=globalConf.clickhouseIP,
         port=globalConf.clickhousePort,
         username=globalConf.clickhouseUsername,
         password=globalConf.clickhousePassword,
         database=globalConf.clickhouseDatabase,
         settings={'use_client_time_zone': 0}  # 关键设置
    )
    clickclient_file = clickFilesystem_MET()
#clickclient.command("SET timezone = 'Asia/Shanghai'")
