from email.mime import base
import json
import datetime
import copy
from netCDF4 import Dataset
import os

base_dir = os.getcwd()
with open(base_dir+"/quantimize/data/atmo.json", "rb") as f:
    atmo_data = json.loads(f.read().decode("utf-8"))
with open(base_dir+"/quantimize/data/bada_data.json", "rb") as f:
    flight_level_data = json.loads(f.read().decode("utf-8"))
with open(base_dir+"/quantimize/data/flights.json","rb") as f:
    flight_data = json.loads(f.read().decode("utf-8"))
nc = Dataset(base_dir+"/quantimize/data/aCCf_0623_p_spec.nc")

def get_flight_info(flight_nr):
    """Return the flight information for a given flight number

    Args:
        flight_nr (int/str/float): Flight number

    Returns:
        dict: Flight number information
    """
    start_time = datetime.datetime.strptime(flight_data[str(flight_nr)]["start_time"], "%H:%M:%S")
    start_time = datetime.time(start_time.hour, start_time.minute, start_time.second)
    this_flight = copy.copy(flight_data[str(flight_nr)])
    this_flight["start_time"] = start_time
    return this_flight

def get_fl(arb_fl):
    """Find next available flightlevel to given level

    Args:
        arb_fl (int/str/float): Current flight level

    Returns:
        str: Flighlevel for atmo data
    """
    arb_fl = int(arb_fl)
    diff = arb_fl%20
    if diff == 0:
        pass
    elif diff >= 10:
        arb_fl = arb_fl+20-diff
    elif diff < 10:
        arb_fl = arb_fl-diff
    return str(arb_fl)

def get_flight_level_data(flight_level):
    """Return information to the next available flight level

    Args:
        flight_level (int/float/str): Flight level

    Returns:
        dict: Dictionary containing information about the flight level
    """
    flight_level = get_fl(flight_level)
    return flight_level_data[flight_level]

def get_long(arb_long):
    """Convert and get longitute ready for data access

    Args:
        arb_long (int/str/float): Longitude value

    Returns:
        str: Converted longitude value for atmo data
    """
    arb_long = float(arb_long)
    diff = arb_long%2
    if diff == 0:
        return str(arb_long)
    elif diff > 0.5 and diff < 1:
        return str(round(arb_long-1,0))
    elif diff >=1 and diff <= 1.5:
        return str(round(arb_long+1,0))
    else:
        return str(round(arb_long,0))

def get_lat(arb_lat):
    """Convert and get latitude ready for data access

    Args:
        arb_lat (int/str/float): Latitude value

    Returns:
        str: Convert latitude value for atmo data
    """
    arb_lat = float(arb_lat)
    diff = arb_lat%2
    if diff == 0:
        return str(arb_lat)
    elif diff > 0.5 and diff < 1:
        return str(round(arb_lat-1,0))
    elif diff >=1 and diff <= 1.5:
        return str(round(arb_lat+1,0))
    else:
        return str(round(arb_lat,0))

def avoid_empty_atmo_data(fl):
    """Avoid flightlevels without data, give back closest data

    Args:
        fl (int): Flightlevel to check

    Returns:
        int: Corrected flighlevel
    """
    if fl < 140:
        return 140
    elif fl == 220:
        return 200
    elif fl == 280:
        return 260
    elif fl == 320:
        return 300
    elif fl > 380:
        return 380
    else:
        return fl

def get_fl_atmo(arb_fl):
    """Find next available flightlevel to given level

    Args:
        arb_fl (int/str/float): Current flight level

    Returns:
        str: Flighlevel for atmo data
    """
    arb_fl = int(arb_fl)
    diff = arb_fl%20
    if diff == 0:
        pass
    elif diff >= 10:
        arb_fl = arb_fl+20-diff
    elif diff < 10:
        arb_fl = arb_fl-diff
    arb_fl = avoid_empty_atmo_data(arb_fl)
    return str(arb_fl)

def get_time(arb_time):
    """Get the corresponding time for the atmo data

    Args:
        arb_time (time): Current time of the airplane

    Returns:
        str: Corresponding time for atmo data
    """
    arb_time = datetime.datetime(2018,6,23,arb_time.hour,arb_time.minute,arb_time.second)
    six_am = datetime.datetime(2018,6,23,6)
    twelve = datetime.datetime(2018,6,23,12)
    six_pm = datetime.datetime(2018,6,23,18)
    if arb_time >= six_am and arb_time < twelve:
        return six_am.strftime("%H:%M:%S")
    elif arb_time >= twelve and arb_time < six_pm:
        return twelve.strftime("%H:%M:%S")
    elif arb_time >= six_pm:
        return six_pm.strftime("%H:%M:%S")

def get_merged_atmo_data(arb_long, arb_lat, arb_fl, arb_time):
    """Returns the merged climate impact data for a given set of location, flightlevel and time

    Args:
        arb_long (int/str/float): Current longitude
        arb_lat (int/str/float): Current latitude
        arb_fl (int/str/float): Current flightlevel
        arb_time (datetime.time): Current time

    Raises:
        Exception: If time was not a datetime.time object

    Returns:
        float: Merged climate data
    """
    LONG = get_long(arb_long)
    LAT = get_lat(arb_lat)
    FL = get_fl_atmo(arb_fl)
    if type(arb_time) is datetime.time:
        TIME = get_time(arb_time)
    else:
        raise Exception("Time is not a time object")
    print(LONG, LAT, FL, TIME)
    return atmo_data[LONG][LAT][FL][TIME]["MERGED"]

def get_atmo_raw_data():
    """Returns the raw data of the nc atmo fil

    Returns:
        quintuple: Latitude, Longitude, Time, FL, Merged data
    """
    lat = nc.variables["LATITUDE"][:]
    long = nc.variables["LONGITUDE"][:]
    time = nc.variables["TIME"][:].tolist()
    fl = nc.variables["LEVEL11_24"][:].tolist()
    atmo_data = nc.variables["MERGED"][:]
    return lat, long, time, fl, atmo_data

def get_hPa(fl):
    fl = int(get_fl(fl))
    if fl <= 140:
        return 600
    elif fl == 160:
        return 550
    elif fl == 180:
        return 500
    elif fl == 200:
        return 450
    elif fl == 220:
        return 450
    elif fl == 240:
        return 400
    elif fl == 260:
        return 350
    elif fl == 280:
        return 350
    elif fl == 300:
        return 300
    elif fl == 320:
        return 300
    elif fl == 340:
        return 250
    elif fl == 360:
        return 225
    elif fl >= 380:
        return 200