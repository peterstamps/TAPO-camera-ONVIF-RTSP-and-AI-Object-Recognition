# SEE DESCRIPTION IN myTapoVideoCapture as well
#
# Import the package 'easydict'. This package proved quite handy for managing the global configurable parameters.
from easydict import EasyDict as edict
cfg = edict()


# used to set camera and video-related parameters
cfg.videoProtocol         = 'rtsp'
cfg.cameraUser            = '<username>'
cfg.cameraPassw           = '<password>'
cfg.cameraIP              = '<192.168.100.1>'
cfg.cameraPort            = '554'
cfg.cameraStream          = 'stream2'
cfg.cameraStream1WxH       = (2560,1440) 
cfg.cameraStream2WxH       = (1280,720) 
cfg.cameraOnvifPort       = '2020'
cfg.cameraOnvif_wsdl_dir  = "</path_to_wsdl_directory>/wsdl" # copy them from python-onvif-zeep-async package to your location
cfg.cameraPrintMessages   = False   # print the XML and HTTP requests (suppress HTTPS request messages with command: python3 montionmain2.py > 2> /dev/null )
cfg.cameraLogMessages     = 'CRITICAL' # debug, info or critical

# memoryFull_percentage prevents that setting cfg.videoRecSecondsBeforeMotion and cfg.cameraStream are
# causing a running out of memory
# Setting it too high means that other apps may not be able to start and/or number of prerecording dropping is high
cfg.memoryFull_percentage = 70.0 # do not accidently add a percentage sign behind the floating number!

#  do not touch next parameter cfg.videoUrl 
cfg.videoUrl         = f'{cfg.videoProtocol}://{cfg.cameraUser}:{cfg.cameraPassw}@{cfg.cameraIP}:{cfg.cameraPort}/{cfg.cameraStream}'
cfg.videoFps         = 15    # the frame speed of the RTSP Stream! Maximum 15; For Tapo streams 1 and 2 the RTSP stream has max 15 FPS
# put below the real FrameSpeed that you have set in your Tapo camera settings
cfg.TapoFrameSpeed   = 15  # real FrameSpeed of tapo Camera

# Video encoder options are
# 'RAW ' # Format: RGB,  Codec ID: 0x00000000, Codec ID/Info: 
#        # Basic Windows bitmap format. 1, 4 and 8 bpp versions are palettised. 16, 24 and 32bpp contain raw RGB samples
#        # RAW create huge files (experienced ~ 30 times larger than other encoders)
#        # In fact each frame is a Bitmap written in a file. Not viewable via VLC, mpv or SMPlayer on Raspberry pi 4
# 'FFVH' # Format: HuffYUV, Codec ID: FFVH. Creates very huge video files! (experienced ~ 16-17 times larger than mpv4!)
# 'MJPG' # compression format
# 'XVID' # Format: MPEG-4 Visual, Codec ID: XVID / XviD
# 'RGBA' # original create large format
# 'X264' # very compact compression format. max resolution 1920 x 1080
# 'H264' # compact compression format. max resolution 1920 x 1080
# 'MPEG' # Format: MPEG Video, Codec ID: MPEG / Chromatic MPEG 1 Video I Frame. This is somewhat smaller than mpv4
# 'mp4v' # Format: mp4v, Codec ID: mp4v 
# 'avc1' # Format: Advanced Video Codec, Codec ID: avc1  Creates very compact video files! max resolution 1920 x 1080
#
# Recording the Tapo C225 stream1 with a resolution of 2560x1440 pixels works with encoders: MJPG, XVID, RGBA, mp4v 
# Some other encoders such as x264, H264 can handle a maximum recording resolution of 1920x1080. 
# In order to use those encoders like avc1, h264, x264 the recording output stream will be resized /downsized with factor 0.75!!
# Note: Recording of Tapo C225 stream2 (1280x720 pixels) is below the maximum recording resolution. No resizing needed. 
#
# cfg.videoEncoder Must always be 4 characters, so also spaces when needed! 
cfg.videoEncoder     = 'H264'  # 
cfg.videoRecordingResolutionFactor = 1.0 # resize frames size before writing them, some videoEncoder have a max allowed frame resolution: 1920x1080
cfg.videoDuration    = 0.15 # In minutes. Max. recording duration e.g. 0.4 => 20s, 0.3 => 18s, 0.2 => 12s, 0.15 => 9s
cfg.videoRecSecondsBeforeMotion = 3 # In seconds. recommended: 5 -> max 10 seconds for Tapo stream2 (1280x720), 2 -> max 3 seconds for Tapo stream1 (2560x1440),
# Next parameter. Seconds setting should be higher then the Camera detection response time (~ 2 seconds) 
# Add extra recording time in seconds (see cfg.videoDuration)  when when new motion(s) are dected just 
# before the maximum recording time has been reached. 
# Note the: To avoid huge files the absolute maximum recording time per file is hard coded to 2.5 minutes
cfg.videoMotionDetectedJustBeforeEndofRecordDuration = 2.1 # In seconds. 
cfg.videoMotionDetectedExtraTimeJustBeforeEndofRecordDuration = 1.2 # in seconds. The time extra added ro RecordDuration
cfg.videoRecsFiles = "avi" # Format to write the video frames. Only use '.avi', it's just a container, the codec is the important thing.

# used to set motion sensitivity parameters
cfg.motionSenseThreshold = 5 # for night cameras with low light, reduce this parameter below 10, This is the threshold pixel value for motion perception. 
cfg.motionSenseArea  = 900 # default = 900, The min Area threshold for detection

# used to simulate a motion detected by the Camera, usefull for testing recording and AI object recognition
cfg.RunMotionSimulation_1 = False  # will trigger MotionDetected to True happens between read of frames 150 and 450
cfg.RunMotionSimulation_2 = False  # will trigger MotionDetected to True happens between read of frames 1050 and 1250

# used to set motion storage location parameters
cfg.storageDirectory        = r"</path_to_AI_pictures_and_videos>/" # end slash required
cfg.basenameOjectRecsFiles  = "camera_capture"
cfg.extensionOjectRecsFiles ="jpg"

# used to set AI server related parameters
cfg.AIserverInstalled = False # set to False when no AI server is available
cfg.AIserverUrl    = "http://localhost:32168/v1/vision/detection"  # URL of your AI server
cfg.AIpictureResolutionFactor = 0.5 # down-scales frames for AI purposes, for stream 1 recommended 0.3 to max 1.0
cfg.objectDetectionInterval = 1.5 ## every x seconds when recording is on USE SMAL MODEL IN CODEPROEJCT AI
cfg.font_scale_Label = 0.4 # the font size in the label of the detected object. Font is  cv2.FONT_HERSHEY_SIMPLEX 
cfg.colorObjectRectangle = (230, 159, 22) # BGR notation (blue , green, red) ; Code for shade of waterblue => (230, 159, 22) ; code light green => (0, 255, 124)                        
cfg.colorLabelRectangle = (230, 159, 22)
cfg.colorLabelText = (0,0,0)
cfg.ObjectsToDetect = ("person", "car", "dog", "cat")  # Must be in a tuple format! Like ("person", "car", "dog", "cat") => Check the AI server models which object are supported
#
# used to set AI server related confidence parameters. Confidence will changes during morning and evening (due to night/day effects)
cfg.min_confidence_day = 0.4 ## Day min_confidence (Float): The minimum confidence level for an object will be detected. In the range 0.0 to 1.0. Default 0.4.
cfg.min_confidence_night = 0.1 ## Night min_confidence (Float): The minimum confidence level for an object will be detected. In the range 0.0 to 1.0. Default 0.1.
cfg.mycity = "Amsterdam"             #  Put here your city where the Camera is located!  The (sensitivity) Confidence parameter will gradually adapt during dawn and dusk between day/night values set above
cfg.mycountry = "Netherlands"        #  Put here your country where the Camera is located
cfg.mytimezone = "Europe/Amsterdam"  #  ADAPT this to your the time zone where the Camera is located
cfg.mytown_latitude = 52.37311       #  The given latitude and longitude are of Royal Palace at Amsterdam DAM Square
cfg.mytown_longitude = 4.89228       #  Adapt these to you camera location!
