IMPORTANT - 
This has been tested and works with Tapo Camera C225. It was all tested on a Raspbery Pi 4 with 4MB RAM!
Room temp 20-21 Celsius, Raspberry Pi 4 sits in a LIRC Aluminium Case, no FAN, Operation Temp was average 42-45 Celcius for myTapoDetectCaptureVideo.py
The multiprocessing version operating temperature is some 3 to 5 degrees higher!

Before running myTapoVideoCapture  with 'python3 myTapoVideoCapture.py' see following steps

1) CHECK and ADAPT the parameters in myTapoMotionConfig.py  (paths!, user and password and IP address)

2) Run pip install for missing Python packages!
When not installed then you need to install the following packages 

3) You might want to change the locale in myTapoVideoCapture
import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style  like 1.000.000,95
--------

Use 'pip install' for following packages. 
The version number listed were installed
For your information python 3.11 was used in a virtual environment. 
This might not be required. It probably will work with other python3 versions as well

python-onvif-zeep-async  (onvif_zeep_async-3.1.12 was used)
python-onvif-zeep        (onvif_zeep-0.2.12 was used)
onvif         (might come with the packages above)
easydict     (easydict-1.11 was used)
asyncio
logging
pytz         (pytz-2023.3.post1)
zeep         (zeep-4.2.1 was used)
typing
httpx        (httpx-0.26.0 was used)
threading 
opencv-python  (opencv_python-4.9.0.80  was used;  cv2  / opencv2)
io
urllib3
json
numpy  (numpy-1.26.1 was used)
psutil
collections (might be standard installed in python 3.11
multiprocessing


Tip: See the imports in the programs to see what else migth be needed. 

IMPORTANT: There is an error in onvif-zeep-async-3.1.12. You need to manually comment some part of the code to get it working.!!
This is how:

download src package from pypi.org
unzip and adapt managers.py
zip and run pip install /storage/emulated/0/Download/onvif-zeep-async-3.1.12.zip

https://github.com/home-assistant/core/blob/dev/homeassistant/components/onvif/event.py#L65
program python-onvif-zeep-async/onvif/managers.py must have a adaption in try and except part

COMMENT OR DELETE THIS CODE BLOCK in python-onvif-zeep-async/onvif/managers.py!!

async def (self) -> None:
"""Renew or start notify subscription."""
if self._shutdown:
return
renewal_call_at = None
try:
renewal_call_at = (
await self._renew_subscription()
)
except:
renewal_call_at = (
await self._restart_subscription()
)
finally:
self._schedule_subscription_renew(
renewal_call_at
or self._loop.time()
+ SUBSCRIPTION_RESTART_INTERVAL_ON_ERROR.total_seconds()
)

