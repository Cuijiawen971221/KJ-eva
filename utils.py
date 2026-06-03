import numpy as np
from typeguard import typechecked
import xarray as xr
#准确率阈值
valuepcth = {
    "2t":2, # 2度
    "2r":5, # 5%
    "2d":2,
    "mslp":10, #hPa
    "sp":10, #hPa
    "rad":10 ,#W/m2
}

degreepcth={
    "wind":[0,0.2,1.5,3.3,5.4,7.9,10.7,13.8,17.1,20.7,24.4,28.4,32.6,36.9,41.4,46.1,50.9,56,61.2],
    "wdir":[0,45,90,135,180,225,270,315,360],
}

multitspcth={
    "tcc":[[[0,5],[5,7],[7,10]],\
           [[1,0],[1,0],[1,1]]],
    "lcc":[[[0,5],[5,7],[7,10]],
           [[1,0],[1,0],[1,1]]],
    "vis": [[[0,1000],[1000,2000],[2000,4000],[4000,6000],[6000,1e6]],
            [[1,1],[0,1],[0,1],[0,1],[0,1]]]
}

tspcth={
    "rain24":[0.1,2,5,10,20],
    "vis":[500,1000,2000,3000,5000,10000],
    "tcc":[1,2,3,4,5,6,7,8,9],
    "lcc":[1,2,3,4,5,6,7,8,9],
    "ch":[100,500,1000,1500,2000,2500,3000,4000,5000]
    #"lct":[0.5,1.0,1.5,2.0,2.5,3.0],

}


pcth = {
    "2t":valuepcth, # 2度
    "2r":valuepcth, # 5%
    "2d":valuepcth,
    "mslp":valuepcth, #hPa
    "sp":valuepcth, #hPa
    "rad":valuepcth ,#W/m2
    "wind":degreepcth,
    "wdir":degreepcth,
    "rain1":tspcth,
    "vis":multitspcth,   
    "tcc":multitspcth,
    "lcc":multitspcth,
    "ch": tspcth,
}


def getWindWdir(fuuu,fvvv):
    if abs(fuuu)==999 and abs(fvvv)==999:
        wspd = -999
        Angle = -999
        wdir = -999
    else:
        wspd = np.sqrt(fuuu**2+fvvv**2)
        Angle = np.rad2deg(np.arccos((fuuu*0+fvvv*1)/wspd))
        if fuuu<0:
            Angle = 360 - Angle
        wdir = Angle
    return wspd,wdir
def getWindWdirArray(fuuu,fvvv):
    fuuu = np.ma.array(fuuu)
    fvvv = np.ma.array(fvvv)
    fuuu = np.ma.masked_where(fuuu==-999,fuuu)
    fvvv = np.ma.masked_where(fvvv==-999,fvvv)

    wspd = np.sqrt(fuuu**2+fvvv**2)
    Angle = np.rad2deg(np.arccos((fuuu*0-fvvv*1)/wspd))
    angleFlag = np.where(fuuu<0)
    Angle[angleFlag] = 360 - Angle[angleFlag]
    wdir = Angle
    return wspd.filled(-999),wdir.filled(-999)

def cloudpc(obs,fcst):
    #obs = obs.compressed()
    #fcst = fcst.compressed()
    count = 0
    for i in range(len(obs)):
        if fcst[i]<=3 and obs[i] <=3: count +=1
        if fcst[i]>=4 and fcst[i]<=5 and obs[i]>=4 and obs[i]<=5: count +=1
        if fcst[i]>=6 and obs[i]>=6:count+=1
    return count /len(obs)*100
        
def vispc(obs,fcst):
    #obs = obs.compressed()
    #fcst = fcst.compressed()
    count = 0
    for i in range(len(obs)):
        if fcst[i]<=1000 and obs[i]<=1000: count += 1
        if fcst[i]>1000 and fcst[i]<=2000 and obs[i]>1000 and obs[i]<=3000: count+=1
        if fcst[i]>2000 and fcst[i]<=4000 and obs[i]>2000 and obs[i]<=5000: count+=1
        if fcst[i]>4000 and fcst[i]<=6000 and obs[i]>4000 and obs[i]<=7000: count+=1
        if fcst[i]>6000 and fcst[i]<10000 and obs[i]>=5000 : count +=1
        if fcst[i]>=10000 and obs[i]>=5000 : count+=1
        #print(fcst[i],obs[i],count)
    return count/len(obs)*100

def chpc(obs,fcst):
    #obs = obs.compressed()
    #fcst = fcst.compressed()
    count = 0
    for i in range(len(obs)):
        if fcst[i]<=100 and obs[i]<=200: count += 1
        if fcst[i]>100 and fcst[i]<=200 and obs[i]<=300: count+=1
        if fcst[i]>200 and fcst[i]<=300 and obs[i]>100 and obs[i]<=500: count+=1
        if fcst[i]>300 and fcst[i]<=400 and obs[i]>200 and obs[i]<=600: count+=1
        if fcst[i]>400 and fcst[i]<=500 and obs[i]>300 and obs[i]<=800: count+=1
        if fcst[i]>500 and fcst[i]<=600 and obs[i]>400 and obs[i]<=1000: count+=1
        if fcst[i]>600 and fcst[i]<=800 and obs[i]>500 and obs[i]<=1200: count+=1
        if fcst[i]>800 and fcst[i]<=1000 and obs[i]>600 and obs[i]<=1500: count+=1
        if fcst[i]>1000 and fcst[i]<=1500 and obs[i]>800 and obs[i]<=2000: count+=1
        if fcst[i]>1500 and fcst[i]<=2000 and obs[i]>1000 and obs[i]<=2500: count+=1
        if fcst[i]>2000 and fcst[i]<=2500 and obs[i]>1500 and obs[i]<=3000: count+=1
        if fcst[i]>2500 and fcst[i]<=3000 and obs[i]>2000 and obs[i]<=4000: count+=1
        if fcst[i]>3000 and fcst[i]<=4000 and obs[i]>2500 and obs[i]<=5000: count+=1
        if fcst[i]>4000 and fcst[i]<5000 and obs[i]>2500 and obs[i]<=5000: count+=1
        if fcst[i]>=5000 and obs[i]>=4000: count +=1
    return count /len(obs)*100

@typechecked
def calcTCPC(obs:np.ma.array,fcst:np.ma.array,amb:np.ma.array,lat:np.ma.array,pcth:dict,var:str,mode="grid"):
    obs = obs.compressed()
    fcst = fcst.compressed()
    amb = amb.compressed()
    lat = lat.compressed()
    ts = []
    ets = []
    pc = np.nan
    far = []
    mar = []
    rmse = np.nan
    abias = np.nan
    bias = np.nan
    if var in pcth.keys() and len(obs)>5:

        if pcth[var] == tspcth:
            for th in pcth[var][var]:
                # falsealarms = tmp2.query(f"{var}>{th} and {var}obs<={th}").shape[0]
                falsealarms = np.ma.where((fcst>th) & (obs<=th))[0].shape[0]
                # hits = tmp2.query(f"{var}>{th} and {var}obs>{th}").shape[0]
                hits = np.ma.where((fcst>th)&(obs>th))[0].shape[0]
                #misses = tmp2.query(f"{var}<={th} and {var}obs>{th}").shape[0]
                misses = np.ma.where((fcst<=th) &(obs>th))[0].shape[0]
                #correctn = tmp2.query(f"{var}<={th} and {var}obs<={th}").
                correctn = np.ma.where((fcst<=th) & (obs<=th))[0].shape[0]
                total = hits+falsealarms+misses+correctn
                print(hits,misses,correctn,falsealarms,total)
                if (hits+falsealarms+misses+correctn)>0:
                    if total != correctn:
                        ts.append((th, hits/(total-correctn)))
                    else:
                        ts.append((th,np.nan))
                    hitsrandom = (hits+misses)*(hits+falsealarms)/total
                    if total-correctn-hitsrandom != 0:
                        ets.append((th,(hits-hitsrandom)/(total-correctn-hitsrandom)))
                    else:
                        ets.append((th,np.nan)) 
                else:
                    ts.append((th,np.nan))
                    ets.append((th,np.nan))

                if (hits+falsealarms>0):
                    far.append((th,falsealarms/(hits+falsealarms)*100))
                else:
                    far.append((th,np.nan))
                if (hits + misses > 0):
                    mar.append((th,misses/(hits+misses) * 100))
                else:
                    mar.append((th,np.nan))
                if th ==0.1 and "rain" in var:
                    pc = (hits+correctn)/total * 100
                else:
                    pc = np.nan 
                if var == "ch":
                    pc = chpc(obs,fcst)
                if var == "vis":
                    pc = vispc(obs,fcst)
                if var == "lcc" or var == "tcc":
                    pc = cloudpc(obs,fcst)
        elif pcth[var] == multitspcth:
            varth = pcth[var][var][0]
            bnd = pcth[var][var][1]
            for iii in range(len(varth)):
                minth = varth[iii][0]
                maxth = varth[iii][1]
                minbnd = bnd[iii][0]
                maxbnd = bnd[iii][1]
                if minbnd ==1 and maxbnd == 1:
                    hits = np.ma.where((fcst>=minth)& (fcst<=maxth) & (obs>=minth) & (obs<=maxth))[0].shape[0]
                    falsealarms = np.ma.where((fcst>=minth)& (fcst<=maxth))[0].shape[0]-hits
                    misses = np.ma.where((obs>=minth) & (obs<=maxth))[0].shape[0]-hits
                    correctn = fcst.shape[0]-hits-falsealarms-misses
                elif minbnd ==0 and maxbnd ==1:
                    hits = np.ma.where((fcst>minth)& (fcst<=maxth) & (obs>minth) & (obs<=maxth))[0].shape[0]
                    falsealarms = np.ma.where((fcst>minth)& (fcst<=maxth))[0].shape[0]-hits
                    misses = np.ma.where((obs>minth) & (obs<=maxth))[0].shape[0]-hits
                    correctn = fcst.shape[0]-hits-falsealarms-misses                    
                if minbnd ==1 and maxbnd == 0:
                    hits = np.ma.where((fcst>=minth)& (fcst<maxth) & (obs>=minth) & (obs<maxth))[0].shape[0]
                    falsealarms = np.ma.where((fcst>=minth)& (fcst<maxth))[0].shape[0]-hits
                    misses = np.ma.where((obs>=minth) & (obs<maxth))[0].shape[0]-hits
                    correctn = fcst.shape[0]-hits-falsealarms-misses
                if minbnd ==0 and maxbnd == 0:
                    hits = np.ma.where((fcst>minth)& (fcst<maxth) & (obs>minth) & (obs<maxth))[0].shape[0]
                    falsealarms = np.ma.where((fcst>minth)& (fcst<maxth))[0].shape[0]-hits
                    misses = np.ma.where((obs>minth) & (obs<maxth))[0].shape[0]-hits
                    correctn = fcst.shape[0]-hits-falsealarms-misses
                print("XXXXXXXXXXXXXX",var,minth,maxth,"hits:",hits,"fa:",falsealarms,"misses:",misses,"correctn:",correctn)
                if (hits+falsealarms+misses)>0:
                    ts.append((maxth,hits/(hits+falsealarms+misses)))
                else:
                    ts.append((maxth,np.nan))
                if (hits+falsealarms) >0:
                    far.append((maxth,falsealarms/(hits+falsealarms)*100))
                else:
                    far.append((maxth,np.nan))
                if (hits+misses) >0:
                    mar.append((maxth,misses/(hits+misses)*100))   
                else:
                    mar.append((maxth,np.nan))

                if var == "vis":
                    pc = vispc(obs,fcst)
                if var == "lcc" or var == "tcc":
                    pc = cloudpc(obs,fcst)
        elif pcth[var] == degreepcth:
            hits = 0
            pclist = pcth[var][var]
            for i in range(1,len(pclist),1):
                val = pclist[i-1]
                vah = pclist[i]

                find = np.ma.where((fcst<vah) & (fcst>=val) & (obs<vah) &(obs>=val))
                hits += find[0].shape[0]

            pc = hits/len(fcst) *100
        elif pcth[var] == valuepcth:
            pc = np.ma.where(abs(fcst-obs)<pcth[var][var])[0].shape[0]/fcst.shape[0]*100
    else:
        pc = np.nan
    if len(obs)>5:  
        if mode=="aws":
            rmse = np.sqrt(np.nanmean(amb**2))
            bias = np.nanmean(amb)
            abias = np.nanmean(np.abs(amb))
        else:
            rmse = np.sqrt(np.nansum(amb**2*np.cos(lat/180*np.pi))/np.nansum(np.cos(lat/180*np.pi)))
            bias = np.nansum(amb*np.cos(lat/180*np.pi))/np.nansum(np.cos(lat/180*np.pi))
            abias = np.nansum(np.abs(amb)*np.cos(lat/180*np.pi))/np.nansum(np.cos(lat/180*np.pi))


    return pc,ts,ets,far,mar,rmse,bias,abias



def adjustUnits(data:xr.DataArray,var:str):
    pass


if __name__ == "__main__":
    a = np.ma.array(np.random.rand(50))*4+3
    b = a + np.random.rand((len(a)))*1
    amb = a-b 
    lat = np.ma.zeros_like(a)
    print(a)
    print(b)
    print(amb)
    a[0] = 5
    b[0] = 5
    fcst = a
    obs = b
    minth = 0
    maxth = 5
    hits = np.ma.where((fcst>minth)& (fcst<=maxth) & (obs>minth) & (obs<=maxth))[0].shape[0]
    falsealarms = np.ma.where((fcst>minth)& (fcst<=maxth))[0].shape[0]-hits
    misses = np.ma.where((obs>minth) & (obs<=maxth))[0].shape[0]-hits
    correctn = fcst.shape[0]-hits-falsealarms-misses        
    print(calcTCPC(a,b,amb,lat,pcth,"tcc","aws"))

