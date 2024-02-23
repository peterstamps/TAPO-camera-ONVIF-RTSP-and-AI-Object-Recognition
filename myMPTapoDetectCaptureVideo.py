# DESCRIPTION
# myTapoDetectCaptureVideo - This is a combination of myTapoMotionDetection.py and myTapoVideoCapture.py
#   This program checks your camera motion messages
#   It uses the ONVIF standard to pull motion messages from the Tapo Camera (tested on C225 model)
#   It also reads the camera RTSP stream and records it when motion is detected
#   Then it will (when configured) also call the AI object Server to create a (compact) jpg picture with 
#   the recognised object(s) marked with a rectangle and label
# myTapoMotionConfig.py - This contains the parameters to configure the proces, 
#   Be carefull to change the configuration as it is (simple) Python program code!#

#
# Reading frames is a continously process. Frames are saved in a deque as prerecorded frames.
# When a motion has been detected the recording starts and frames will be written one by one from the deque
# Each written frame will be deleted from the deque (first in first out), 
# meanwhile new frames will be added to the deque till the recorded seconds before motion is reached
# or the max memoryFull_percentage is reached. 
# In such cases the first frame will be dropped from the deque, and a new added. 
# This will avoid to run out of memory!!
# IMPORTANT: when you open too much other apps while running this 
# your memoryFull_percentage might be reached much quicker influencing a proper recording
# In about each 2 seconds a ONVIF message is returned to indicate a motion has happened or not 
# The speed of the recording is somewhat higher in the beginning till object is detected.

from myMPTapoMotionConfig import cfg
from myMPTapoMotion_dawn_dusk import *
import asyncio
import logging
from time import sleep 
import datetime as dt
from datetime import datetime, timedelta
from pytz import UTC
from zeep import xsd
from typing import Any, Callable
from onvif import ONVIFCamera
from threading import Thread
from time import sleep, time
import cv2
import os
import sys
import io
import urllib3
import json
from collections import deque
from multiprocessing import Process, Queue
import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style


if cfg.cameraLogMessages.lower()  == "debug":
  logging.getLogger("zeep").setLevel(logging.DEBUG)
  logging.getLogger("httpx").setLevel(logging.DEBUG)
elif cfg.cameraLogMessages.lower()  == "info":
  logging.getLogger("zeep").setLevel(logging.INFO)
  logging.getLogger("httpx").setLevel(logging.INFO)
elif cfg.cameraLogMessages.lower() == "critical":
  logging.getLogger("zeep").setLevel(logging.CRITICAL)
  logging.getLogger("httpx").setLevel(logging.CRITICAL)

http = urllib3.PoolManager()
basename = cfg.basenameOjectRecsFiles
ext = cfg.extensionOjectRecsFiles
os.makedirs(cfg.storageDirectory , exist_ok=True)
base_path = os.path.join(cfg.storageDirectory , basename) 


color = {
    'white':    "\033[1;37m",
    'yellow':   "\033[1;33m",
    'green':    "\033[1;32m",
    'blue':     "\033[1;34m",
    'cyan':     "\033[1;36m",
    'red':      "\033[1;31m",
    'magenta':  "\033[1;35m",
    'black':      "\033[1;30m",
    'darkwhite':  "\033[0;37m",
    'darkyellow': "\033[0;33m",
    'darkgreen':  "\033[0;32m",
    'darkblue':   "\033[0;34m",
    'darkcyan':   "\033[0;36m",
    'darkred':    "\033[0;31m",
    'darkmagenta':"\033[0;35m",
    'darkblack':  "\033[0;30m",
    'off':        "\033[0;0m"
}

### CLASS FOR GETTING FRAMES  FROM CAMERA FOR RECORDING AND AI OBJECT RECOGNITION Recognation

class camCapture:
    def __init__(self, camID):
        self.capture = cv2.VideoCapture(camID)
        self.buffer_size = cfg.videoFps*cfg.videoRecSecondsBeforeMotion
        self.deque_of_frames = deque(maxlen=self.buffer_size )
        self.deque_of_msgs = deque(maxlen=2)
        self.recording_on = False
        self.status = False
        self.isstop = False
        self.frameCounter = 0
        self.frames_read_for_recording = 0
        self.frames_written = 0
        self.recordDuration = cfg.videoDuration * 60
        self.recording_file_exists = False
        self.recording_start_time = 0
        self.motionDetectionRunning = False
        self.motionDetected = False
        self.cameraMessages  = None
        self.ret_message = None
        self.objectDetectionInterval = cfg.objectDetectionInterval
        self.lastTimeObjectDetection = 0.0
        self.objectDeltaTime = None
        self.capture_start_time = None
        self.capture_elapsed_time = 0
        self.recording_elapsed_time = 0        
        self.memfull_percentage = 0.0
        self.codec = cv2.VideoWriter_fourcc(*cfg.videoEncoder) # mind the asterix!
        self.output_video_file_name = 'output_dummy.avi'
        self.output_video = None 


    def start1(self, buffer_size):
        print(f'Camera starts filling max. buffer size of {self.buffer_size} frames')
        t1 = Thread(target=self.queryframe, daemon=True, args=())
        t1.start()

    def start2(self):
        print(f'Camera will be polled for motion event messages')
        t2 = Thread(target=self.querymsg(), daemon=True, args=())
        t2.start()
        print(T2)

    def querymsg(self):

        while (not self.isstop):
          # Read from the shared Queue
          if self.sharedQueue.empty() == False:
            self.cameraMessages = self.sharedQueue.get(True,1)
#The "\033[K" number controls the behaviour of the EL sequence:
#
#    0: clear forward till end of line (default)
#    1: clear backward till beginning of line
#    2: clear whole line
#    EL sequence does not move the cursor
          if not self.recording_on:
            print(f"{color['magenta']}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - @frame: {self.frameCounter:n} - {self.cameraMessages}",  end=f'{color["off"]}\033[K\r')
          self.deque_of_msgs.append(self.cameraMessages)
          if len(self.deque_of_msgs) > 0: 
            self.process_videos_AIpictures()

    def getmsg(self):
          return self.deque_of_msgs.popleft()

    def stop(self):
        self.isstop = True
        print('Camera stopped!')

    def getframe(self):
        return self.deque_of_frames.popleft()


    def queryframe(self):
        # used to record the time when we processed last frame 
        prev_frame_time = 0
        # used to record the time at which we processed current frame 
        new_frame_time = 0
        while (not self.isstop):
            start = time()
            self.status, tmp = self.capture.read()
            self.frameCounter += 1
            #print(f"self.frameCounter: {self.frameCounter}")
            if self.recording_on:
              self.frames_read_for_recording += 1            
            new_frame_time = time() 
            # Calculating the fps 
            # fps will be number of frames processed in given time frame 
            # since their will be most of time error of 0.001 second 
            # we will be subtracting it to get more accurate result 
            fps = 1/(new_frame_time-prev_frame_time) 
            prev_frame_time = new_frame_time 
            # converting the fps into integer 
            fps = int(fps) 
           # if fps > cfg.TapoFrameSpeed:  # slow speed down to number of real frame speed
            #  pass
          #  else:
            self.deque_of_frames.append(tmp)
            processing_time = (time() - start) *1000
            #print(f'{fps} - Read frame processed : {processing_time:2.0f}ms', end='\033[K\r')
            
        self.capture.release()
        
        
    def process_videos_AIpictures(self):        
          if self.recording_on == False:
            self.motionDetected = False
            self.cameraMessages = self.getmsg()  # get a msg(s) from the camera!
          else:
            self.ret_message = 'recording'
          if self.cameraMessages.startswith("Motion Detected."):     
              self.motionDetected = True
          elif self.cameraMessages.startswith("No cameraMessages"):     
            # Server disconnected without sending a response, probably due to no cameraMessages.
            print(f"{color['red']}A check of the camera might be needed!\n{self.ret_message}",  end=f"{color['off']}\033[K\r")
            exit(1) 
          else:
              self.motionDetected = False


          # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
         # print(f"Frame: {self.frameCounter:n} Buffer: {len(self.deque_of_frames)}={sys.getsizeof(self.deque_of_frames):n}bytes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Motion detected: {'yes' if self.motionDetected else 'no '} Camera UTC time: {self.cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S') if self.cameraMessages else 'not available'}", end='\033[K\r') # with output include this \n{cameraMessages}", end='\033[K\r')  
        
          # simulate a motion detection
          if cfg.RunMotionSimulation_1:
            if 150 <= self.frameCounter <= 450: self.motionDetected=True
          if cfg.RunMotionSimulation_2:
            if 1050 <= self.frameCounter <= 1250: self.motionDetected=True

          # If a motion is detected the recording will be switched on and 
          # recording will happen as long as the cfg.recordDuration indicates
          # even if meanwhile no motion has been detected!
          # When de maximum recording time (cfg.recordDuration) is reached the recording will be switch off
          # a recording file will be created at the start of recording and closed(released) when max recording time is reached 
          if self.motionDetected:
               if self.recording_on == False:  
                  self.recording_on = True 
                  self.frames_read_for_recording = 0    
  
          if self.recording_on == True:
              if self.recording_file_exists == True:
                pass
              else:
                # create a new recording file with time stamp.
                fileName = f"{cfg.storageDirectory}Output_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{cfg.videoRecsFiles}"    # file name with date,time stamping
                # print(self.codec, cfg.videoFps, self.recording_frame_dimension)
                self.output_video = cv2.VideoWriter(fileName, self.codec, cfg.videoFps, self.recording_frame_dimensions)
                print(f"\033[K{color['yellow']}Recording in file: {fileName}", end=f"{color['off']}\n")
                self.recording_file_exists = True  # the recording file has been created
                self.recording_start_time = time()
                self.recording_elapsed_time = 0 
                
              if self.recording_file_exists == True:  
                while self.recording_on == True and len(self.deque_of_frames) > 0:  
                  frame = self.getframe() # get a frame(s) from the camera!
                  self.recording_elapsed_time = (time() - self.recording_start_time)  
                  print(f"\033[K{color['green']}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - @frame: {self.frameCounter:n} - Motion detected, recording time elapsed: {self.recording_elapsed_time:2.0f}s < Max. duration: {self.recordDuration:2.0f}s", end=f"{color['off']}\r")                    

                  if self.recording_on and self.motionDetected:
                    if self.recordDuration < 2.5 * 60: # maximum of 2.5 minutes of recording in one file
                        self.recordDuration += 1  # add 1 second extra recording time
                  else:
                    self.recordDuration =  cfg.videoDuration * 60 # reset to original value

                  if self.recording_elapsed_time > self.recordDuration: 
                    self.output_video.release()  # make sure the file with the recording will be closed properly
                    self.recording_on = False # stop recording as record duration was reached  
                    self.motionDetected = False # set camera motion detected switch to off
                    self.recording_file_exists = False # set switch on to make new recording file creation possible
                    self.recording_elapsed_time = 0  # reset the recording elapsed time to zero  
                    self.recording_start_time = 0 # reset the start time the recording 
                    # print(f"Frames read => {cam.frames_read_for_recording} ex. buffer: {len(self.deque_of_frames)} | {self.frames_written} <= Frames written", end='\033[K\n') 
                    break  # important break the while loop! 

                  if frame.all() != None:
                    the_frame =  frame.copy()
                    if cfg.videoRecordingResolutionFactor < 1.0:   # downscale by configurable factor
                      frame = cv2.resize(the_frame, self.recording_frame_dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
                    self.output_video.write(frame)
                    self.frames_written += 1  

                    try:
                      if cfg.AIserverInstalled:
                         self.lastTimeObjectDetection = self.AIObjectRecognition(frame, self.AI_picture_dimensions, self.lastTimeObjectDetection)   # call AI object recognition 
                    except Exception as e:
                         print(f"Continue writing frames. Error happened with AI Object Recognition: \n{e}",end='\033[K\n')

              else:
                self.recording_on = False 
                self.frames_read_for_recording = 0
                

    def AIObjectRecognition(self, frame, AI_picture_dimensions, lastTimeObjectDetection):
        if self.recording_on:
          self.objectDeltaTime = time() - self.lastTimeObjectDetection
          #print(self.objectDeltaTime , '>', self.objectDetectionInterval)
          if self.objectDeltaTime > self.objectDetectionInterval: # every x seconds see cfg.objectDetectionInterval

              the_frame =  frame.copy()
              if cfg.AIpictureResolutionFactor < 1.0:   # scale by configurable factor
                the_frame = cv2.resize(the_frame, AI_picture_dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
              is_success, buffer = cv2.imencode(".jpg", the_frame)
              io_buf = io.BytesIO(buffer)

              code, new_confidence, seconds, confidence_change_per_second_morning = get_adapted_confidence(datetime.now(pytz.UTC) ) 
              #print (f'Code: {code}, new_confidence: {new_confidence}, seconds:{seconds}, change/sec: {confidence_change_per_second_morning}')



              response = http.request_encode_body(
                  'POST',
                  cfg.AIserverUrl,  headers=None, encode_multipart=True, multipart_boundary=None,
                  fields = {'min_confidence': f'{new_confidence}', 'typedfile': (f"{basename}.{ext}", io_buf.getbuffer(),'image/jpg'),}   #open(image_path,"rb").read(),'image/jpg'),}
              )# .json() 
              #print(response.status)
              if f"{response.status}".startswith('20'):
                  res = json.loads(response.data) 
                  # using json.loads()
                  # convert dictionary string to dictionary  
                  #print(f"response={res}")   
                  if "success" in res:
                      if "predictions" in res:
                          # we save the time of the last object detection
                          self.lastTimeObjectDetection = time()
                          labels = []
                          for object in res["predictions"]:
                              #print(object) #["label"])
                              label = object["label"]  
                              confidence = object["confidence"]  
                              label_confidence = f'{label}-{(confidence*100.0):.01f}%'                            
                              if label in cfg.ObjectsToDetect: # we capture picture(s) only for these objects see myTapoMotionConfig.py file
                                object_rect_line_thickness = 1 # line thickness around detected object   
                                font_scale = cfg.font_scale_Label
                                (text_width, text_height) = cv2.getTextSize(label_confidence, cv2.FONT_HERSHEY_SIMPLEX, font_scale, object_rect_line_thickness)[0]
                                # set the text color (foreground) 
                                text_thickness = 0 #  thickness of the text in the box
                                # set the text color (foreground) 
                                text_color = cfg.colorLabelText # black or white are usual colors
                                # set the text rectangle background 
                                startX  = object["x_min"]  # left line position of the object box and labelbox
                                startY  = object["y_min"]  # top line position of the object box and reference +shift for bottom line labelbox
                                endX    = object["x_max"]
                                endY    = object["y_max"]
                                shift = 0 # pixels above the top line of the object rectangle
                                bottom_line_labelbox = startY - shift if startY - shift > shift else startY + shift
                                top_line_labelbox  = bottom_line_labelbox - text_height 
                                top_left_labelbox = (startX, top_line_labelbox) 
                                left_line_labelbox = startX
                                right_line_labelbox = startX + text_width
                                bottom_right_labelbox =  (right_line_labelbox , bottom_line_labelbox )
                                box_coords = (top_left_labelbox, bottom_right_labelbox)
                                # draw the filled label box
                                cv2.rectangle(the_frame, box_coords[0], box_coords[1], cfg.colorLabelRectangle, -1)     # light green color = (0, 255, 124), lightblue = (0, 190, 255)
                                # linestypes: Filled=cv2.FILLED, 4-connected=line LINE_4 cv2.LINE_4 8-connected line=cv2.LINE_8, antialiased line=cv2.LINE_AA
                                # put text the filled label box
                                cv2.putText(the_frame, label_confidence, (startX, bottom_line_labelbox ), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, text_thickness, cv2.LINE_AA)                                                                                        
                                # draw the boax around the detected object
                                cv2.rectangle(the_frame, (startX - object_rect_line_thickness, startY + object_rect_line_thickness), (endX + object_rect_line_thickness, endY + 2*(object_rect_line_thickness)), cfg.colorObjectRectangle , object_rect_line_thickness)
                                cv2.imwrite(f'{base_path}_{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}_{object["label"]}.{ext}', the_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                                        
                                # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
                                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} objectDetected: {object['label']}", end='\033[K\r') 

                                #break # with break active only one image will be created per detection round
                                  
                      elif "message" in res:
                          print(res["message"])
                      elif "error" in res:
                          print(res["error"])
                      else:
                          pass
                          #print(res)
                      #print(res)

        return self.lastTimeObjectDetection
        
        

### CLASS FOR GETTING MESSAGES FROM CAMERA

class myCamMsgs:
    async def getOnvifMessages(self,sharedQueue):
      self.sharedQueue = sharedQueue
    ###  lines marked with ###  have been tested and are working fine, but not needed here  
      self.OnvifCam = ONVIFCamera(
          cfg.cameraIP,
          int(cfg.cameraOnvifPort) ,
          cfg.cameraUser,
          cfg.cameraPassw,  
          cfg.cameraOnvif_wsdl_dir,
          )
      # Update xaddrs for services 
      await self.OnvifCam.update_xaddrs() 
      
      # Create a pullpoint manager. 
      interval_time = (dt.timedelta(seconds=5))
      pullpoint_mngr = await self.OnvifCam.create_pullpoint_manager(interval_time, subscription_lost_callback = Callable[[], None],)

      # create the subscription 
      subscription = await self.OnvifCam.create_subscription_service("PullPointSubscription")
      while True:
        # create the pullpoint  
        pullpoint = await self.OnvifCam.create_pullpoint_service()
        
        # call SetSynchronizationPoint to generate a notification message too ensure the webhooks are working.
        await pullpoint.SetSynchronizationPoint()      
      
        # pull the cameraMessages from the camera, set the request parameters
        # by setting the pullpoint_req.Timeout you define the refreshment speed of the pulls
        pullpoint_req = pullpoint.create_type('PullMessages') 
        pullpoint_req.MessageLimit=10
        pullpoint_req.Timeout = (dt.timedelta(days=0,hours=0,seconds=1))

        cameraMessages = await pullpoint.PullMessages(pullpoint_req)
        #print(f'\033[K{color["yellow"]}',cameraMessages, end=f'{color["off"]}\033[K\n') 
        # renew the subscription makes sense when looping over 
        termination_time = (
           (dt.datetime.utcnow() + dt.timedelta(days=1,hours=1,seconds=3))
              .isoformat(timespec="seconds").replace("+00:00", "Z")
          ) 
        if cameraMessages:
          cur_time = f"Camera Current Time: {cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S')}"
          if cameraMessages['NotificationMessage'] != []:
            ret_message = f"Motion Detected. {cur_time}"
          else:
            ret_message = f"No Notification received. {cur_time}"   
        else:
          ret_message = "No cameraMessages received." 
        self.sharedQueue.put(ret_message)  
        
        #print(f"{color['blue']}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Send: {ret_message}",  end=f"{color['off']}\033[K\n")        
        await subscription.Renew(termination_time)  
          
        # we close the pullpoint . This makes sense when no While loop is used  
        #await pullpoint.close()
        #await self.OnvifCam.close()  
        #return self.cameraMessages

    def motionDetection(self,sharedQueue):
      asyncio.get_event_loop().run_until_complete(self.getOnvifMessages(sharedQueue))



def startRecording(sharedQueue):
    cam = camCapture(cfg.videoUrl)
    cam.sharedQueue = sharedQueue
    print(f"Start of capturing @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 
    print(f"The capture backend is: {cam.capture.getBackendName()}") 
    # The default resolutions of the frame are obtained (system dependent)
    cam.frame_width = int(cam.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam.frame_height = int(cam.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))     
    print(f"Camera {cfg.cameraStream} resolution Width x Height: {cam.frame_width}x{cam.frame_height}")

    if  cfg.cameraStream == 'stream1' and cfg.videoRecordingResolutionFactor > 0.75 and \
         cfg.videoEncoder.lower() in ('avc1', 'x264', 'h264'):  # these codecs do NOT work with stream1's large resolution
        # Need to set to max allowed frame resolution to: 1920x1080 which equals to resizing factor 0.75
        cfg.videoRecordingResolutionFactor = 0.75 
 
    cam.AI_picture_dimensions = (int(cam.frame_width * cfg.AIpictureResolutionFactor), int(cam.frame_height * cfg.AIpictureResolutionFactor))  

    cam.recording_frame_dimensions = (int(cam.frame_width * cfg.videoRecordingResolutionFactor), int(cam.frame_height * cfg.videoRecordingResolutionFactor))  

    print(f"Recording resolution Width x Height: {cam.recording_frame_dimensions[0]}x{cam.recording_frame_dimensions[1]}")

    if cfg.AIserverInstalled == True:
     print(f"AI object recognition picture resolution Width x Height: {cam.AI_picture_dimensions[0]}x{cam.AI_picture_dimensions[1]}")
       
    # start the thread to read video frames from the camera
    cam.start1(buffer_size=cam.buffer_size)
    # wait till buffer is filled
    sleep(cfg.videoRecSecondsBeforeMotion)
    # start the thread to read ONVIF messages from the camera
    cam.start2()



if __name__ == '__main__':
  
    sharedQueue = Queue()
    trx = myCamMsgs()
    global p1, p2
    p1 = Process(target=trx.motionDetection, args=(sharedQueue,))      # process p1
    p1.daemon = True
    p1.start() 
    p2 = Process(target=startRecording, args=(sharedQueue,))
    p2.start() 
    p1.join()
    p2.join()

  
  
