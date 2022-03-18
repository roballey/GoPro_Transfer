#! /bin/python3
# FIXME: Replace subprocess execution with direct python calls
import sys
import os
import subprocess
import re
from goprocam import GoProCamera, constants

# Currently hard coded for my Max
gopro_wifi="RobsMax360"
gopro_bt="DF:3D:67:5C:26:b8"
local_dir="Timelapse_Max"

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

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    os.chdir(local_dir)

    medialist = gpCam.listMedia(format=True, media_array=True)

    for media in medialist:
        # TODO: Find a better way of detecting time lapse photos than this regexp, can we use media[2] or [3]?
        match = re.match("GS[A-Z][A-Z]", media[1])
        if match:
            # TODO: download to a specified directory
            gpCam.downloadMultiShot(f"{media[0]}/{media[1]}")

    print("Turning off GoPro...")
    gpCam.power_off()

# FIXME: Why does reconnecting to UnifiAP throw an error but others work ok?
print(f"Re-connecting to previous WiFi network '{ssid}'...")
subprocess.run(["nmcli","c","up", "id", ssid])
