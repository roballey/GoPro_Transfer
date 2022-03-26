#! /bin/python3
# FIXME: Replace subprocess execution with direct python calls
import sys
import os
import subprocess
import json
from goprocam import GoProCamera, constants
from exif import Image

# Currently hard coded for my Max
gopro_wifi="RobsMax360"
gopro_bt="DF:3D:67:5C:26:b8"
camera="Max"

# Save SSID for currently connected WiFi
results=subprocess.run(["iwgetid","-r"], capture_output=True, text=True)
ssid=results.stdout.rstrip("\n")

# Try connecting via Bluetooth and turning on Wifi,
print(f"Establishing BT connection to GoPro...")
results=subprocess.run(["python3","../gopro-ble-py/main.py","--address", gopro_bt, "--command", "wifi on"])

# If BT connection fails, prompt user to turn GoPro on and try again...
if results.returncode == 1:
    input("Power on GoPro and press <ENTER>: ")
    results=subprocess.run(["python3","../gopro-ble-py/main.py","--address", gopro_bt, "--command", "wifi on"])
    if results.returncode == 1:
        print("Unable to connect via BT and turn on WiFi, aborting")
        sys.exit(1)

# Connect computer to GoPro WiFi
print(f"Connecting to GoPro Wifi network {gopro_wifi}...")
results=subprocess.run(["nmcli","c","up", "id", gopro_wifi])
print(f"Status = {results.returncode}")

try:
    gpCam = GoProCamera.GoPro()

except:
    print(f"Unable to connect to GoPro: {sys.exc_info()[0]}");

else:
    print("Connected to GoPro")

    # Place all images beneath a camera specific directory
    if not os.path.exists(camera):
        os.makedirs(camera)
    os.chdir(camera)

    sequences=[]
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
                for i in range(start,end+1):
                    image=f"{base}{i:04d}.JPG"
                    #print(f"Download then delete {dirname}/{image}")
                    if i==start:
                        sequences.append((dirName, image))
                    gpCam.downloadMedia(dirname,image)
                    gpCam.deleteFile(dirname, image)
                os.chdir("..")
            else:
                print(f"Ignoring non timelapse file {mediaFile['n']}")

    print("Turning off GoPro...")
    gpCam.power_off()

# FIXME: ssid as reported by iwgetid is not always the same as name/id used by nmcli
print(f"Re-connecting to previous WiFi network '{ssid}'...")
# DNF Using hardcoded name iso ssid here to get around the above FIXME
subprocess.run(["nmcli","c","up", "id", "Auto UnifiAP5"])

# Rename directories based on location reverse geocoded from exif lat, long of first image in each sequence
# FIXME: Falling over when trying to get exif lat, long
#for seq in sequences:
#    print(f"Transferred sequence {seq[0]}/{seq[1]}")
#    with open(f'{seq[0]}/{seq[1]}', 'rb') as image_file:
#        my_image = Image(image_file)
# TODO: Will need to handle if first image doesnt have lat long but later images do
#        print(f"lat {my_image.gps_latitude}, long {my_image.gps_longitude}")
# TODO: Reverse geocode with lat, long and rename directory
