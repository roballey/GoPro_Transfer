#! /bin/python3
# FIXME: Does not work with GoPro MAX and 5Ghz WiFi band
# FIXME: Not deleting images from Hero 10 when transfering via WiFi?
# FIXME: Not robust to Nominatum connection failures (causes MTB Tx to abort)
#
# Changes:
#  - Upgraded GoProCam to 4.2.0, can now connect WiFi on Hero 10
#  - Replaced ble subprocess execution with direct python calls
#  - Updated exif_latlon.py
#  - WIP: improve modularisation
#  - Also support direct transfer of MTP mounted GoPro
#  - Run from any directory and write files to "work_dir" from config file

import sys
import os
from pathlib import Path
import shutil
import subprocess
import json
from goprocam import GoProCamera, constants
#from exif import Image
from geopy.geocoders import Nominatim
import time
from datetime import datetime
import asyncio
import argparse
import re
from tqdm import tqdm

import exif_latlon
from gopro_ble import main as ble

configFile = Path.home() / ".config" / "goprotransfer.json"
sequences=[]

def RenameSequenceDirectories(sequences):
    # Rename directories based on location reverse geocoded from exif lat, long of first image in each sequence
    print("Renaming sequence directories")
    print("-------------------------------------------------------\n")
    geolocator = Nominatim(user_agent="GoPro_Transfer")

    for dirName, fileName in sequences:
        fullName=os.path.join(dirName,fileName)
        print(f"Renaming {dirName} based on {fileName} ...")
        try:
            locName=GetLocation(geolocator, fullName)
            os.rename(dirName, f"{dirName}_{locName}")
        except Exception as inst:
            print(f"ERROR: Unable to rename {dirName}, exception {type(inst)}")
        time.sleep(2)  # Delay so as to be a good citizen and not abuse nominatim

def GetLocation(geolocator, fullName):
    locName="UNKNOWN"
    lat,lon = exif_latlon.get_lat_lon(fullName)
    if lat is None:
        print(f"ERROR: No lat/lon for '{fullName}'")
    else:
        location = geolocator.reverse((lat, lon))

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
        elif 'county' in location.raw['address']:
            locName=location.raw['address']['county']
        elif 'state' in location.raw['address']:
            locName=location.raw['address']['state']
        elif 'name' in location.raw['address']:
            locName=location.raw['address']['name']
        else:
            print(f"ERROR: '{fullName}' No location from '{location.raw}'")

        locName=locName.replace(" ","_")
    return(locName)

def CreateDir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

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
    mtp_cleanup=lambda x: print(f"MTP: Not removing dir {x}")
else:
    mtp_transfer=shutil.move
    mtp_cleanup=os.rmdir

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

now = datetime.now().strftime("%Y-%m-%d") 
dest_dir=os.path.join(workDir,f"{now}_{camera}")
# FIXME: If dest_dir already exists create and use a new directory?

# TODO: Retry MTP directory checking, sometimes it takes a while to connect
if os.path.exists(gopro_mtp):
    print(f"{camera} connected via USB/MTP.")

    src_dir=f"{gopro_mtp}/GoPro MTP Client Disk Volume/DCIM"
    if os.path.exists(src_dir):

        dest_still_dir=os.path.join(dest_dir,f"Stills")
        dest_video_dir=os.path.join(dest_dir,f"Video")
        dest_seq_dir=""

        sequence_codes=[]

        geolocator = Nominatim(user_agent="GoPro_Transfer")
        print(f"Transfering files from beneath '{src_dir}' to '{dest_dir}'...")
        # TODO: Lots of efficency stuff:
        #       - Compile regexps
        #       - Keep track of directories created and don't continually check if they exist
        # Regexs observed:
        #    Type    Camera   Regex
        #    Still   Max      GS__.*\.JPG
        #    Seq     Max      GS.*\.JPG
        #    Video   Max      GS.*\.360
        #    Video   Max      GS.*\.THM
        #    Video   Max      GS.*\.LRV
        #    Still   Hero10   GOPR.*\.JPG
        #    Seq     Hero10   GO.*\.JPG
        #    Video   Hero10   GX.*\.MP4
        #    Video   Hero10   GX.*\.THM
        #    Video   Hero10   GX.*\.LRV
        for root, dirs, files in os.walk(src_dir, topdown=False):
            num_files=len(files)
            for file in tqdm(files):
                src_file=os.path.join(root,file)
                if re.match("GS__.*\.JPG",file) or re.match("GOPR.*\.JPG",file):
                    CreateDir(dest_still_dir)
                    tqdm.write(f"Still Image {file} -> {dest_still_dir}")
                    mtp_transfer(f"{src_file}", dest_still_dir)
                elif re.match("G..*\.JPG",file):
                    seq_code="Seq_"+file[:4]
                    if seq_code not in sequence_codes:
                        sequence_codes.append(seq_code)
                        location=GetLocation(geolocator, src_file)
                        dest_seq_dir=os.path.join(dest_dir,seq_code+"_"+location)
                        tqdm.write(f"Sequence '{seq_code}' at '{location}'")

                    CreateDir(dest_seq_dir)
                    mtp_transfer(f"{src_file}", dest_seq_dir)
                elif re.match(".*\.(MP4|360|LRV|THM)",file):
                    CreateDir(dest_video_dir)
                    if re.match(".*\.(MP4|360)",file):
                        tqdm.write(f"Video {file} -> {dest_video_dir}")
                    mtp_transfer(f"{src_file}", dest_video_dir)
            for directory in dirs:
                mtp_cleanup(os.path.join(root,directory))

        print(f"MTP Transfer done.")

    else:
        print(f"ERROR: Could not find GoPro MTP source directory'{src_dir}'")
        quit()


else:
    print(f"'{gopro_mtp} does not exist")
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

        # Create and change to destination directory
        if not os.path.exists(dest_dir):
            print(f"Creating directory '{dest_dir}'")
            os.makedirs(dest_dir)
        else:
            print(f"Using existing directory '{dest_dir}'")
        print(f"GoPro files will be transferred to {dest_dir}")
        print("-------------------------------------------------------\n")
        os.chdir(dest_dir)

        gopro_media = json.loads(gpCam.listMedia())

        for directory in gopro_media["media"]:
            src_dir  = directory["d"]
            for mediaFile in directory["fs"]:
                filename = mediaFile["n"];

                # If file has a 'b' (begin?) entry, it represents a sequence (timelapse or burst)
                if 'b' in mediaFile:
                    seq_code="Seq_"+filename[2:4]
                    print(f"DBG: filename {filename} code {seq_code}")
                    base=filename[:4]
                    rel_dir_name=seq_code

                    # Place each sequence in it's own directory
                    if not os.path.exists(rel_dir_name):
                        os.makedirs(rel_dir_name)
                    os.chdir(rel_dir_name)

                    start=int(mediaFile["b"])
                    end=int(mediaFile["l"])
                    print(f"---Download sequence of {end-start} images")
                    for i in range(start,end+1):
                        seq_image_filename=f"{base}{i:04d}.JPG"
                        if i==start:
                            sequences.append((rel_dir_name, seq_image_filename))
                        print(f"   ---Download sequence image {i-start}/{end-start} ",end=" ")
                        # FIXME: Stop downloadMedia from printing so a tqdm progress bar can be used instead
                        gpCam.downloadMedia(src_dir,seq_image_filename)
                        gpCam.deleteFile(src_dir, seq_image_filename)
                    os.chdir("..")
                else:
                    # Place non-timelapse files in their own directory
                    rel_dir_name=f"NonSeq"
                    if not os.path.exists(rel_dir_name):
                        os.makedirs(rel_dir_name)
                    os.chdir(rel_dir_name)
                    print(f"---Download non-timelapse file ",end=" ")
                    gpCam.downloadMedia(src_dir,filename)
                    gpCam.deleteFile(src_dir, filename)
                    os.chdir("..")

        print("Turning off GoPro...")
        print("-------------------------------------------------------\n")
        gpCam.power_off()

    # FIXME: ssid as reported by iwgetid is not always the same as name/id used by nmcli (sometimes it has "Auto" pre-pended)
    if ssid != gopro_wifi:
        print(f"Re-connecting to previous WiFi network '{ssid}'...")
        print("-------------------------------------------------------\n")
        subprocess.run(["nmcli","c","up", "id", ssid])

    # FIXME: Wait for network reconnection instead of just waiting
    time.sleep(10)  # Delay to ensure network reconnection is complete

    print("Renaming directories...")
    print("-------------------------------------------------------\n")
    RenameSequenceDirectories(sequences)

print("-------------------------------------------------------\n")
print(f"Opening file explorer on '{dest_dir}'")
# FIXME: ISO nemo open gnome-terminal or start upload directly?
subprocess.Popen(["nemo",dest_dir], start_new_session=True)
