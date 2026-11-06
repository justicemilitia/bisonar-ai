# Creality Ender-3 V3 KE + generic USB webcam

Use an ordinary UVC webcam (tested: Logitech C310, `046d:081b`) with the printer's own camera service instead of Creality's Nebula Camera. Tested on Creality OS V1.1.0.15.

Out of the box the printer ignores non-Creality webcams:

- `cam_app` exits because `/tmp/.cam_version` is missing. `auto_uvc.sh` writes that file only when `cam_util` can read firmware info from a Creality (Sonix) camera.
- Many webcams send MJPEG frames without a Huffman table (DHT). Chrome shows them, but WebKit (Safari, OrcaSlicer's Device tab on macOS) does not.

## Files

| File | What it does |
|---|---|
| [code/auto_uvc.sh](code/auto_uvc.sh) | Patched `/usr/bin/auto_uvc.sh`. Writes a fallback `/tmp/.cam_version` for cameras without Creality firmware info (updates disabled), and uses 1280x720 when the camera has no 1920x1080 MJPG mode. Changes are marked `PATCH`. |
| [code/kamera.html](code/kamera.html) | Viewer page. Polls `?action=snapshot`, inserts the standard JPEG Huffman table when it is missing, shows the frame. Works in Safari and OrcaSlicer. |

## Install

Needs root on the printer (Settings > Root account information). Root may affect your warranty.

    scp -O code/auto_uvc.sh root@<printer-ip>:/tmp/auto_uvc.sh
    ssh root@<printer-ip> "sh -n /tmp/auto_uvc.sh && cp /tmp/auto_uvc.sh /usr/bin/auto_uvc.sh && chmod +x /usr/bin/auto_uvc.sh"
    scp -O code/kamera.html root@<printer-ip>:/usr/share/mjpg-streamer/www/kamera.html

Restart the printer, then open:

- Chrome: `http://<printer-ip>:8080/?action=stream`
- Safari / OrcaSlicer: `http://<printer-ip>:8080/kamera.html`

In OrcaSlicer: connection type `CrealityPrint`, host `http://<printer-ip>`, Device UI `http://<printer-ip>:8080/kamera.html`.

## Undo

    ssh root@<printer-ip> "cp /rom/usr/bin/auto_uvc.sh /usr/bin/auto_uvc.sh"

A firmware update may remove both files; copy them again. Don't accept a camera firmware update offered by the printer.

## Limits

Creality Print doesn't show the webcam, and Creality Cloud connects but stays grey (its H.264 path most likely can't decode the DHT-less frames).

`auto_uvc.sh` is based on Creality's original script from the printer firmware.

## Camera mount

I printed [Ender 3 V3 SE / KE Logitech Webcam Camera Mount (C270 or similar)](https://www.printables.com/model/1161793-ender-3-v3-se-ke-logitech-webcam-camera-mount-c270) by FeetOffTheTable. The C310 fits it. PLA, no supports, 46 minutes. It slides onto the right end of the X gantry, so the camera moves up with Z.
