#! /bin/python3
# FIXME: Does not work with GoPro MAX and 5Ghz WiFi band
#
# Changes:
#  - Upgraded GoProCam to 4.2.0, can now connect WiFi on Hero 10
#  - Replaced ble subprocess execution with direct python calls
#  - Updated exif_latlon.py
#  - WIP: improve modularisation
#  - WIP: Also support direct transfer of MTP mounted GoPro (works except for directory renaming)

import sys
import os
from pathlib import Path
import shutil
import subprocess
import json
from goprocam import GoProCamera, constants
from exif import Image
from geopy.geocoders import Nominatim
import time
from datetime import datetime
import exif_latlon
import asyncio
import argparse
import re
from tqdm import tqdm

from gopro_ble import main as ble

configFile = Path.home() / ".config" / "goprotransfer.json"
sequences=[]

def rename_directories(sequences):
    # Rename directories based on location reverse geocoded from exif lat, long of first image in each sequence
    print("Renaming directories")
    print("-------------------------------------------------------\n")
    geolocator = Nominatim(user_agent="GoPro_Transfer")

    for dirName, fileName in sequences:
        fullName=os.path.join(dirName,fileName)
        print(f"Renaming {dirName} based on {fileName} ...")
        try:
            lat,lon = exif_latlon.get_lat_lon(fullName)
            if lat is None:
                print("No lat/lon, not moving")
            else:
                location = geolocator.reverse((lat, lon))

                locName=""
                if 'hamlet' in location.raw['address']:
                    locName=location.raw['address']['hamlet']
                elif 'village' in location.raw['address']:
                    locName=location.raw['address']['village']
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
        except Exception as inst:
            print(f"Unable to rename {dirName}, exception {type(inst)}")

def CreateDir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def CreateAndChangeToDestDir(camera):
    now = datetime.now().strftime("%Y-%m-%d") 
    directory=f"{now}_{camera}"
    if not os.path.exists(directory):
        print(f"Creating directory '{directory}'")
        os.makedirs(directory)
    else:
        print(f"Using existing directory '{directory}'")
    print(f"GoPro files will be transferred to {directory}")
    print("-------------------------------------------------------\n")
    os.chdir(directory)

#==============================================================================
parser = argparse.ArgumentParser(
                    prog='Download_GoPro',
                    description='Transfer files from GoPro to computer')
parser.add_argument('-dm', '--dont-move', help="Don't move files from camera (copy instead), for development use",
                    action='store_true') 

parser.add_argument('Camera', help="Name of camera from which to transfer")
args = parser.parse_args()

if args.dont_move:
    print(f"\nCopying instead of moving files\n")
    mtp_transfer=shutil.copy
else:
    mtp_transfer=shutil.move

print(f"\n\nTransferring files from GoPro '{args.Camera}'")
print("=======================================================\n")

if not os.path.exists(configFile):
    print(f"ERROR: Config file '{configFile}' does not exist")
    quit()

# Get camera details from config file
camera = None
config = json.load(open(configFile, "r"))

# WIP: put all files relative to workDir (see dirName below)
workDir = config['work_dir']

for i in config['cameras']:
    if i['camera'] == args.Camera:
        gopro_bt = i['bt']
        gopro_wifi = i['wifi']
        gopro_mtp = i['mtp']
        camera = i['camera']
        #print(f"{camera} {gopro_bt} {gopro_wifi}")

if camera is None:
    print(f"No entry for camera '{args.Camera}' in '{configFile}'")
    sys.exit(1)

if os.path.exists(gopro_mtp):
    print(f"{camera} connected via USB/MTP.")

    src_dir=f"{gopro_mtp}/GoPro MTP Client Disk Volume/DCIM"
    if os.path.exists(src_dir):
        now = datetime.now().strftime("%Y-%m-%d") 
        dest_dir=os.path.join(workDir,f"{now}_{camera}")

        dest_still_dir=os.path.join(dest_dir,f"Stills")
        dest_video_dir=os.path.join(dest_dir,f"Video")

        print(f"Transfering files from beneath '{src_dir}' to '{dest_dir}'...")
        for root, dirs, files in os.walk(src_dir, topdown=False):
            num_files=len(files)
            with tqdm(total=num_files) as pbar:
                for file in files:
                    pbar.update(1)
                    src_file=os.path.join(root,file)
                    if re.match("GS__.*\.JPG",file):
                        CreateDir(dest_still_dir)
                        #print(f"Still Image {file} -> {dest_still_dir}")
                        mtp_transfer(f"{src_file}", dest_still_dir)
                    elif re.match("GS.*\.JPG",file):
                        dest_seq_dir=os.path.join(dest_dir,"Seq_"+file[:4])
                        CreateDir(dest_seq_dir)
                        #print(f"Seq. Image {file} -> {dest_seq_dir}")
                        mtp_transfer(f"{src_file}", dest_seq_dir)
                    elif re.match("GS.*\.(360|LRV|THM)",file):
                        CreateDir(dest_video_dir)
                        #print(f"Video {file} -> {dest_video_dir}")
                        mtp_transfer(f"{src_file}", dest_video_dir)
            for directory in dirs:
                print(f"Dir {directory}")
        quit()

        if args.dont_move:
            shutil.copy(f"{src_dir}", dest_dir)
        else:
            shutil.move(f"{src_dir}", dest_dir)

        # FIXME: Build list of directory and filenames in sequences for rename_directories

        print(f"Transfer done.")
    else:
        print(f"ERROR: Could not find GoPro MTP source directory'{src_dir}'")
        quit()

    # FIXME: Move to end of script once below FIXME is fixed
    subprocess.Popen(["nemo",dest_dir], start_new_session=True)

    # FIXME: Remove quit once sequences is built
    quit()

else:
    print(f"'{gopro_mtp} does not exist")
    quit()   # FIXME: for development
    print("Camera not connected via USB/MTP, trying Bluetooth/WiFi")

    # Save SSID for currently connected WiFi
    results=subprocess.run(["iwgetid","-r"], capture_output=True, text=True)
    ssid=results.stdout.rstrip("\n")

    # Try connecting to GoPro via Bluetooth and turning on Wifi,
    print(f"Establishing BlueTooth connection to GoPro '{camera}'...")
    print("-------------------------------------------------------\n")
    bt_connected=False
    bt_tried=0

    while ( (not bt_connected) and (bt_tried < 2)):
        try:
          bt_tried = bt_tried+1
          print(f"  Connection attempt {bt_tried}")
          asyncio.run(ble.run(gopro_bt, "wifi on"))

        # If BT connection fails, prompt user to turn GoPro on and try again...
        except:
            if (bt_tried < 2):
              print(f"  Unable to connect via Bluetooth")
              input(f"    Ensure remote is not connected.\n    Power on GoPro '{camera}' and press <ENTER>: ")

        else:
            bt_connected=True

    if (not bt_connected):
      print(f"Unable to connect to '{camera}' via Bluetooth")
      sys.exit(1)

    # Connect computer to GoPro WiFi
    print(f"Connecting to GoPro '{camera}' Wifi network '{gopro_wifi}'...")
    print("-------------------------------------------------------\n")
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
        CreateAndChangeToDestDir(camera)

        media = json.loads(gpCam.listMedia())

        for directory in media["media"]:
            srcdirname  = directory["d"]
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
                        gpCam.downloadMedia(srcdirname,image)
                        gpCam.deleteFile(srcdirname, image)
                    os.chdir("..")
                else:
                    # Place non-timelapse files in their own directory
                    dirName=f"NonTimeLapse_{camera}"
                    if not os.path.exists(dirName):
                        os.makedirs(dirName)
                    os.chdir(dirName)
                    image=mediaFile['n']
                    print(f"---Download non-timelapse file ",end=" ")
                    gpCam.downloadMedia(srcdirname,filename)
                    gpCam.deleteFile(srcdirname, filename)
                    os.chdir("..")

        print("Turning off GoPro...")
        print("-------------------------------------------------------\n")
        gpCam.power_off()

    # FIXME: ssid as reported by iwgetid is not always the same as name/id used by nmcli (sometimes it has "Auto" pre-pended)
    print(f"Re-connecting to previous WiFi network '{ssid}'...")
    print("-------------------------------------------------------\n")
    subprocess.run(["nmcli","c","up", "id", ssid])

    time.sleep(2)  # Delay to ensure network reconnection is complete

print("Renaming directories...")
rename_directories(sequences)
