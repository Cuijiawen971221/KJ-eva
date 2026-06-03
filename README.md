北京kj检验评估项目 代码备份
代码说明：
1、函数/配置项文件

文件	用途
config.py 	从 pathconfig.yaml 读路径（各模式 fcst/output/tools）、pparms 配置类
grib_dict.py	GRIB2 变量名字典
grid_proc.py	核心：格点插值、区域/机场/站点处理、GRIB 读写、多进程池、入库逻辑（
yunyao_met.py	核心统计：高空/地面要素 TS、Bias、相关系数等检验算法
mode_function.py	MODE 降水空间检验算法
utils.py	检验指标辅助（准确率阈值等）
met_clickhouse_util.py	实况/站点/区域保存、批量写入 CK
clickhouse_util.py	ClickHouse 客户端封装（含 HPC 文件队列写入）
clickhouse_util_cjw.py / clickhouse_util_host.py	变体/主机版 CK 连接
met_weather.py	气象数据处理大模块（可被 main 引用）
py2java.py	Python 与 Java 侧数据结构/调用桥接
interp_point2grid.py	站点到格点插值（xesmf）
humidity_calc.py	湿度计算（Vaisala 公式）
hash.py	哈希值生成工具
read_fss.py	读取 FSS 结果
read_station_from_db.py	从库读站点
getStationID.py	站点 ID 查询
merge_KJRHC.py	KJ区域高分辨率模式，站点后订正结果合并（多要素）
split.py / pynio_split.py	GRIB/数据集切分
wind_grib.py	风场 GRIB 读取
rain_fss_ts_function.py	降水 TS/FSS 相关函数库
rain24_grid.py	24h 降水格点处理逻辑
emend.py	变量名修正（PRC、T2C 等）


2、并行处理程序（提交计算节点）

文件	用途	命令行参数
mpi_area_ground_met.py	地面区域检验（多要素）	fcst, timedelta, ref, leng
mpi_area_ground_met_test.py	同上（测试/并行子进程版）	同上
mpi_area_ground_loop_fcst.py	并行拉起多模式 mpi_area_ground_met_test	ref, dt(timedelta), length
mpi_area_plev_met.py	高空气压层检验	fcst, timedelta, ref
mpi_point_interpAmet.py	站点插值检验	fcst, timedelta
mpi_convert_rain.py	降水转换/检验流水线	fcst, timedelta, ref
mpi_conver_rain.py	降水转换（拼写变体）	fcst（2、3 参数注释掉）
mpi_grid_proc.py	格点处理任务调度	fcst
mpi_grid_proc_his.py 	历史格点检验处理	fcst
mpi_grid.py	检查各模式 job 消息并触发格点任务	无 argv（读配置+当前时次）
mpi_airport_interp.py	机场插值批处理	fcst
mpi_airport_interp_his.py	历史机场插值（缺失回补）	fcst
mpi_weather_dig.py	气象数据挖掘/处理	fcst
utils_read_pkltodb.py	将 airport 插值 pickle 写入 数据库	fcst
mpi_process_ecmwf_rain.py	ECMWF 累计降水处理	无 argv（内部算当前 UTC 起报）
mpi_process_ecmwf_rain_his.py	ECMWF 降水历史	无 argv / 硬编码
mpi_process_ncep_rain.py	NCEP 降水	无 argv
mpi_process_ncep_rain_his.py	NCEP 降水历史回补	/
mpi_process_kt1279_rain.py	KT1279 降水	无 argv
mpi_process_cldas_rain.py	CLDAS 参考降水	无 argv
mpi_process_cmagfs_rain.py	CMA-GFS 降水	无 argv
mpi_process_auto_rain.py	AUTO 模式降水	无 argv

 
3、降水检验（FSS / TS / 24h）
文件	用途	参数
fss24_point.py	24h 降水 FSS（格点+邻域）	16 个 sys.argv：①起报小时(0/12) ②fcstroot ③obsroot ④maskroot ⑤⑥起止日期(YYYYMMDD) ⑦-⑩经纬范围 ⑪half_size逗号串 ⑫FCST_path ⑬grid_file ⑭cdo_path ⑮region_id ⑯输出名
rain_point24.py	24h 降水点检验	①time ②fcstroot ③outputroot ④⑤起止日期
rain_ts_point.py	站点降水 TS（按日循环）	da_01, da_02（日号区间，如 1–31）
rain_ts_aws.py	AWS 站点 TS	da_01, da_02
rain_fss_ts_ds.py	多模式 FSS+TS 数据集	argv 注释，硬编码模式列表
getRain24Sum.py	从库算 24h 累计降水	/

4、报文 / 文件解码器
文件	用途	参数
uniform_decoder.py	GTS 统一解码 → CK	库函数 decoder_main(stime)；main 可本地测
mh_decoder.py	民航 MH 报文 → CK	decoder_main(date_num)；main 循环日期
jd_decoder.py	军队 JD 报文	同 MH
micaps_decoder.py	MICAPS 数据解码	main 本地测试
csv_decoder.py / dat_decoder.py	CSV/DAT 解码	main 测试
word_decoder.py	Word(.docx) → CSV	main 写死 decode("demo.docx","structure")
select_param.py	从 GRIB 筛 850hPa 位势高度	infile, outfile

5、台风模块
文件	用途	参数
Typhoon_location_main.py	统一调度（状态机轮询 GVT/动态定位）	--model：ECMWF | NCEP | KT1279
decode_TFB.py	台风报文 TFB 解码	datetime_now（如 20250501）
typhoon_decode_function.py	解码公共函数	库模块

===============================================================================================================

