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

# memoryFull_percentage prevents that setting cfg.videoRecSecondsBeforeMotion and cfg.cameraStream are
# causing a running out of memory
# Setting it too high means that other apps may not be able to start and/or number of prerecording dropping is high
cfg.memoryFull_percentage = 70.0 # do not accidently add a percentage sign behind the floating number!

#  do not touch next parameter cfg.videoUrl 
cfg.videoUrl         = f'{cfg.videoProtocol}://{cfg.cameraUser}:{cfg.cameraPassw}@{cfg.cameraIP}:{cfg.cameraPort}/{cfg.cameraStream}'
cfg.videoFps         = 15    # maximum: 15; For Tapo streams 1 and 2 the RTSP stream has max 15 FPS

#  Be careful with specifying frame sizes. In the constructor you need to pass the frame size as (column, row) 
#  e.g. 640x480. However the array you pass in, is indexed as (row, column).
#  If your input image has a different size to the VideoWriter, it will fail (often silently)
#  Only pass in 8 bit images, manually cast your arrays if you have to (.astype('uint8'))
#  In fact, never mind, just always cast. Even if you load in images using cv2.imread, you need to cast to uint8...
#  MJPG will fail if you don't pass in a 3 channel, 8-bit image. I get an assertion failure for this at least.
#  XVID also requires a 3 channel image but fails silently if you don't do this.
#  H264 seems to be fine with a single channel image
#  If you need raw output, say from a machine vision camera, you can use 'DIB '. 
#  'RAW ' or an empty codec sometimes works. Oddly if I use DIB, I get an ffmpeg error, but the video is saved fine.
#  If I use RAW, there isn't an error, but Windows Video player won't open it. 

# Video encoder options are
# 'RAW ' # Format: RGB  Codec ID: 0x00000000, Codec ID/Info: 
#        # Basic Windows bitmap format. 1, 4 and 8 bpp versions are palettised. 16, 24 and 32bpp contain raw RGB samples
#        # RAW create huge files (experienced ~ 30 times larger than other encoders)
#        # In fact each frame is a Bitmap written in a file. Not viewable via VLC, mpv or SMPlayer on Raspberry pi 4
# 'MJPG' # compression format
# 'XVID' # Format: MPEG-4 Visual, Codec ID: XVID / XviD
# 'RGBA' # original create large format
# 'X264' # very compact compression format
# 'H264' # compact compression format
# 'MPEG' # Format: MPEG Video, Codec ID: MPEG / Chromatic MPEG 1 Video I Frame. This is a somewhat larger compression format
# 'mp4v' # Format: mp4v, Codec ID: mp4v 
# 'avc1' # Format: Advanced Video Codec, Codec ID: avc1  Creates very compact video files!

# cfg.videoEncoder Must always be 4 characters! 
# Tapo C225 stream1 (2560x1440 pixels) works with XVID, MJPG and mp4v
# Tapo C225 stream2 (1280x720  pixels) works with avc1 X264, H264, MJPG and mp4v also RAW but see above

cfg.videoEncoder     = 'mp4v'  
cfg.videoScale       = 0.4 # down-scales video frames size, recommended 0.5 to max 0.8 (Use 0.8 to 1.0 larger only when Yolo5 model is set to medium or large)
cfg.videoShow        = True  # to show/hide output video
cfg.videoDuration    = 0.2 # video save file duration in minutes e.g. 0.4 => 20s, 0.3 => 18s, 0.2 => 12s, 0.15 => 9s
cfg.videoRecSecondsBeforeMotion = 5 # recommended: 5 -> max 10) seconds for Tapo stream2 (1280x720), 2 -> max 3) seconds for Tapo stream1 (2560x1440),
cfg.videoRecsFiles = "avi" # format to write the video frames. Only use '.avi', it's just a container, the codec is the important thing.

# used to set motion sensitivity parameters
cfg.motionSenseThreshold = 5 # for night cameras with low light, reduce this parameter below 10, This is the threshold pixel value for motion perception. 
cfg.motionSenseArea  = 900 # default = 900, The min Area threshold for detection

# used to simulate a motion detected by the Camera, usefull for testing recording and AI object recognition
cfg.RunMotionSimulation_1 = True  # will trigger MotionDetected to True happens between read of frames 150 and 450
cfg.RunMotionSimulation_2 = False  # will trigger MotionDetected to True happens between read of frames 1050 and 1250

# used to set motion storage location parameters
cfg.storageDirectory        = r"/home/peter/Pictures/Tapo/"
cfg.basenameOjectRecsFiles  = "camera_capture"
cfg.extensionOjectRecsFiles ="jpg"

# used to set AI server related parameters
cfg.AIserverInstalled = False # set to False when no AI server is available
cfg.AIserverUrl    = "http://localhost:32168/v1/vision/detection"
cfg.min_confidence = 0.4 ## min_confidence (Float): The minimum confidence level for an object will be detected. In the range 0.0 to 1.0. Default 0.4.
cfg.objectDetectionInterval = 2.0 ## every two seconds when recording is on 
cfg.font_scale_Label = 0.4 # the font size in the label of the detected object. Font is  cv2.FONT_HERSHEY_SIMPLEX 
cfg.colorObjectRectangle = (230, 159, 22) # BGR notation (blue , green, red) ; Code for shade of waterblue => (230, 159, 22) ; code light green => (0, 255, 124)                        
cfg.colorLabelRectangle = (230, 159, 22)
cfg.colorLabelText = (0,0,0)
cfg.ObjectsToDetect = ("person") #, "car", "dog", "cat")  # Must be in a tuple format! Like ("person", "car", "dog", "cat") => Check the AI server models which object are supported
