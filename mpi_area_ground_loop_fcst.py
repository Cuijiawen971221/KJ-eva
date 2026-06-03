import subprocess
import multiprocessing
from multiprocessing import Pool
import time
from typing import List, Callable, Union, Tuple, Dict
import logging
import glob
import datetime
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParallelFramework:
    """
    并行处理框架，支持通过multiprocessing并行执行Python函数，
    以及通过subprocess并行执行外部命令
    """
    
    def __init__(self, max_workers: int = None):
        """
        初始化并行框架
        
        参数:
            max_workers: 最大工作进程数，默认使用CPU核心数
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        logger.info(f"初始化并行框架，最大工作进程数: {self.max_workers}")
    
    def run_python_functions_parallel(self, 
                                     functions: List[Callable], 
                                     args_list: List[Tuple] = None) -> List[Union[object, Exception]]:
        """
        使用multiprocessing并行执行Python函数
        
        参数:
            functions: 要执行的函数列表
            args_list: 每个函数对应的参数列表， None表示无参数
            
        返回:
            函数执行结果列表，如果执行出错则返回异常对象
        """
        if args_list is None:
            args_list = [() for _ in range(len(functions))]
            
        if len(functions) != len(args_list):
            raise ValueError("函数列表和参数列表长度必须一致")
            
        logger.info(f"开始并行执行 {len(functions)} 个Python函数")
        
        results = []
        with Pool(processes=self.max_workers) as pool:
            # 创建任务列表
            tasks = []
            for func, args in zip(functions, args_list):
                tasks.append(pool.apply_async(self._wrap_function, (func, args)))
            
            # 获取结果
            for i, task in enumerate(tasks):
                try:
                    result = task.get()  # 等待任务完成
                    results.append(result)
                    logger.debug(f"函数 {i+1}/{len(tasks)} 执行完成")
                except Exception as e:
                    logger.error(f"函数 {i+1}/{len(tasks)} 执行出错: {str(e)}")
                    results.append(e)
        
        logger.info(f"所有Python函数执行完毕")
        return results
    
    def _wrap_function(self, func: Callable, args: Tuple) -> object:
        """包装函数用于错误捕获"""
        try:
            return func(*args)
        except Exception as e:
            logger.error(f"函数执行出错: {str(e)}")
            raise
    
    def run_commands_parallel(self, 
                             commands: List[str],
                             shell: bool = True,
                             capture_output: bool = True,
                             text: bool = True) -> List[Dict[str, Union[int, str, Exception]]]:
        """
        使用subprocess和multiprocessing并行执行外部命令
        
        参数:
            commands: 要执行的命令列表
            shell: 是否使用shell执行命令
            capture_output: 是否捕获 stdout 和 stderr
            text: 是否以文本模式返回输出
            
        返回:
            命令执行结果列表，每个结果包含returncode, stdout, stderr或error
        """
        logger.info(f"开始并行执行 {len(commands)} 个外部命令")
        
        results = []
        with Pool(processes=self.max_workers) as pool:
            # 创建任务列表
            tasks = []
            for cmd in commands:
                tasks.append(pool.apply_async(
                    self._run_single_command, 
                    (cmd, shell, capture_output, text)
                ))
            
            # 获取结果
            for i, task in enumerate(tasks):
                try:
                    result = task.get()  # 等待任务完成
                    results.append(result)
                    if result['returncode'] == 0:
                        logger.debug(f"命令 {i+1}/{len(tasks)} 执行成功")
                    else:
                        logger.warning(f"命令 {i+1}/{len(tasks)} 执行失败，返回码: {result['returncode']}")
                except Exception as e:
                    logger.error(f"命令 {i+1}/{len(tasks)} 执行出错: {str(e)}")
                    results.append({'error': str(e)})
        
        logger.info(f"所有外部命令执行完毕")
        return results
    
    def _run_single_command(self, 
                           cmd: str, 
                           shell: bool, 
                           capture_output: bool, 
                           text: bool) -> Dict[str, Union[int, str]]:
        """执行单个外部命令"""
        try:
            kwargs = {
                'shell': shell,
                'text': text
            }
            
            if capture_output:
                kwargs['stdout'] = subprocess.PIPE
                kwargs['stderr'] = subprocess.PIPE
            
            result = subprocess.run(cmd, **kwargs)
            
            output = {
                'command': cmd,
                'returncode': result.returncode
            }
            
            if capture_output:
                output['stdout'] = result.stdout
                output['stderr'] = result.stderr
                
            return output
        except Exception as e:
            logger.error(f"命令执行出错: {str(e)}")
            raise


# 示例用法
if __name__ == "__main__":
    # 初始化并行框架
    parallel_framework = ParallelFramework(max_workers=16)
    
    ref = sys.argv[1]
    dt = sys.argv[2]
    length = sys.argv[3]
        
    # 2. 示例：并行执行外部命令
    commands = []
    programPath = "/vol8/home/kongjun/VERIFY/met/met_backend/"
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py KT1279 {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/KT1279_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py CMA_GFS {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/CMA_GFS_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py AUTO {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/AUTO_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py NCEP {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/NCEP_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py ECMWF {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/ECMWF_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py VISFCST {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/VISFCST_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py KT1279_CLOUD {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/KT1279_CLOUD_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py REGION {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/REGION_{ref}_ground.log")
    commands.append(f"/vol7/home/kongjun/SOFTWARES/anaconda3/envs/met_interp_panoply/bin/python {programPath}/mpi_area_ground_met_test.py KJRH {dt} {ref} {length} >/vol8/home/kongjun/VERIFY/met/met_backend/log/KJRH_{ref}_ground.log")
    for cmd in commands:
        print(cmd)
    start_time = time.time()
    command_results = parallel_framework.run_commands_parallel(commands)
    
    print("\n外部命令执行结果:")
    for i, result in enumerate(command_results):
        if 'error' in result:
            print(f"命令 {i+1} 出错: {result['error']}")
        else:
            print(f"命令 {i+1} 返回码: {result['returncode']}")
            print(f"命令 {i+1} 输出: {result['stdout'].strip()}")
    
    print(f"外部命令并行执行总时间: {time.time() - start_time:.2f}秒")

