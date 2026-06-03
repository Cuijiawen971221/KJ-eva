import pygrib
import datetime as dt 

fout_dict = {}

grbs = pygrib.open("dc3b1cde69d71d6363f021d95eabd56c.grib")
for grb in grbs:
    timestr = "{:d}{:0>4d}".format(grb["date"],grb["time"])
    print(timestr)
    print(grb["time"]==100)
    if grb["time"] in [600,900,1200,1500,1800,2100,300,0]:
        if timestr not in fout_dict.keys():
            fout_dict[timestr] =[]
        fout_dict[timestr].append(grb)
print("start split")

for k in fout_dict.keys():
    with open("ERA5{:s}000.grib".format(k),"wb") as f:
        for var in fout_dict[k]:
            f.write(var.tostring())
    


