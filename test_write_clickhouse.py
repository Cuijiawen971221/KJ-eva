from clickhouse_util import clickclient,clickclient_file
import numpy as np
import xarray as xr
from py2java import *
import datetime
import pickle

if __name__=="__main__":
    ppp = ",".join([pyweb2java(var) for var in ["2t","2d"]])
    obsdate = datetime.datetime.strptime("2025050100","%Y%m%d%H")
    sql = f"""
        SELECT id, region_name, region_code, left_top_lon, left_top_lat, right_bottom_lon, right_bottom_lat FROM szybjydb.sys_region_config
        """
    obs = clickclient.query_df(sql)
    print(obs)
    clickclient_file.insert_df(sql,obs)

