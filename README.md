# GoPro_Transfer
Transfer files from a GoPro to a PC via MTP or Bluetooth/WiFi.

First tests if camera is mounted via MTP, if it is, moves files.

If MTP directory doesnt exist, connects to the GoPro via BlueTooth to turn on Wifi, then connects to the GoPro via Wifi and moves all files from the GoPro to the PC file system.
Files are placed beneath a directory named after the camera and the current date.  Within this directory each sequence goes into a subdirectory named with the sequence number and the location (based on the coordinates of the first image in the sequence).
After transfering (moving) all images switches back to the original WiFi network.

## Configuration File

Requires a configuration file named `.goprotransfer.json` in `~/.config`
Configuration file specifies:
  - "work_dir" Where GoPro files will be moved beneath
  - "cameras" Array of camera entries consisting of:
    - "camera" Name by which camera is referred and passed to script as arg1
    - "bt" Bluetooth MAC address of camera
    - "wifi" WiFi network name of camera
    - "mtp" MTP mount point of camera

## Limitations
- Tested with Hero 10 Black, Hero 5 Black and Max 360, may or may not work with other models
- Fails with Hero 5 Black containing ~10000 time lapse photos
- Only tries the MTP mount point once and may switch to trying BT/Wifi even though connected via WiFi

## Notes
Must be run in a virtual environment, create with:
  `python3 -m venv Venv`
Was not working using higher level `goprocam` library functions to download sequences, hence the hand rolled nature of the download.

Camera must have been previously paired to the PC via Bluetooth.  (On GOPro Max select Preferences->Connections->Connect Device->GoPro App then open Bluetooth settings in Linux Mint and check for new GoPro device and setup. Then copy BT mac address from device info into cameras.json file)
PC must have been previously connected to the GoPro's WiFi network and the password saved.

## Dependencies
Uses [gopro-ble-py](https://github.com/roballey?tab=stars#:~:text=KonradIT%20/%20gopro%2Dble%2Dpy) and [gopro-py-api](https://github.com/KonradIT/gopro-py-api) (`goprocam`) for connection to the GoPro.
Uses `pillow` to read exif information from images.
Uses `geopy` to perform reverse geocoding (using nominatem),
