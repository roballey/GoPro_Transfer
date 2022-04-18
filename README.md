# GoPro_Transfer
Transfer files from a GoPro to a PC via WiFi.

First connects to the GoPro via BlueTooth to turn on Wifi, then connects to the GoPro via Wifi and moves all time lapse photos from the GoPro to the PC file system.
Files are placed beneath a directory named after the camera and the current date.  Within this directory each sequence goes into a subdirectory named with the sequence number and the location (based on the coordinates of the first image in the sequence).
After transfering (moving) all images switches back to the original WiFi network.

## Limitations
- Tested with Hero 5 Black and Max 360.  
- Only transfers time lapse and burst photos.

## Notes
Was not working using higher level `goprocam` library functions to download sequences, hence the hand rolled nature of the download.

Camera must have been previously paied to the PC via Bluetooth.
PC must have been previously connected to the GoPro's WiFi network and the password saved.

## Dependencies
Uses [gopro-ble-py](https://github.com/roballey?tab=stars#:~:text=KonradIT%20/%20gopro%2Dble%2Dpy) and [gopro-py-api](https://github.com/KonradIT/gopro-py-api) (`goprocam`) for connection to the GoPro.
Uses `pillow` to read exif information from images.
Uses `geopy` to perform reverse geocoding (using nominatem),
