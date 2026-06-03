from clickhouse_util import clickclient
import datetime
import numpy as np


def getRain(obstime,HH):
    
    # first get data from database 
    tgtime = obstime-datetime.timedelta(hours=HH)
    tgtimestr = tgtime.strftime("%Y-%m-%d %H:%M:%S")
    obstimestr = obstime.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"""
           SELECT station_code,longitude,latitude,observation_time,precipitation_24  FROM szybjydb.surface_observation_data where message_type='aws' AND observation_time = '{obstimestr}'
           """
    t1 =datetime.datetime.now()
    rain = clickclient.query_df(sql)
    t2 =datetime.datetime.now()
    print("数据库读取耗时：",t2-t1)
    # groupby station_code and sum precipitation 
    #rain_group = rain.groupby(["station_code","longitude","latitude"])
    #rain_group_count = rain_group.count()
    #rain_sum = rain_group["precipitation"].sum().reset_index()
    
    #rain_group = rain_group_count.iloc[np.where(rain_group_count["precipitation"].to_numpy()==HH)].reset_index() 
    #station_code = rain_group["station_code"].to_numpy()
    # filter station which loc changed 
    #station,count = np.unique(rain_sum["station_code"].to_numpy(),return_counts=True)
    # one get station with static location 
    rain_sum_select = rain #rain_sum[rain_sum["station_code"].isin(station_code)]
    
    t3 =datetime.datetime.now()
    print("CALC耗时：",t3-t2)
    rain_sum_select = rain_sum_select.rename(columns={"precipitation_24":"precipitation"})
    return rain_sum_select


if __name__=="__main__":
    now = datetime.datetime(2025,5,3,0,0,0)
    result = getRain(now,24) 
    print(result)
