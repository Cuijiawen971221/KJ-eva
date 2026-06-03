import meteva.base as meb
import numpy as np
import datetime
import pandas as pd

def decoder_main(filename):
    sta = meb.read_stadata_from_micaps3(filename)  #在其他参数缺省的情况下，站点列表、时间和层次信息均根据文件内容设置,时效设置为0

    sta.to_csv(f"./obs/mi/m3.csv")
    sta.to_csv(f"./obs/mi/m3.dat", sep=' ', index=False)


if __name__ == "__main__":
    decoder_main(f"./obs/mi/m3.txt")
