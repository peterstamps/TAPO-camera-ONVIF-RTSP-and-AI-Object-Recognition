TAPO C225 and other TAPO ONVIF camera's
- Access to motion event messages via ONVIF, 
- RTSP based Live stream access and video stream recording triggered by motion events send by Tapo camera via ONVIF
- AI object recognition and interval based creation of snapshot picture with marked detected object(s) with label
- AI object recognition can be switched off in the configuration in case you do not have an AI server installed
- Lots of easy configuration !
- Automatic sensitivity adaption to detect objects. This will be adapted automatically during dusk and dawn time between day/night sensitivity threshold settings 
- Easy to use: run simply one of the various versions stored in this github directory.
    python3 myMPTapoDetectCaptureVideo.py  << This multiprocessing version is the best therefore the preferrred version 
    OR  use the non multiprocessing version: 
    python3 myTapoDetectCaptureVideo.py
    OR use my first version: 
    python3 myTapoVideoCapture.py'
- To check/test the motion event messages you can separately run python3 myTapoMotionDetection.py
- Have fun and maybe you can improve it
- You may want to play with the configuration settings to finetune in order to get the optimal result for your hardware

IMPORTANT - THESE ARE REAL WORKABLE EXAMPLE PROGRAMS. This is not meant to be a project for endless development by me!
The myTapoDetectCaptureVideo.py version of the program has been tested and works with Tapo Camera C225. It was all tested on a Raspbery Pi 4 with 4MB RAM!
Room temp 20-21 Celsius, Raspberry Pi 4 sits in a LIRC Aluminium Case, no FAN, Operation Temp was average 42-45 Celcius

Before running  'python3 myMPTapoDetectCaptureVideo.py' (PREFERRED!) or the other versions read following steps!!

1) CHECK and ADAPT the parameters in myMPTapoMotionConfig.py  OR myTapoMotionConfig.py  

  Set the camera details like user and password and IP address paths, location etc. to your OWN VALUES!
  Read the comments in the config file!

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

4) Optional: You might want to change the locale in myMPTapoDetectCaptureVideo and/or myTapoDetectCaptureVideo or myTapoVideoCapture
import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style  like 1.000.000,95
--------

NEW:  myIPcamrecorder.py

myIPcamrecorder.py is a NEW STANDALONE program to capture streams from your IP camera, detect motion, record the video, display the motion on the screen and detect objects in the recorded video like person, dog, cat, car). Can be customized. Set inside the program for the settings. Simply run python3 myIPcamrecorder.py after you have set your own parameter values. It does NOT use motion events from the camera. The functionality is however similar to the examples above.
The code is however much more simple than the other examples.  The basis was created with ChatGTP, however ChatGTP did not create a flawless example... on the contrary. But it helped me more than expected.


Note that i have added some variants in one of my repositories.

The latest apps are doing the following once configured via a simple  .ini file and started in a terminal(console) on raspberry pi (or other linux e.g. Ubuntu)

1. Login into the configured Tapo camera (any ONVIF-S compatible camera will do)
 
 
2. Read the video stream.
 
 
3. Detect if a motion happened.
 
 
4. Record the motion and store the video at a configurable location on a disk.
 
 
4. Optional, when configured in your .ini file: Make and analyse every Xth second (is configurable) a frame, a snapshot of the video stream using an AI object recognition service running local on Rasberry Pi, like i have. You can also use a remote AI service, as it is just an URL you need to specify.
 
 
5. When one of the configured objects is recognized a jpeg picture will be saved at a configurable location on the disk.
 
 
6. Optional: the saved picture(s) can be mailed to you or the one you specify as a receiver. You just need to define an email account similar like you have on your phone mail. The mail function is completely included and simple configurable in the .ini file.
 
 
7. You can optionally exclude certain areas of the camera view using a mas. The instructions how to create a mask file is in the readme.txt. So only areas that you want will be used for motion detection. 
  
  
The latest App versions will use the motion areas defined on the camera and use a motion trigger message from the Tapo camera itself. That takes heavier load away from your Raspberry Pi. Other versions use a motion detection on the Raspberry Pi itself. Some camera's where no subscription to event messages is possible can use those  App versions. Read the Readme.txt file in each repository.
 
 
8. You can optionally view the resized video stream, the resized stream with the mask, a resized motion view and a full pixel view of the stream (large). An option is available (configurable) to view the motions and objects live in the video. The motion spots are marked and labelled live in the video and on the saved picture if you want that.
 
 
9. You can decide which objects you would recognise like a car, person cat, dog, bus, truck and many more when your AI object recognition service supports them.
 
 
10. Each video and picture is uniquely timestamped and in the picture file also the label is used. So jpeg pictures of persons are easy to find. The timestamp points you then quickly to the right video. Very simple.
 
 
11. You define subject and body text of the email. The picture can be optional embedded in the mail.
 
 
12. When you do not have/ want AI or mail, set in the .ini file a value to No and these functions will not be used.
 
 
13. The .ini file has clear explanations and default values.
 
 
14. You can record 4K video (2560x1440 pixels =stream1 of Tapo) with the C++ based apps on a Rasberry PI 4 with 4GB RAM 64bits,  and a disk attached or good USB 3.0 storage stick of about 128 or more GB.
 
 
15. The Python versions work better with the 720p HD format (1280x720 pixels =stream2 of Tapo) on a Raspberry Pi 4, although I got reasonable results with 4K. But only if you reduce all other loads, switch of WiFi, Bluetooth, Samba, etc.. 
 
 
16. My advice: Use stream2 with Python versions of the App.
 
 
17. My advice: Use stream1 with the C++versions of the App.
 
 
As I started with Python and later on detected that C++ was probably faster and better for 4K video I used the Python expertise to build further with C++. That is why one of the  latest C++ versions has a little more functionality like Mail included.
 
 
As I could not find an easy to use ONVIF library in C++, I decided to embed a Python runtime in the C++ App. An included Python program polls every Xth second the Tapo camera for ONVIF event (motion) messages. once motion is detected, recording starts.
 
 
I have to admit that this was a very, very complex exercise to get it all working. I am not a C++ programmer at all. 
 
 
Plenty of research and examples, trial and errors were needed to get it working.
 
 
Now I am done.... although never say never...
