import yaml
import config as cf
import clickhouse_connect

globalConf = cf.pparms("./pathconfig.ymal").param

clickclient = clickhouse_connect.get_client(
    host=globalConf.clickhouseIP,
    port=globalConf.clickhousePort,
    username=globalConf.clickhouseUsername,
    password=globalConf.clickhousePassword,
    database=globalConf.clickhouseDatabase
)

sql = f"""
                SELECT DISTINCT station_code, longitude, latitude FROM surface_observation_data 
        """
obs = clickclient.query_df(sql)
know = {}
for row in obs.itertuples():
    if row.station_code not in know.keys():
        know[row.station_code] = (row.longitude,row.latitude)
    else:
        if row.longitude != know[row.station_code][0] and row.latitude != know[row.station_code][1]:
            print(row.station_code,row.longitude,row.latitude,know[row.station_code][0],know[row.station_code][1])
#print(obs[["ID","longitude","latitude"]])

