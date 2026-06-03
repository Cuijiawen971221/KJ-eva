import pygrib
import sys 
infile = sys.argv[1]
outfile = sys.argv[2]

print(infile,outfile)

grbs = pygrib.open(infile)

params = ["Geopotential Height"]

for grb in grbs:
    grb.select(name="Geopotential Height",level=85000)
    print(grb)

