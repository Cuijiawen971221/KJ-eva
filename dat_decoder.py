import numpy as np
import datetime
import pandas as pd


def decoder_main(filename):
    df = pd.read_csv(filename, sep =r'\s+')
    print(df)


if __name__ == "__main__":
    decoder_main(f"./obs/mi/m3.dat")

