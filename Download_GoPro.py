#! /bin/python3
# FIXME: Replace subprocess execution with direct python calls
# FIXME: Does not work with GoPro MAX and 5Ghz WiFi band
# Upgraded GoProCam to 4.2.0, can now connect WiFi on Hero 10
# Had to go connections->connect device->the remote on Hero 10 every time for BT connection to work but no lo0nger seems required
# Was getting errors doing listMedia on Hero 10 but now working 
import sys
import os
import subprocess
import json
from goprocam import GoProCamera, constants
from exif import Image
from geopy.geocoders import Nominatim
import time
from datetime import datetime

import exif_latlon

configFile = "cameras.json"
sequences=[]

# Check for correct usage: Download_GoPro.py <Camera>
if len(sys.argv) != 2:
    print("Must specify camera to use")
    sys.exit(1)

# Get camera BlueTooth MAC address and Wifi SSID from config file
camera = None
config = json.load(open(configFile, "r"))
for i in config['cameras']:
    if i['camera'] == sys.argv[1]:
        gopro_bt = i['bt']
        gopro_wifi = i['wifi']
        camera = i['camera']
        #print(f"{camera} {gopro_bt} {gopro_wifi}")

if camera is None:
    print(f"No entry for camera {sys.argv[1]} in '{configFile}'")
    sys.exit(1)

# Save SSID for currently connected WiFi
results=subprocess.run(["iwgetid","-r"], capture_output=True, text=True)
ssid=results.stdout.rstrip("\n")

# Try connecting to GoPro via Bluetooth and turning on Wifi,
print(f"Establishing BlueTooth connection to GoPro '{camera}'...")
results=subprocess.run(["python3","../gopro-ble-py/main.py","--address", gopro_bt, "--command", "wifi on"])

# If BT connection fails, prompt user to turn GoPro on and try again...
if results.returncode == 1:
    input(f"Power on GoPro '{camera}' and press <ENTER>: ")
    results=subprocess.run(["python3","../gopro-ble-py/main.py","--address", gopro_bt, "--command", "wifi on"])
    if results.returncode == 1:
        print(f"Unable to connect to camera '{camera}' via BlueTooth and turn on WiFi, aborting")
        sys.exit(1)

# Connect computer to GoPro WiFi
print(f"Connecting to GoPro '{camera}' Wifi network '{gopro_wifi}'...")
results=subprocess.run(["nmcli","c","up", "id", gopro_wifi])
print(f"Status = {results.returncode}")

try:
    gpCam = GoProCamera.GoPro()

except:
    print(f"Unable to connect to GoPro: {sys.exc_info()[0]}");

else:
    # Report camera overview
    gpCam.overview()

    # Place all files beneath a camera specific directory
    now = datetime.now().strftime("%Y-%m-%d") 
    cameraDir=f"{now}_{camera}"
    if not os.path.exists(cameraDir):
        os.makedirs(cameraDir)
    os.chdir(cameraDir)
    print(f"GoPro files will be downloaded to {cameraDir}")

    media = json.loads(gpCam.listMedia())

    for directory in media["media"]:
        dirname  = directory["d"]
        for mediaFile in directory["fs"]:
            filename = mediaFile["n"];

            # If file has a 'b' (begin?) entry, it represents a sequence (timelapse or burst)
            if 'b' in mediaFile:
                base=filename[:4]
                dirName=f"{base}_{camera}"

                # Place each sequence in it's own directory
                if not os.path.exists(dirName):
                    os.makedirs(dirName)
                os.chdir(dirName)

                start=int(mediaFile["b"])
                end=int(mediaFile["l"])
                print(f"---Download sequence of {end-start} images")
                for i in range(start,end+1):
                    image=f"{base}{i:04d}.JPG"
                    if i==start:
                        sequences.append((dirName, image))
                    print(f"   ---Download image {i-start}/{end-start} ",end=" ")
                    gpCam.downloadMedia(dirname,image)
                    gpCam.deleteFile(dirname, image)
                os.chdir("..")
                # TODO: Rename directory here 1 at a time instead of all at once at end
            else:
                # Place non-timelapse files in their own directory
                dirName=f"NonTimeLapse_{camera}"
                if not os.path.exists(dirName):
                    os.makedirs(dirName)
                os.chdir(dirName)
                image=mediaFile['n']
                print(f"---Download non-timelapse file ",end=" ")
                gpCam.downloadMedia(dirname,filename)
                gpCam.deleteFile(dirname, filename)
                os.chdir("..")

    print("Turning off GoPro...")
    gpCam.power_off()

# FIXME: ssid as reported by iwgetid is not always the same as name/id used by nmcli
print(f"Re-connecting to previous WiFi network '{ssid}'...")
# DNF Using hardcoded name iso ssid here to get around the above FIXME
subprocess.run(["nmcli","c","up", "id", "Auto UnifiAP5"])

# Rename directories based on location reverse geocoded from exif lat, long of first image in each sequence
geolocator = Nominatim(user_agent="GoPro_Transfer")

for dirName, fileName in sequences:
    fullName=os.path.join(dirName,fileName)
    print(f"Moving {fullName}...")
    lat,lon = exif_latlon.get_lat_lon(fullName)
    if lat is None:
        print("No lat/lon, not moving")
    else:
        location = geolocator.reverse((lat, lon))

        locName=""
        if 'hamlet' in location.raw['address']:
            locName=location.raw['address']['hamlet']
        elif 'suburb' in location.raw['address']:
            locName=location.raw['address']['suburb']
        elif 'town' in location.raw['address']:
            locName=location.raw['address']['town']
        elif 'city' in location.raw['address']:
            locName=location.raw['address']['city']
        else:
            print(f"{fullName} No location from - {location.raw}")

        locName=locName.replace(" ","_")
        print(locName)
        os.rename(dirName, f"{dirName}_{locName}")
        time.sleep(2)  # Delay so as to be a good citizen and not abuse nominatim
    print()
