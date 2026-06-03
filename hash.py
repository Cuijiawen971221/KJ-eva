import hashlib


sql = f"""
        SELECT id, region_name, region_code, left_top_lon, left_top_lat, right_bottom_lon, right_bottom_lat FROM szybjydb.sys_region_config
        """
hashstr = hashlib.sha256(sql.replace(" ","").encode("utf-8")).hexdigest()
print(hashstr)

