#! /bin/python3
from PIL import Image, ExifTags

sequences = [("Test_Images","Max_GPS.JPG"), ("Test_Images","Max_NoGPS.JPG")]

# Get a float from numerator and denominator pair
get_float = lambda x: float(x[0]) / float(x[1])

# Convert exif degree, minute, seconds as num/denom to decimal degrees
def convert_to_degrees(value):
    deg = get_float(value[0])
    minutes = get_float(value[1])
    seconds = get_float(value[2])
    return deg + (minutes / 60.0) + (seconds / 3600.0)

# Extract decimal latitude and longitude from exif dictionary
def extract_lat_lon(exif):
    try:
        gps_latitude = exif[34853][2]
        gps_latitude_ref = exif[34853][1]
        gps_longitude = exif[34853][4]
        gps_longitude_ref = exif[34853][3]
        lat = convert_to_degrees(gps_latitude)
        if gps_latitude_ref != "N":
            lat = -lat

        lon = convert_to_degrees(gps_longitude)
        if gps_longitude_ref != "E":
            lon = -lon
        return lat, lon
    except KeyError:
        return None, None

def get_lat_lon(imageFile):
    try:
        image = Image.open(imageFile)
    except:
        print(f"Could not open {imageFile}")
        return None, None

    exif = image.getexif()
    if exif is None:
        print('No exif data')
        return None, None
    return extract_lat_lon(exif)
