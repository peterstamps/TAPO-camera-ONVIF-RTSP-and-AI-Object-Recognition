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

from myTapoMotionConfig import cfg
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


class camCapture:
    def __init__(self, camID):
        self.buffer_size = cfg.videoFps*cfg.videoRecSecondsBeforeMotion
        self.deque_of_frames = deque(maxlen=self.buffer_size )
        self.deque_of_msgs = deque(maxlen=2)
        self.recording_on = False
        self.status = False
        self.isstop = False
        self.frameCounter = 0
        self.capture = cv2.VideoCapture(camID)
        self.frames_read = 0
        self.frames_written = 0
        self.recordDuration = cfg.videoDuration * 60
        self.recording_file_exists = False
        self.recording_start_time = 0
        self.motionDetectionRunning = False
        self.motionDetected = False
        self.cameraMessages  = None
        self.ret_message = None
        self.objectDetectionInterval = cfg.objectDetectionInterval
        self.lastTimeObjectDetection = time()
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

    def start2(self, interval_time):
        print(f'Camera will be asked for motion event messages each {cfg.cameraMsgQueryInterval}s')
        t2 = Thread(target=self.querymsg(cfg.cameraMsgQueryInterval), daemon=True, args=())
        t2.start()

    def querymsg(self,interval_time):
        while (not self.isstop):
          self.ret_message,self.cameraMessages = self.motionDetection()
          #print(self.ret_message,self.cameraMessages)
          tmp = [self.ret_message, self.cameraMessages]
          self.deque_of_msgs.append(tmp)
          #sleep(interval_time) # maybe needed: minimal interval between each query to avoid overloading the camera  
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
        while (not self.isstop):
            start = time()
            self.status, tmp = self.capture.read()
            self.frameCounter += 1
            self.frames_read += 1
            processing_time = (time() - start) *1000
            #print(f'Read frame processed : {processing_time:2.0f}ms', end='\033[K\r')
            self.deque_of_frames.append(tmp)
        self.capture.release()
        
        
    def process_videos_AIpictures(self):        
          if self.recording_on == False:
            self.motionDetected = False
            self.ret_message, self.cameraMessages = self.getmsg()  # get a msg(s) from the camera!
          else:
            self.ret_message = 'recording'
          if self.ret_message == 'ok':     # camera has returned a message
            if self.cameraMessages['NotificationMessage'] != []:
              self.motionDetected = True
            else:
              self.motionDetected = False
          elif self.ret_message == 'recording': # 
            self.motionDetected = True
          else: # Server disconnected without sending a response, probably due to no cameraMessages.
            print(f"A check of the camera might be needed!\n{self.ret_message}", end='\033[K\n')
            exit(1) 

          # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
          print(f"Frame: {self.frameCounter:n} Buffer: {len(self.deque_of_frames)}={sys.getsizeof(self.deque_of_frames):n}bytes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Motion detected: {'yes' if self.motionDetected else 'no '} Camera UTC time: {self.cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S') if self.cameraMessages else 'not available'}", end='\033[K\r') # with output include this \n{cameraMessages}", end='\033[K\r')  

            
          # simulate a motion detection
          if cfg.RunMotionSimulation_1:
            if 150 <= cam.frameCounter <= 450: self.motionDetected=True
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
  
          if self.recording_on == True:
              if self.recording_file_exists == True:
                pass
              else:
                # create a new recording file with time stamp.
                fileName = f"{cfg.storageDirectory}Output_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{cfg.videoRecsFiles}"    # file name with date,time stamping
                # print(self.codec, cfg.videoFps, (self.frame_width, self.frame_height))
                self.output_video = cv2.VideoWriter(fileName, self.codec, cfg.videoFps, (self.frame_width, self.frame_height))
                print(f"Recording in file: {fileName}", end='\033[K\n')
                self.recording_file_exists = True  # the recording file has been created
                self.recording_start_time = time()
                self.recording_elapsed_time = 0 
                
              if self.recording_file_exists == True:  
                while self.recording_on == True and len(self.deque_of_frames) > 0:  
                  frame = self.getframe() # get a frame(s) from the camera!
                  self.recording_elapsed_time = (time() - self.recording_start_time)  
                  print(f"Record time elapsed: {self.recording_elapsed_time:2.0f}s < Max. duration: {self.recordDuration:2.0f}s, frames in buffer: {len(self.deque_of_frames)}", end='\033[K\r')                    

                  if self.recording_elapsed_time > self.recordDuration: 
                    self.output_video.release()  # make sure the file with the recording will be closed properly
                    self.recording_on = False # stop recording as record duration was reached  
                    self.motionDetected = False # set camera motion detected switch to off
                    self.recording_file_exists = False # set switch on to make new recording file creation possible
                    self.recording_elapsed_time = 0  # reset the recording elapsed time to zero  
                    self.recording_start_time = 0 # reset the start time the recording 
                    print(f"Frames read => {cam.frames_read} | {self.frames_written} <= Frames written", end='\033[K\n') 
                    break  # important break the while loop! 

                  if frame.all() != None:
                    self.output_video.write(frame)
                    self.frames_written += 1  

                    try:
                      if cfg.AIserverInstalled:
                         self.lastTimeObjectDetection = self.AIObjectRecognition(frame, AI_picture_dimensions, self.lastTimeObjectDetection)   # call AI object recognition 
                    except Exception as e:
                         print(f"Continue writing frames. Error happened with AI Object Recognition: \n{e}",end='\033[K\n')

              else:
                self.recording_on = False 
                

    def AIObjectRecognition(self, frame, AI_picture_dimensions, lastTimeObjectDetection):
        if self.motionDetected:
          self.objectDeltaTime = time() - self.lastTimeObjectDetection
          # print(self.objectDeltaTime , '>', self.objectDetectionInterval)
          if self.objectDeltaTime > self.objectDetectionInterval: # every x seconds see cfg.objectDetectionInterval

              the_frame =  frame.copy()
              if cfg.videoScale <= 1.0:   # downscale by configurable factor
                the_frame = cv2.resize(the_frame, AI_picture_dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
              is_success, buffer = cv2.imencode(".jpg", the_frame)
              io_buf = io.BytesIO(buffer)

              response = http.request_encode_body(
                  'POST',
                  cfg.AIserverUrl,  headers=None, encode_multipart=True, multipart_boundary=None,
                  fields = {'min_confidence': f'{cfg.min_confidence}', 'typedfile': (f"{basename}.{ext}", io_buf.getbuffer(),'image/jpg'),}   #open(image_path,"rb").read(),'image/jpg'),}
              )# .json() 
              #print(response.status)
              if f"{response.status}".startswith('20'):
                  res = json.loads(response.data) 
                  # using json.loads()
                  # convert dictionary string to dictionary  
                  #print(f"response={res}")   
                  if "success" in res:
                      if "predictions" in res:
                          labels = []
                          for object in res["predictions"]:
                              #print(object["label"])
                              label = object["label"]    
                              if label in cfg.ObjectsToDetect: # we capture picture(s) only for these objects see myTapoMotionConfig.py file
                                object_rect_line_thickness = 1 # line thickness around detected object   
                                font_scale = cfg.font_scale_Label
                                (text_width, text_height) = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, object_rect_line_thickness)[0]
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
                                padding = 1
                                # draw the filled label box
                                cv2.rectangle(the_frame, box_coords[0], box_coords[1], cfg.colorLabelRectangle, -1)     # light green color = (0, 255, 124), lightblue = (0, 190, 255)
                                # linestypes: Filled=cv2.FILLED, 4-connected=line LINE_4 cv2.LINE_4 8-connected line=cv2.LINE_8, antialiased line=cv2.LINE_AA
                                # put text the filled label box
                                cv2.putText(the_frame, label, (startX + padding, bottom_line_labelbox - padding ), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, text_thickness, cv2.LINE_AA)                                                                                        
                                # draw the boax around the detected object
                                cv2.rectangle(the_frame, (startX - object_rect_line_thickness, startY + object_rect_line_thickness), (endX + object_rect_line_thickness, endY + 2*(object_rect_line_thickness)), cfg.colorObjectRectangle , object_rect_line_thickness)
                                cv2.imwrite(f'{base_path}_{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}_{object["label"]}.{ext}', the_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                                        
                                # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
                                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} objectDetected: {object['label']}", end='\033[K\r') 

                                break # we creat only one image
                                  
                      elif "message" in res:
                          print(res["message"])
                      elif "error" in res:
                          print(res["error"])
                      else:
                          pass
                          #print(res)
                      #print(res)
        # we save the time of the last object detection
        self.lastTimeObjectDetection = time()
        return self.lastTimeObjectDetection

    async def getOnvifMessages(self):
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

      # create the pullpoint  
      pullpoint = await self.OnvifCam.create_pullpoint_service()
    
      # pull the cameraMessages from the camera, set the request parameters
      # by setting the pullpoint_req.Timeout you define the refreshment speed of the pulls
      pullpoint_req = pullpoint.create_type('PullMessages') 
      pullpoint_req.MessageLimit=10
      pullpoint_req.Timeout = (dt.timedelta(days=0,hours=0,seconds=1))
      self.cameraMessages = await pullpoint.PullMessages(pullpoint_req)

      # we close the pullpoint . This makes sense when no While loop is used  
      await pullpoint.close()
      await self.OnvifCam.close()  
      return self.cameraMessages

    def motionDetection(self):
      while True: 
        cameraMessages =asyncio.new_event_loop().run_until_complete(self.getOnvifMessages())
        ret_message = "ok"
        #print('motion', ret_message, cameraMessages)
        return ret_message, cameraMessages


if __name__ == '__main__':
    print(f"Start of capturing @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 

    cam = camCapture(camID=cfg.videoUrl)
    
    # The default resolutions of the frame are obtained (system dependent)
    cam.frame_width = int(cam.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam.frame_height = int(cam.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))     
    print(f"Frame width x height: {cam.frame_width}x{cam.frame_height}")
    AI_picture_dimensions = (int(cam.frame_width * cfg.videoScale), int(cam.frame_height * cfg.videoScale))  
        
    # start the thread to read video frames from the camera
    cam.start1(buffer_size=cam.buffer_size)
    # start the thread to read ONVIF messages from the camera
    cam.start2(interval_time=cfg.cameraMsgQueryInterval)

