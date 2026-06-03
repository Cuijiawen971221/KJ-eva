import numpy as np
import os
import yaml
from types import SimpleNamespace

def plev(fcst,anal,output,cmean):
    fcstroot="/home/yunyao/workshop/met/met_backend/fcst/{:s}/".format(fcst)
    analroot="/home/yunyao/workshop/met/met_backend/fcst/{:s}/".format(anal)
    outputroot="/home/yunyao/workshop/met/met_backend/output/{:s}".format(output)
    cmeanroot="/home/yunyao/workshop/met/met_backend/{:s}/".format(cmean)
    return fcstroot,analroot,outputroot,cmeanroot

def dict_to_namespace(d):
    if isinstance(d,dict):
        return SimpleNamespace(**{k:dict_to_namespace(v) for k,v in d.items()})
    elif isinstance(d, list):
        return [ dict_to_namespace(item) for item in d]
    else:
        return d


class pparms():
    def __init__(self,filename):
        with open (filename) as f:
            pinall = yaml.safe_load(f)
            ymlparam = dict_to_namespace(pinall)

        self.param = ymlparam

        self.obj = pinall
        if "kt1279fcstpath" in pinall.keys() :
            self.kt1279fcstpath=pinall["kt1279fcstpath"]
        if "kt1279cloudfcstpath" in pinall.keys() :
            self.kt1279cloudfcstpath=pinall["kt1279cloudfcstpath"]
        if "visfcstfcstpath" in pinall.keys() :
            self.visfcstfcstpath=pinall["visfcstfcstpath"]
        if "ncepfcstpath" in pinall.keys() :
            self.ncepfcstpath=pinall["ncepfcstpath"]      
        if "era5fcstpath" in pinall.keys() :
            self.era5fcstpath=pinall["era5fcstpath"]
        if "ecmwffcstpath" in pinall.keys() :
            self.ecmwffcstpath=pinall["ecmwffcstpath"]
        if "autofcstpath" in pinall.keys() :
            self.autofcstpath=pinall["autofcstpath"]
        if "regionfcstpath" in pinall.keys() :
            self.regionfcstpath=pinall["regionfcstpath"]
        if "kjrhfcstpath" in pinall.keys():
            self.kjrhfcstpath=pinall["kjrhfcstpath"]
 
            
        if "kt1279outputpath" in pinall.keys() :
            self.kt1279outputpath=pinall["kt1279outputpath"]
        if "kt1279cloudoutputpath" in pinall.keys() :
            self.kt1279cloudoutputpath=pinall["kt1279cloudoutputpath"]
        if "visfcstoutputpath" in pinall.keys() :
            self.visfcstoutputpath=pinall["visfcstoutputpath"]
        if "ncepoutputpath" in pinall.keys() :
            self.ncepoutputpath=pinall["ncepoutputpath"]      
        if "era5outputpath" in pinall.keys() :
            self.era5outputpath=pinall["era5outputpath"]
        if "ecmwfoutputpath" in pinall.keys():
            self.ecmwfoutputpath = pinall["ecmwfoutputpath"]
        if "autooutputpath" in pinall.keys():
            self.autooutputpath = pinall["autooutputpath"]
        if "regionoutputpath" in pinall.keys():
            self.regionoutputpath = pinall["regionoutputpath"]
        if "kjrhoutputpath" in pinall.keys():
            self.kjrhoutputpath = pinall["kjrhoutputpath"]
            

        if "kt1279toolspath" in pinall.keys() :
            self.kt1279toolspath=pinall["kt1279toolspath"]
        if "kt1279cloudtoolspath" in pinall.keys() :
            self.kt1279cloudtoolspath=pinall["kt1279cloudtoolspath"]
        if "visfcsttoolspath" in pinall.keys() :
            self.visfcsttoolspath=pinall["visfcsttoolspath"]
        if "nceptoolspath" in pinall.keys() :
            self.nceptoolspath=pinall["nceptoolspath"]      
        if "era5toolspath" in pinall.keys() :
            self.era5toolspath=pinall["era5toolspath"]
        if "ecmwftoolspath" in pinall.keys():
            self.ecmwftoolspath = pinall["ecmwftoolspath"]
        if "autotoolspath" in pinall.keys():
            self.autotoolspath = pinall["autotoolspath"]
        if "regiontoolspath" in pinall.keys():
            self.regiontoolspath = pinall["regiontoolspath"]
        if "kjrhtoolspath" in pinall.keys():
            self.kjrhtoolspath = pinall["kjrhtoolspath"]

        ####################################################
        if "kt1279th" in pinall.keys():
            self.kt1279th = pinall["kt1279th"]
        if "ecmwfth" in pinall.keys():
            self.ecmwfth = pinall["ecmwfth"]
        if "ncepth" in pinall.keys():
            self.ncepth = pinall["ncepth"]
        if "cldasth" in pinall.keys():
            self.cldasth = pinall["cldasth"]
        if "autoth" in pinall.keys():
            self.autoth = pinall["autoth"]
        if "kt1279cloudth" in pinall.keys():
            self.kt1279cloudth = pinall["kt1279cloudth"]
        if "visfcstth" in pinall.keys():
            self.visfcstth = pinall["visfcstth"]
        if "regionth" in pinall.keys():
            self.regionth = pinall["regionth"]
        if "kjrhth" in pinall.keys():
            self.kjrhth = pinall["kjrhth"]

        #####################################################
        if "kt1279awspoint" in pinall.keys():
            self.kt1279awspoint = pinall["kt1279awspoint"]
        if "kt1279metpath" in pinall.keys():
            self.kt1279metpath = pinall["kt1279metpath"]
        if "kt1279obspath" in pinall.keys():
            self.kt1279obspath = pinall["kt1279obspath"]
        if "kt1279weightpoint" in pinall.keys():
            self.kt1279weightpoint = pinall["kt1279weightpoint"]
        ######################################################
        if "ncepawspoint" in pinall.keys():
            self.ncepawspoint = pinall["ncepawspoint"]
        if "ncepmetpath" in pinall.keys():
            self.ncepmetpath = pinall["ncepmetpath"]
        if "ncepobspath" in pinall.keys():
            self.ncepobspath = pinall["ncepobspath"]
        if "ncepweightpoint" in pinall.keys():
            self.ncepweightpoint = pinall["ncepweightpoint"]
        #####################################################
        if "ecmwfawspoint" in pinall.keys():
            self.ecmwfawspoint = pinall["ecmwfawspoint"]
        if "ecmwfmetpath" in pinall.keys():
            self.ecmwfmetpath = pinall["ecmwfmetpath"]
        if "ecmwfobspath" in pinall.keys():
            self.ecmwfobspath = pinall["ecmwfobspath"]
        if "ecmwfweightpoint" in pinall.keys():
            self.ecmwfweightpoint = pinall["ecmwfweightpoint"]
        ###############################################################
        if "kt1279cloudawspoint" in pinall.keys():
            self.kt1279cloudawspoint = pinall["kt1279cloudawspoint"]
        if "kt1279cloudmetpath" in pinall.keys():
            self.kt1279cloudmetpath = pinall["kt1279cloudmetpath"]
        if "kt1279cloudobspath" in pinall.keys():
            self.kt1279cloudobspath = pinall["kt1279cloudobspath"]
        if "kt1279cloudweightpoint" in pinall.keys():
            self.kt1279cloudweightpoint = pinall["kt1279cloudweightpoint"]
        ###############################################################
        if "visfcstawspoint" in pinall.keys():
            self.visfcstawspoint = pinall["visfcstawspoint"]
        if "visfcstmetpath" in pinall.keys():
            self.visfcstmetpath = pinall["visfcstmetpath"]
        if "visfcstobspath" in pinall.keys():
            self.visfcstobspath = pinall["visfcstobspath"]
        if "visfcstweightpoint" in pinall.keys():
            self.visfcstweightpoint = pinall["visfcstweightpoint"]
        ###############################################################
        if "autoawspoint" in pinall.keys():
            self.autoawspoint = pinall["autoawspoint"]
        if "autometpath" in pinall.keys():
            self.autometpath = pinall["autometpath"]
        if "autoobspath" in pinall.keys():
            self.autoobspath = pinall["autoobspath"]
        if "autoweightpoint" in pinall.keys():
            self.autoweightpoint = pinall["autoweightpoint"]
        ###############################################################
        if "regionawspoint" in pinall.keys():
            self.regionawspoint = pinall["regionawspoint"]
        if "regionmetpath" in pinall.keys():
            self.regionmetpath = pinall["regionmetpath"]
        if "regionobspath" in pinall.keys():
            self.regionobspath = pinall["regionobspath"]
        if "regionweightpoint" in pinall.keys():
            self.regionweightpoint = pinall["regionweightpoint"]
        ###############################################################
        if "kjrhawspoint" in pinall.keys():
            self.kjrhawspoint = pinall["kjrhawspoint"]
        if "kjrhmetpath" in pinall.keys():
            self.kjrhmetpath = pinall["kjrhmetpath"]
        if "kjrhobspath" in pinall.keys():
            self.kjrhobspath = pinall["kjrhobspath"]
        if "kjrhweightpoint" in pinall.keys():
            self.kjrhweightpoint = pinall["kjrhweightpoint"]

##############################
        if "cmeanpath" in pinall.keys() :
            self.cmeanpath=pinall["cmeanpath"]
            
        if "projMainDir" in pinall.keys():
            self.projMainDir = pinall["projMainDir"]

#######################################################
        if "cldasfcstpath" in pinall.keys() :
            self.cldasfcstpath=pinall["cldasfcstpath"]
        if "cldasoutputpath" in pinall.keys() :
            self.cldasoutputpath=pinall["cldasoutputpath"]
        if "cldasmetpath" in pinall.keys() :
            self.cldasmetpath=pinall["cldasmetpath"]
        if "cldastoolspath" in pinall.keys() :
            self.cldastoolspath=pinall["cldastoolspath"]
        if "cldasobspath" in pinall.keys():
            self.cldasobspath = pinall["cldasobspath"]
        if "cldasweightpoint" in pinall.keys():
            self.cldasweightpoint = pinall["cldasweightpoint"]
        if "cldasawspoint" in pinall.keys():
            self.cldasawspoint = pinall["cldasawspoint"]



########################plev grid############################
        if "plevcmeanroot" in pinall.keys():
            self.plevcmeanroot = pinall["plevcmeanroot"]
        if "plevfcstroot" in pinall.keys():
            self.plevfcstroot = pinall["plevfcstroot"]
        if "plevoutputroot" in pinall.keys():
            self.plevoutputroot = pinall["plevoutputroot"]
        if "plevobsroot" in pinall.keys():
            self.plevobsroot = pinall["plevobsroot"]

########################surf grid#############################
        if "surffcstroot" in pinall.keys():# 模式数据和ERA5 用这个
            self.surffcstroot = pinall["surffcstroot"]
        if "surfobsroot" in pinall.keys(): #CLDA 利用这个
            self.surfobsroot = pinall["surfobsroot"]
        if "maskroot" in pinall.keys():
            self.maskroot = pinall["maskroot"]

#######################################DB#######################################  
        if "clickhouseIP" in pinall.keys():
            self.clickhouseIP = pinall["clickhouseIP"]
        if "clickhousePort" in pinall.keys():
            self.clickhousePort = pinall["clickhousePort"]          
        if "clickhouseUsername" in pinall.keys():
            self.clickhouseUsername = pinall["clickhouseUsername"]            
        if "clickhousePassword" in pinall.keys():
            self.clickhousePassword = pinall["clickhousePassword"]            
        if "clickhouseDatabase" in pinall.keys():
            self.clickhouseDatabase = pinall["clickhouseDatabase"]
      
#################################GTS 配置#####################################
        if "gtsorigpath" in pinall.keys():
            self.gtsorigpath = pinall["gtsorigpath"]
        if "gtstmppath" in pinall.keys():
            self.gtstmppath = pinall["gtstmppath"]
        if "gtsoutputpath" in pinall.keys():
            self.gtsoutputpath = pinall["gtsoutputpath"]        
        if "gtsbinpath" in pinall.keys():
            self.gtsbinpath = pinall["gtsbinpath"]        
############################### MPIRUN ######################################
        if "model" in pinall.keys():
            self.model = pinall["model"]
        if "message" in pinall.keys():
            self.message = pinall["message"]
        if "clickTofile" in pinall.keys():
            self.clickTofile = pinall["clickTofile"]
        if "use_DB" in pinall.keys():
            self.use_DB = pinall["use_DB"]

ymlConf = pparms("./pathconfig.yaml").param

JOB={"KT1279": np.concatenate((np.arange(0,99,1),np.arange(99,120,3),np.arange(120,241,6))),
     "NCEP": np.arange(0,241,3),
     "ECMWF": np.concatenate((np.arange(0,78,3),np.arange(78,246,6))),
     "KT1279_CLOUD": np.arange(0,73,1),
     "VISFCST": np.arange(0,49,1),
     "AUTO": np.arange(0,241,3),
     "CLIMATE": np.arange(0,24*61,24),
     "CMA_GFS":np.arange(0,241,3),
     "EMEND":np.arange(1,73,1),
     "REGION":np.arange(0,73,1),
     "KJRH":np.arange(0,73,1),
    }
