from clickhouse_util import clickclient

sql = """
                SELECT station_id, station_code, longitude, latitude FROM station_info where station_code='cq_gts' 
     """

obs = clickclient.query_df(sql)
print(obs)
