import argparse
import glob
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import config as cf

# 文件名示例:
# NAFP_KDSZ_KHMA_YYYYMMDDHHMMSS-UMC-{STA}-72.TXT
FILE_RE = re.compile(
    r"^NAFP_KDSZ_KHMA_(\d{14})-(UMC|VMC|T2C|PRC|CLC|VIC)-(.+?)-72\.TXT$",
    re.IGNORECASE,
)
# 要素字典
ELEMENT_NAME = {
    "T2C": "t2m",
    "UMC": "u_wind",
    "VMC": "v_wind",
    "PRC": "precip",
    "VIC": "visibility",
    "CLC": "cloud",
}
# 输出的csv表头
OUTPUT_COLUMNS = [
    "cycle",
    "station",
    "lead_idx",
    "t2m",
    "u_wind",
    "v_wind",
    "precip",
    "visibility",
    "cloud",
]
# 所有需要处理的要素
ALL_ELEMENTS = ["T2C", "UMC", "VMC", "PRC", "VIC", "CLC"]

# 设置日志
def setup_logger(log_file: str, verbose: bool = True) -> logging.Logger:
    logger = logging.getLogger("merge_kjrhc")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger

# 标记路径
def marker_paths(mess_root: str, cycle: str) -> Tuple[str, str]:
    day_str = cycle[:8]
    base_dir = os.path.join(mess_root, "KJRHC", day_str)
    retry_path = os.path.join(base_dir, f"KJRHC-{cycle}.retry")
    ok_path = os.path.join(base_dir, f"KJRHC-{cycle}.ok")
    return retry_path, ok_path

# 写入retry标记
def write_retry_marker(mess_root: str, cycle: str, message: str = "") -> str:
    retry_path, ok_path = marker_paths(mess_root, cycle)
    os.makedirs(os.path.dirname(retry_path), exist_ok=True)
    if not os.path.exists(retry_path):
        with open(retry_path, "w", encoding="utf-8") as f:
            f.write(message or f"retry {cycle}\n")
    return retry_path

# 将retry标记改为ok标记
def switch_retry_to_ok(mess_root: str, cycle: str, message: str = "") -> str:
    retry_path, ok_path = marker_paths(mess_root, cycle)
    os.makedirs(os.path.dirname(ok_path), exist_ok=True)
    if os.path.exists(retry_path):
        os.replace(retry_path, ok_path)
    else:
        with open(ok_path, "w", encoding="utf-8") as f:
            f.write("")
    if message:
        with open(ok_path, "w", encoding="utf-8") as f:
            f.write(message + "\n")
    return ok_path

# 统计NC文件数量
def count_nc_files(nc_root: str, cycle: str) -> int:
    # 需求: 检查 /process_time/ 路径下 *AVO-EAI-*.NC 数量
    nc_dir = os.path.join(nc_root, cycle)
    pattern = os.path.join(nc_dir, "*AVO-EAI-*.NC")
    return len(glob.glob(pattern))

def ns_get_first(ns, keys: List[str], default=None):
    for key in keys:
        if hasattr(ns, key):
            value = getattr(ns, key)
            if value not in (None, ""):
                return value
    return default


def discover_files(input_root: str) -> Dict[Tuple[str, str], Dict[str, str]]:
    """
    扫描目录，按 (cycle, station) 聚合各要素文件.
    返回:
      {
        (cycle, station): {"T2C": path, "UMC": path, ...}
      }
    """
    grouped: Dict[Tuple[str, str], Dict[str, str]] = defaultdict(dict)

    for root, _, files in os.walk(input_root):
        for file_name in files:
            match = FILE_RE.match(file_name)
            if not match:
                continue

            ts14, element, station = match.groups()
            station = station.strip()
            element = element.upper()

            # 优先使用父目录中的 YYYYMMDDHH
            parent_dir = os.path.basename(root)
            if re.fullmatch(r"\d{10}", parent_dir):
                cycle = parent_dir
            else:
                cycle = ts14[:10]

            grouped[(cycle, station)][element] = os.path.join(root, file_name)

    return grouped


def _read_text_table(path: str) -> pd.DataFrame:
    # 同时兼容制表符、空格和逗号分隔
    df = pd.read_csv(
        path,
        sep=r"\s+|,",
        engine="python",
        header=None,
        comment="#",
        skip_blank_lines=True,
    )
    # 删除全空列
    df = df.dropna(axis=1, how="all")
    return df


def read_element_series(path: str, element: str) -> pd.DataFrame:
    """
    将单要素 TXT 标准化为两列:
      lead_idx(1..N), <element_value>
    """
    df = _read_text_table(path)
    if df.empty:
        return pd.DataFrame(columns=["lead_idx", ELEMENT_NAME[element]])

    # 常见情况:
    # 1) 2列以上: 第1列是时效/索引，最后1列是值
    # 2) 1列: 仅值，使用行号作为 lead_idx
    if df.shape[1] >= 2:
        lead = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        value = pd.to_numeric(df.iloc[:, -1], errors="coerce")
        out = pd.DataFrame({"lead_idx": lead, ELEMENT_NAME[element]: value})

        # 若第一列无法解析为数字，退化为按行索引拼接
        if out["lead_idx"].isna().all():
            out["lead_idx"] = range(1, len(out) + 1)
    else:
        value = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        out = pd.DataFrame(
            {
                "lead_idx": range(1, len(value) + 1),
                ELEMENT_NAME[element]: value,
            }
        )

    # 去掉值为空的行
    out = out.dropna(subset=[ELEMENT_NAME[element]], how="all")
    return out


def merge_station_elements(cycle: str, station: str, element_files: Dict[str, str]) -> pd.DataFrame:
    merged = None
    for element in ALL_ELEMENTS:
        path = element_files.get(element)
        if not path:
            continue
        part = read_element_series(path, element)
        merged = part if merged is None else pd.merge(merged, part, on="lead_idx", how="outer")

    if merged is None or merged.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    merged.insert(0, "station", station)
    merged.insert(0, "cycle", cycle)
    merged = merged.sort_values("lead_idx").reset_index(drop=True)

    for col in ["t2m", "u_wind", "v_wind", "precip", "visibility", "cloud"]:
        if col not in merged.columns:
            merged[col] = pd.NA

    return merged[OUTPUT_COLUMNS]


def write_station_csv(df: pd.DataFrame, station: str, output_root: str, cycle: str, split_by_cycle: bool) -> str:
    file_name = f"KJRHC-METE-{station}-72.csv"
    out_dir = os.path.join(output_root, cycle) if split_by_cycle else output_root
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, file_name)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def process_one_cycle(
    cycle: str,
    txt_root: str,
    output_root: str,
    mess_root: str,
    logger: logging.Logger,
    split_by_cycle: bool = True,
) -> bool:
    _, ok_path = marker_paths(mess_root, cycle)
    if os.path.exists(ok_path):
        logger.info("cycle=%s 已有ok标记, 跳过处理: %s", cycle, ok_path)
        return True

    txt_cycle_dir = os.path.join(txt_root, cycle)
    if not os.path.isdir(txt_cycle_dir):
        write_retry_marker(mess_root, cycle, f"txt dir not found: {txt_cycle_dir}")
        logger.warning("cycle=%s TXT目录不存在: %s", cycle, txt_cycle_dir)
        return False

    grouped = discover_files(txt_cycle_dir)
    if not grouped:
        write_retry_marker(mess_root, cycle, f"no txt files under {txt_cycle_dir}")
        logger.warning("cycle=%s 未发现可处理TXT文件: %s", cycle, txt_cycle_dir)
        return False

    # 只处理当前 cycle 的站点
    station_groups = {
        station: files for (group_cycle, station), files in grouped.items() if group_cycle == cycle
    }
    if not station_groups:
        write_retry_marker(mess_root, cycle, f"no station groups in {txt_cycle_dir}")
        logger.warning("cycle=%s 未发现站点分组", cycle)
        return False

    total_csv = 0
    incomplete_stations = 0
    failed_write = 0

    for station, element_files in sorted(station_groups.items()):
        missing = sorted(set(ALL_ELEMENTS) - set(element_files.keys()))
        if missing:
            incomplete_stations += 1
            logger.warning(
                "cycle=%s station=%s 要素不齐全, 缺少: %s; 继续输出CSV, 缺失列留空",
                cycle,
                station,
                ",".join(missing),
            )

        station_df = merge_station_elements(cycle, station, element_files)
        if station_df.empty:
            logger.warning("cycle=%s station=%s 合并结果为空", cycle, station)
            failed_write += 1
            continue

        out_path = write_station_csv(station_df, station, output_root, cycle, split_by_cycle)
        if os.path.exists(out_path):
            total_csv += 1
            logger.info("cycle=%s station=%s CSV写入成功: %s", cycle, station, out_path)
        else:
            failed_write += 1
            logger.error("cycle=%s station=%s CSV写入后不存在: %s", cycle, station, out_path)

    if total_csv > 0 and failed_write == 0:
        ok_path = switch_retry_to_ok(
            mess_root,
            cycle,
            f"ok cycle={cycle} csv={total_csv} incomplete={incomplete_stations}",
        )
        logger.info("cycle=%s 处理完成, 状态改为ok: %s", cycle, ok_path)
        return True

    retry_path = write_retry_marker(
        mess_root,
        cycle,
        f"retry cycle={cycle} csv={total_csv} failed={failed_write} incomplete={incomplete_stations}",
    )
    logger.warning("cycle=%s 处理未完成, 状态保持retry: %s", cycle, retry_path)
    return False


def parse_cycle(cycle: str) -> datetime:
    return datetime.strptime(cycle, "%Y%m%d%H")


def validate_cycle_hour(cycle_dt: datetime, cycle_text: str) -> None:
    if cycle_dt.hour not in (0, 12):
        raise ValueError(f"时次必须为00或12: {cycle_text}")


def calc_cycle_range(now: Optional[datetime] = None) -> Tuple[str, str]:
    """实时任务: 结束为当前时次(00/12), 开始为结束时间往前推一天."""
    if now is None:
        now = datetime.now()
    hour_suffix = "12" if now.hour >= 12 else "00"
    end_dt = datetime.strptime(now.strftime("%Y%m%d") + hour_suffix, "%Y%m%d%H")
    start_dt = end_dt - timedelta(days=1)
    return start_dt.strftime("%Y%m%d%H"), end_dt.strftime("%Y%m%d%H")


def iter_cycle_range(start_cycle: str, end_cycle: str) -> List[str]:
    start_dt = parse_cycle(start_cycle)
    end_dt = parse_cycle(end_cycle)
    validate_cycle_hour(start_dt, start_cycle)
    validate_cycle_hour(end_dt, end_cycle)
    if start_dt > end_dt:
        raise ValueError(f"开始时间晚于截止时间: {start_cycle} > {end_cycle}")

    cycles: List[str] = []
    current = start_dt
    while current <= end_dt:
        cycles.append(current.strftime("%Y%m%d%H"))
        current += timedelta(hours=12)
    return cycles


def run(
    txt_root: str,
    nc_root: Optional[str],
    output_root: str,
    mess_root: str,
    split_by_cycle: bool = True,
    require_nc_count: int = 72,
) -> int:
    if not nc_root:
        nc_root = txt_root

    start_cycle, end_cycle = calc_cycle_range()
    cycles = iter_cycle_range(start_cycle, end_cycle)
    log_file = os.path.join(
        mess_root,
        "KJRHC",
        "logs",
        f"merge_KJRHC_{start_cycle}_{end_cycle}.log",
    )
    logger = setup_logger(log_file=log_file, verbose=True)
    logger.info("实时任务启动 start=%s end=%s cycle_count=%d", start_cycle, end_cycle, len(cycles))
    logger.info("参数 txt_root=%s nc_root=%s output_root=%s mess_root=%s", txt_root, nc_root, output_root, mess_root)

    success_count = 0
    fail_count = 0
    for cycle in cycles:
        nc_count = count_nc_files(nc_root, cycle)
        logger.info("cycle=%s NC文件数量=%d (要求=%d)", cycle, nc_count, require_nc_count)
        if nc_count < require_nc_count:
            fail_count += 1
            retry_path = write_retry_marker(
                mess_root,
                cycle,
                f"retry cycle={cycle} nc_count={nc_count} required={require_nc_count}",
            )
            logger.warning("cycle=%s NC不足, 保持retry: %s", cycle, retry_path)
            continue

        done = process_one_cycle(
            cycle=cycle,
            txt_root=txt_root,
            output_root=output_root,
            mess_root=mess_root,
            logger=logger,
            split_by_cycle=split_by_cycle,
        )
        if done:
            success_count += 1
        else:
            fail_count += 1

    logger.info("实时任务结束 success=%d fail=%d total=%d", success_count, fail_count, len(cycles))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合并 KJRHC 站点多要素 TXT 为单站 CSV")
    parser.add_argument(
        "-c",
        "--config",
        default=os.path.join(os.path.dirname(__file__), "pathconfig.yaml"),
        help="配置文件路径(默认: 脚本同目录 pathconfig.yaml)",
    )
    parser.add_argument(
        "-i",
        "--txt-root",
        required=False,
        default=None,
        help="TXT输入根目录(可选, 优先级高于配置文件)",
    )
    parser.add_argument(
        "-n",
        "--nc-root",
        required=False,
        default=None,
        help="NC输入根目录(可选; 不填则默认等于txt_root)",
    )
    parser.add_argument(
        "-o",
        "--output-root",
        required=False,
        default=None,
        help="输出根目录(可选, 优先级高于配置文件)",
    )
    parser.add_argument(
        "-m",
        "--mess-root",
        required=False,
        default=None,
        help="mess 根目录(可选, 优先级高于配置文件)",
    )
    parser.add_argument(
        "--no-split-by-cycle",
        action="store_true",
        help="不按 cycle 分子目录输出，直接写到输出根目录",
    )
    parser.add_argument(
        "--require-nc-count",
        type=int,
        default=None,
        help="触发TXT拼接所需的最小NC文件数量(可选, 默认72)",
    )
    args = parser.parse_args()

    conf = cf.pparms(args.config).param
    txt_root = args.txt_root or ns_get_first(
        conf,
        [
            "kjrhc_txt_root",
            "kjrhc_data_root",
            "kjrhc_root",
            "kjrhcfcstpath",
            "kjrhfcstpath",
        ],
    )
    output_root = args.output_root or ns_get_first(
        conf,
        [
            "kjrhc_output_root",
            "kjrhc_csv_output_root",
            "kjrhcoutputpath",
            "kjrhoutputpath",
        ],
    )
    mess_root = args.mess_root or ns_get_first(
        conf,
        ["kjrhc_mess_root", "kjrhcmesspath", "message"],
    )
    nc_root = args.nc_root or ns_get_first(
        conf,
        ["kjrhc_nc_root", "kjrhcncpath", "kjrhc_data_root", "kjrhc_root", "kjrhcfcstpath", "kjrhfcstpath"],
    )
    require_nc_count = args.require_nc_count
    if require_nc_count is None:
        require_nc_count = int(ns_get_first(conf, ["kjrhc_require_nc_count"], 72))

    start_cycle, end_cycle = calc_cycle_range()
    print({
        "txt_root": txt_root,
        "nc_root": nc_root,
        "output_root": output_root,
        "mess_root": mess_root,
    })
    print({
        "start_cycle": start_cycle,
        "end_cycle": end_cycle,
        "split_by_cycle": not args.no_split_by_cycle,
        "require_nc_count": require_nc_count,
    })

    exit_code = run(
        txt_root=txt_root,
        nc_root=nc_root,
        output_root=output_root,
        mess_root=mess_root,
        split_by_cycle=not args.no_split_by_cycle,
        require_nc_count=require_nc_count,
    )
    sys.exit(exit_code)
