# SEE DESCRIPTION IN myTapoVideoCapture as well
#
# Import the package 'easydict'. This package proved quite handy for managing the global configurable parameters.
from easydict import EasyDict as edict
cfg = edict()


# used to set camera and video-related parameters
cfg.videoProtocol         = 'rtsp'
cfg.cameraUser            = 'user'
cfg.cameraPassw           = 'password'
cfg.cameraIP              = '192.168.100.1'
cfg.cameraPort            = '554'
cfg.cameraStream          = 'stream2'
cfg.cameraOnvifPort       = '2020'
cfg.cameraOnvif_wsdl_dir  = "/home/user/Documents/onvif/wsdl"  # copy them from python-onvif-zeep-async package to your location
cfg.cameraPrintMessages   = False   # print the XML and HTTP requests (suppress HTTPS request messages with command: python3 montionmain2.py > 2> /dev/null )
cfg.cameraLogMessages     = 'CRITICAL' # debug, info or critical

cfg.memoryFull_percentage = 70.0 # Too high means that other apps may not be able to start and/or prerecording time reduces

#  do not touch next parameter cfg.videoUrl 
cfg.videoUrl         = f'{cfg.videoProtocol}://{cfg.cameraUser}:{cfg.cameraPassw}@{cfg.cameraIP}:{cfg.cameraPort}/{cfg.cameraStream}'
cfg.videoFps         = 15    # maximum: 15; For Tapo streams 1 and 2 the RTSP stream has max 15 FPS
# Video encoder options are
# 'MJPG' # compression format
# 'XVID' # compression format
# 'RGBA' # original create large format
# 'X264' # very compact compression format
# 'MPEG' # larger compression format
# 'mp4v' # not lower case !  compression format

cfg.videoEncoder     = 'X264'  # stream1 works with MJPG and mp4v)! encoder options are 'MJPG' 'XVID' 'WVM2'
cfg.videoScale       = 0.4 # down-scales video frames size, recommended 0.5 to max 0.8 (Use 0.8 to 1.0 larger only when Yolo5 model is set to medium or large)
cfg.videoShow        = True  # to show/hide output video
cfg.videoDuration    = 0.15 # video save file duration in minutes e.g. 0.4 => 20s, 0.3 => 18s, 0.2 => 12s, 0.15 => 9s
cfg.videoRecSecondsBeforeMotion = 5 # recommended: 5 -> max 10) seconds for Tapo stream2 (1280x720), 2 -> max 3) seconds for Tapo stream1 (2560x1440),
cfg.videoRecsFiles = "avi" # format to write the video frames

# used to set motion sensitivity parameters
cfg.motionSenseThreshold = 5 # for night cameras with low light, reduce this parameter below 10, This is the threshold pixel value for motion perception. 
cfg.motionSenseArea  = 900 # default = 900, The min Area threshold for detection

# used to simulate a motion detected by the Camera, usefull for testing recording and AI object recognition
cfg.RunMotionSimulation_1 = False  # will trigger MotionDetected to True happens between read of frames 150 and 450
cfg.RunMotionSimulation_2 = False  # will trigger MotionDetected to True happens between read of frames 1050 and 1250

# used to set motion storage location parameters
cfg.storageDirectory        = r"/home/user/Pictures/Tapo/"
cfg.basenameOjectRecsFiles  = "camera_capture"
cfg.extensionOjectRecsFiles ="jpg"

# used to set AI server related parameters
cfg.AIserverUrl    = "http://localhost:32168/v1/vision/detection"  # AICodeProject was used, Deepstack and others will also work adapt the URL
cfg.min_confidence = 0.5 ## min_confidence (Float): The minimum confidence level for an object will be detected. In the range 0.0 to 1.0. Default 0.4.
cfg.objectDetectionInterval = 2.0 ## every two seconds when recording is on 
cfg.font_scale_Label = 0.4 # the font size in the label of the detected object. Font is  cv2.FONT_HERSHEY_SIMPLEX 
cfg.colorObjectRectangle = (230, 159, 22) # BGR notation (blue , green, red) ; Code for shade of waterblue => (230, 159, 22) ; code light green => (0, 255, 124)                        
cfg.colorLabelRectangle = (230, 159, 22)
cfg.colorLabelText = (0,0,0)
cfg.ObjectsToDetect = ("person", "car", "dog", "cat")  # Must be in a tuple format! Like ("person", "car", "dog", "cat") => Check the AI server models which object are supported
