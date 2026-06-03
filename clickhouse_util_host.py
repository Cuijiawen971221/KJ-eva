import clickhouse_connect
import config as cf

globalConf = cf.pparms("./pathconfig.yaml").param

#clickclient = None
clickclient_db = clickhouse_connect.get_client(
     host=globalConf.clickhouseIP,
     port=globalConf.clickhousePort,
     username=globalConf.clickhouseUsername,
     password=globalConf.clickhousePassword,
     database=globalConf.clickhouseDatabase,
     settings={'use_client_time_zone': 0}  # 关键设置
 )
#clickclient.command("SET timezone = 'Asia/Shanghai'")
