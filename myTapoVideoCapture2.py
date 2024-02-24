# DESCRIPTION
# myTapoMotionDetection.py - This program can be run seperately to check your camera motion messages
#   It uses the ONVIF standard to pull motion messages from the Tapo Camera (tested on C225 model)
# myTapoMotionConfig.py - This contains the parameters to configure the proces, 
#   Be carefull to change the configuration as it is (simple) Python program code!#
# myTapoVideoCapture - This reads the camera RTSP stream and records it when motion is detected
#   It will also call the AI object Server to create a (compact) jpg picture with 
#   the recognised object(s) marked with a rectangle and label
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

from threading import Thread
from myTapoMotionConfig import cfg
from myTapoMotionDetection import motionDetection
from datetime import datetime
from time import sleep, time
import cv2
import os
import sys
import io
import urllib3
import json
import numpy as np
import psutil
from collections import deque
import imutils

import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style


http = urllib3.PoolManager()
basename = cfg.basenameOjectRecsFiles
ext = cfg.extensionOjectRecsFiles
os.makedirs(cfg.storageDirectory , exist_ok=True)
base_path = os.path.join(cfg.storageDirectory , basename) 

frames_read = 0
frames_written = 0
recordDuration = cfg.videoDuration * 60
recording_file_exists = False
recording_on = False
recording_start_time = 0
motionDetectionRunning = False
motionDetected = False
cameraMessages  = None
ret_message = None
objectDetectionInterval = cfg.objectDetectionInterval
lastTimeObjectDetection = time()
objectDeltaTime = None
capture_start_time = None
capture_elapsed_time = 0
recording_elapsed_time = 0        
memfull_percentage = 0.0
codec = cv2.VideoWriter_fourcc(*cfg.videoEncoder) # mind the asterix!
output_video_file_name = None
output_video = None 
camera_buffer_size=cfg.videoFps*cfg.videoRecSecondsBeforeMotion


class camCapture:
    def __init__(self, camID, buffer_size):
        self.deque_of_frames = deque(maxlen=buffer_size)
        self.status = False
        self.isstop = False
        self.frameCounter = 0
        self.frames_read = 0
        self.capture = cv2.VideoCapture(camID)

    def start(self, buffer_size):
        print(f'Camera starts filling max. buffer size of {buffer_size} frames')
        t1 = Thread(target=self.queryframe, daemon=True, args=())
        t1.start()

    def stop(self):
        self.isstop = True
        print('Camera stopped!')

    def getframe(self):
        return self.deque_of_frames.popleft()

    def get_allbufferedframes(self):
        self.allbufferedframes = self.deque_of_frames.copy()
        self.deque_of_frames.rotate(len(self.allbufferedframes)) #  Rotate the deque n steps to the right.
        return self.allbufferedframes

    def queryframe(self):
        while (not self.isstop):
            start = time()
            self.status, tmp = self.capture.read()
            self.frameCounter += 1
            self.frames_read += 1
            #print('Read frame processed : ', (time() - start) *1000, 'ms', end='\033[K\r')
            self.deque_of_frames.append(tmp)

        self.capture.release()

# END OF CLASS

def AIObjectRecognition(frame, AI_picture_dimensions, lastTimeObjectDetection):
  if motionDetected:
    objectDeltaTime = time() - lastTimeObjectDetection
    # print(objectDeltaTime , '>', objectDetectionInterval)
    if objectDeltaTime > objectDetectionInterval: # every x seconds see cfg.objectDetectionInterval

        the_frame =  frame.copy() 
        if cfg.AIpictureResolutionFactor <= 1.0:   # downscale by configurable factor
          the_frame = cv2.resize(the_frame, AI_picture_dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
        is_success, buffer = cv2.imencode(".jpg", the_frame)
        io_buf = io.BytesIO(buffer)
        # decode
        # decode_img = cv2.imdecode(np.frombuffer(io_buf.getbuffer(), np.uint8), -1)
        #myiofile = io_buf.getbuffer()

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
  lastTimeObjectDetection = time()
  return lastTimeObjectDetection


# END of AI Object Recognition function


if __name__ == '__main__':
    print(f"Start of capturing @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 

    cam = camCapture(camID=cfg.videoUrl , buffer_size=camera_buffer_size)
    
    # The default resolutions of the frame are obtained (system dependent)
    frame_width = int(cam.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))     
    print(f"Frame width x height: {frame_width}x{frame_height}")
    AI_picture_dimensions = (int(frame_width * cfg.AIpictureResolutionFactor), int(frame_height * cfg.AIpictureResolutionFactor))  
        
    # start the reading frame thread
    cam.start(buffer_size=camera_buffer_size)

    # filling the deque/buffer with frames read
    sleep(5)

    # the moment we can capture a video after the buffer was filled
    capture_start_time = time()
    
    # check if their is enough memory left for other programs
    
    memfull_percentage = ( psutil.virtual_memory().used / psutil.virtual_memory().total ) * 100.0
    # we save frames in memory to catch the latest frames before motion detection triggers the recording (pre-motion)
    if memfull_percentage > cfg.memoryFull_percentage:   # to avoid an overrun of the memory by saving large frames and numbers of seconds of stream1)
      print(f"Memory percentage {memfull_percentage:2.1f} is above threshold of {cfg.memoryFull_percentage}.\nProgram Stops! Adapt in configuration: cfg.videoFps and/or cfg.videoRecSecondsBeforeMotion.", end='\033[K\n')
      exit(1)


    while True:
      #try:
          if recording_on == False:  # Only check for motion detection when no recording happens to avoid delay in writing frames
            ret_message, cameraMessages = motionDetection()
          else:
            ret_message = 'recording'
          # print(cameraMessages , '\n')
          
          if ret_message == 'ok':     # camera has returned a message
            if cameraMessages['NotificationMessage'] != []:
              motionDetected = True
            else:
              motionDetected = False
          elif ret_message == 'recording': # 
            motionDetected = True
          else: # Server disconnected without sending a response, probably due to no cameraMessages.
            print(f"A check of the camera might be needed!\n{ret_message}", end='\033[K\n')
            exit(1) 

          # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
          print(f"Frame: {cam.frameCounter:n} Buffer: {len(cam.deque_of_frames)}={sys.getsizeof(cam.deque_of_frames):n}bytes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Motion detected: {'yes' if motionDetected else 'no '} Camera UTC time: {cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S') if cameraMessages else 'not available'}", end='\033[K\r') # with output include this \n{cameraMessages}", end='\033[K\r')  

            
          # simulate a motion detection
          if cfg.RunMotionSimulation_1:
            if 150 <= cam.frameCounter <= 450: motionDetected=True
          if cfg.RunMotionSimulation_2:
            if 1050 <= cam.frameCounter <= 1250: motionDetected=True

          # If a motion is detected the recording will be switched on and 
          # recording will happen as long as the cfg.recordDuration indicates
          # even if meanwhile no motion has been detected!
          # When de maximum recording time (cfg.recordDuration) is reached the recording will be switch off
          # a recording file will be created at the start of recording and closed(released) when max recording time is reached 
          if motionDetected:
               if recording_on == False:  
                  recording_on = True     
  
          
          if recording_on == True:
              if recording_file_exists == True:
                pass
              else:
                # create a new recording file with time stamp.
                fileName = f"{cfg.storageDirectory}Output_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{cfg.videoRecsFiles}"    # file name with date,time stamping
                # print(codec, cfg.videoFps, (frame_width, frame_height))
                output_video = cv2.VideoWriter(fileName, codec, cfg.videoFps, (frame_width, frame_height))
                print(f"Recording in file: {fileName}", end='\033[K\n')
                recording_file_exists = True  # the recording file has been created
                recording_start_time = time()
                recording_elapsed_time = 0 
                

              if recording_file_exists == True:  
                while recording_on == True and len(cam.deque_of_frames) > 0:  
                  frame = cam.getframe() # get a frame(s) from the camera!
                  recording_elapsed_time = (time() - recording_start_time)  
                  print(f"Record time elapsed: {recording_elapsed_time:2.0f}s < Max. duration: {recordDuration:2.0f}s, frames in buffer: {len(cam.deque_of_frames)}", end='\033[K\r')                    

                  if recording_elapsed_time > recordDuration: 
                    output_video.release()  # make sure the file with the recording will be closed properly
                    recording_on = False # stop recording as record duration was reached  
                    motionDetected = False # set camera motion detected switch to off
                    recording_file_exists = False # set switch on to make new recording file creation possible
                    recording_elapsed_time = 0  # reset the recording elapsed time to zero  
                    recording_start_time = 0 # reset the start time the recording 
                    print(f"Frames read => {cam.frames_read} | {frames_written} <= Frames written", end='\033[K\n') 
                    break  # important break the while loop! 

                  
                  output_video.write(frame)
                  frames_written += 1  

                  try:
                    if cfg.AIserverInstalled:
                       lastTimeObjectDetection = AIObjectRecognition(frame, AI_picture_dimensions, lastTimeObjectDetection)   # call AI object recognition 
                  except Exception as e:
                       print(f"Continue writing frames. Error happened with AI Object Recognition: \n{e}",end='\033[K\n')
                      

                 # cv2.imshow('video',frame)
                 # sleep( 20 / 1000) # mimic the processing time

                 # if cv2.waitKey(1) == 27:  # 27 is escape
                 #       cv2.destroyAllWindows()
                 #       cam.stop()
                 #       exit(0)

                  
           
              else:
                recording_on = False 
                
                 
                

          #show_frame()      # displays a window. use key q to quit, but it will reappear due to loop
          #print(f"{cam.frameCounter} recording?: {recording_on}, rec.file?: {recording_file_exists}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, recording_elapsed_time: {recording_elapsed_time} < {recordDuration}?") 

     # except Exception as e:
     #     print(f"error: \n{e}")


