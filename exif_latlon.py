#! /bin/python3
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_exif(filename):
    """Returns a dictionary of EXIF data from a file"""
    exif_data = {}
    image = Image.open(filename)
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for sub_tag in value:
                        sub_decoded = GPSTAGS.get(sub_tag, sub_tag)
                        gps_data[sub_decoded] = value[sub_tag]

                    exif_data[decoded] = gps_data
                else:
                    exif_data[decoded] = value
        else:
             print("No EXIF data found")
             quit()

        return exif_data
    except:
        print("Exception getting exif dictionary")
        return None

def dms_to_decimal_degrees(ref, dms):
    """Return an EXIF latitude or longitude in deciemal degrees"""
    decimal = dms[0] + (dms[1]/60.0) + (dms[2]/3600.0)
    if (ref == "S") or (ref == "W"):
        decimal = 0 - decimal
    return decimal

def get_lat_lon(imageFile):
    try:
        exif=get_exif(imageFile)
    except:
        print(f"Could not get EXIF info from {imageFile}")
        return None, None

    return dms_to_decimal_degrees(exif['GPSInfo']['GPSLatitudeRef'], exif['GPSInfo']['GPSLatitude']), dms_to_decimal_degrees(exif['GPSInfo']['GPSLongitudeRef'], exif['GPSInfo']['GPSLongitude'])


#print(f"Lat,lon: {get_lat_lon('2024-08-25_Max4/GSAA_Max4/GSAA7867.JPG')}")
