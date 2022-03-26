#! /bin/python3
import sys
import os
import subprocess
import json
from goprocam import GoProCamera, constants

# Currently hard coded for my Hero 5
gopro_wifi="GP54508924"
gopro_bt="D8:59:3A:63:0A:8F"
camera="_GP5"

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

    # TODO: Check this works for all sequences, accross directories etc.
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
                    gpCam.downloadMedia(dirname, image)
                    gpCam.deleteFile(dirname,  image)
                os.chdir("..")
            else:
                print(f"Ignoring non timelapse file {mediaFile['n']}")

    # TODO: Check all downloads and deletes have completed before powering off
    print("Turning off GoPro...")
    gpCam.power_off()

# FIXME: ssid as reported by iwgetid is not always the same as name/id used by nmcli so this can fail
print(f"Re-connecting to previous WiFi network '{ssid}'...")
subprocess.run(["nmcli","c","up", "id", ssid])
