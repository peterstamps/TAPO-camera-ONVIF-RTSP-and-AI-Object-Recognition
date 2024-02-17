TAPO C225 and otherTAPO ONVIF camera's
- Access to motion event messages via ONVIF, 
- RTSP based Live stream access and video stream recording triggered by motion events send by Tapo camera via ONVIF
- AI object recognition and interval based creation of snapshot picture with marked detected object(s) with label
- AI object recognition can be switched off in the configuration in case you do not have an AI server installed
- Lots of easy configuration !
- Easy to use: run simple python3 myTapoDetectCaptureVideo.py
- To check/test the motion event messages you can separately run python3 myTapoMotionDetection.py
- Have fun and maybe you can improve it
- You may want to play with the configuration settings to finetune in order to get the optimal result for your hardware

IMPORTANT - THESE ARE REAL WORKABLE EXAMPLE PROGRAM. Not meant as a project for endless development by me!
This has been tested and works with Tapo Camera C225. It was all tested on a Raspbery Pi 4 with 4MB RAM!
Room temp 20-21 Celsius, Raspberry Pi 4 sits in a LIRC Aluminium Case, no FAN, Operation Temp was average 42-45 Celcius

Before running  'python3 myTapoDetectCaptureVideo.py' OR 'python3 myTapoVideoCapture.py' read following steps!!

1) CHECK and ADAPT the parameters in myTapoMotionConfig.py  (paths!, user and password and IP address)

2) Run pip install for missing Python packages! 
   When not installed then you need to install the listed packages in file Readme_install_these_python_packages.txt
   Use 'pip install' for following packages. 
   For your information only: python 3.11 was used in a virtual environment. 
   This python version might not be required. It probably will work with other python3 versions as well.
 
3) Create a wsdl directory and put the required WSDL files in it. This is how you can do it.
   - Download the python-onvif-zeep-async SOURCE distribution package at:  https://pypi.org/project/onvif-zeep-async/#files
     (a direct download is at https://files.pythonhosted.org/packages/68/65/c39f751794b4cd60238b4202fc27d35c81fdc8ea226cc9bead2b983c7818/onvif-zeep-async-3.1.12.tar.gz)
   - Unzip the onvif-zeep-async-3.1.12.tar.gz to a temporary location (for example in your Downloads folder)
   - Look in the new folder 'onvif-zeep-async-3.1.12' for folder 'onvif' and inside onvif you find a folder called 'wsdl'.
   - Copy the wsdl to the desired location and adapt parameter 'cfg.cameraOnvif_wsdl_dir' in myTapoMotionConfig.py

4) Optional: You might want to change the locale in myTapoDetectCaptureVideo or myTapoVideoCapture
import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style  like 1.000.000,95
--------



