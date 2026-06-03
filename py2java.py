

def pyweb2java(var):
    translate={
        "2t":"temperature",
        "2d":"dew_point_temperature",
        "2r":"humidity",
        "wind":"wind_speed",
        "wdir":"wind_direction",
        "rain1":"precipitation",
        "rain24":"precipitation_24",
        "sp":"pressure",
        "mslp":"sea_level_pressure",
        "rad":"radiation",
        "vis":"visibility",
        "tcc":"total_cloud_cover",
        "lcc":"low_cloud_cover",
        "ch":"cloud_height",
        "gh":"geo_height",
        "t":"temperature",
        "r":"humidity",
        "NCEP":"ncep",
        "KT1279":"t1279",
        "ECMWF":"ecmwf",
        "CMAGFS":"cmagfs",
        "BUFR":"upper",
        "SELF":"zero-field",
        "ERA5":"era5",
        "AWS":"station",
        "AIRPORT":"airport",
        "CLDAS":"cldas",
        "GTS":"GTS",
        "CMA_GFS":"CMAGFS",
    }

    if var in translate.keys():
        return translate[var]
    else:
        return var
