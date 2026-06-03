import os
import pandas as pd
import re

pattern1 = r'.*T2C.*\.TXT$'
pattern2 = r'.*UMC.*\.TXT$'
pattern3 = r'.*VMC.*\.TXT$'
pattern4 = r'.*PRC.*\.TXT$'
pattern5 = r'.*VIC.*\.TXT$'
pattern6 = r'.*CLC.*\.TXT$'


patterns = [pattern1,pattern2,pattern3,pattern4,pattern5,pattern6]
file_type = 'TXT'

def find_files(patterns,inpath):
    matching_files = []
    for root,dirs,files in os.walk(inpath):
        for file in files:
            if re.match(patterns,file):
                matching_files.append(os.path.join(root,file))
    return matching_files
    
inpath = '/vol8/home/kongjun/VERIFY/met/met_backend/orig/KJRH/2026051100/'

matching_files = []
for pattern in patterns:
    files = find_files(pattern,inpath)
    
    
print(files)

#if len(matching_files)!=6:
#    print('not enough!!!')
#else:
#    data_frames=[]
#    for file_path in matching_files:
#        df = pd.read_csv(file_path,sep='\t',header=None)
        
