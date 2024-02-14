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
import time
import cv2
import os
import io
import urllib3
import json
import numpy as np
import psutil
from collections import deque

import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style

http = urllib3.PoolManager()

basename = cfg.basenameOjectRecsFiles
ext = cfg.extensionOjectRecsFiles
os.makedirs(cfg.storageDirectory , exist_ok=True)
base_path = os.path.join(cfg.storageDirectory , basename)                  


class RTSPVideoWriterObject(object):

    def __init__(self, rtsp_stream_link=None):
        # Create a VideoCapture object
        self.status = None
        self.frame = None
        self.frameCounter = 0  
        self.frames_read = 0  
        self.frames_written = 0 
        self.number_of_frames_to_prerecord = cfg.videoFps*cfg.videoRecSecondsBeforeMotion
        self.deque_of_frames = deque()
        self.recordDuration = cfg.videoDuration * 60
        self.recording_file_exists = False
        self.recording_on = False
        self.capture_start_time = time.time()
        self.recording_start_time = 0
        self.motionDetected = False
        self.cameraMessages  = None
        self.ret_message = None
        self.objectDetectionInterval = cfg.objectDetectionInterval
        self.lastObjectDetectiontime = time.time()
        self.objectDeltaTime = None
        self.capture_elapsed_time = 0
        self.recording_elapsed_time = 0        
        self.capture = cv2.VideoCapture(rtsp_stream_link)
        self.memfull_percentage = 0.0

        # Default resolutions of the frame are obtained (system dependent)
        #sel.frame_width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        #self.frame_height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.frame_width = int(self.capture.get(3)) # same as above
        self.frame_height = int(self.capture.get(4)) # same as above       
        self.dimensions = (int(self.frame_width * cfg.videoScale), int(self.frame_height * cfg.videoScale))  
              
        # Set up codec and output video settings
        #self.codec = cv2.VideoWriter_fourcc('M','J','P','G') # compression format
        #self.codec = cv2.VideoWriter_fourcc(*'MJPG') # same compression format as above, other notation: mind the asterix!
        #self.codec = cv2.VideoWriter_fourcc(*'XVID') # compression format
        #self.codec = cv2.VideoWriter_fourcc(*'RGBA') #original large format
        #self.codec = cv2.VideoWriter_fourcc(*'X264') #compact compression format
        self.codec = cv2.VideoWriter_fourcc(*cfg.videoEncoder) # mind the asterix!
        
        self.output_video_file_name = None
        self.output_video = None # was cv2.VideoWriter(self.output_video_file_name, self.codec, cfg.videoFps, (self.frame_width, self.frame_height))

        # Start a thread to read and record frames from the video stream
        self.thread = Thread(target=self.record_frames, args=())
        self.thread.daemon = True
        self.thread.start()          


    def record_frames(self):
        # Read the next frames from the stream in a different thread
        while True:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
                self.frameCounter += 1
                if vsw.recording_on == True:
                  self.frames_read += 1
                self.memfull_percentage = ( psutil.virtual_memory().used / psutil.virtual_memory().total ) * 100.0
                # we save frames in memory to catch the latest frames before motion detection triggers the recording (pre-motion)
                if self.memfull_percentage > cfg.memoryFull_percentage:   # to avoid an overrun of the memory by saving large frames and numbers of seconds of stream1)
                  print(f"Memory percentage {self.memfull_percentage} is above threshold of {cfg.memoryFull_percentage}. Dropping recorded frames.", end='\033[K\n')
                  self.deque_of_frames.popleft() # drop first frame from deque!
                else: # enough RAM memory to keep frames                  
                  if len(self.deque_of_frames) > self.number_of_frames_to_prerecord: # With 30fps this means 150 frames in memory
                    self.deque_of_frames.popleft() # drop first frame from deque!
                  else:
                    self.deque_of_frames.append(self.frame) # add frame to deque
                  
                #print(f"At frame {self.frameCounter}. Now we have {len(self.deque_of_frames)} prerecorded frames. Max.: {self.number_of_frames_to_prerecord if self.number_of_frames_to_prerecord else ''} ", end='\033[K\n')

            
    def write_frames(self):
        # write the read frames from the memory buffer into video output file when recording is on
        while self.recording_on == True and len(self.deque_of_frames) > 0:   
          # write the first recorded frame in the deque and then drop that 
          frame = self.deque_of_frames.popleft()  
          self.output_video.write(frame)
          self.frames_written += 1 
          try:
            if cfg.AIserverInstalled:
              self.AIObjectRecognition()   # call AI object recognition 
          except Exception as e:
              print(f"Continue writing frames. Error happened with AI Object Recognition: \n{e}",end='\033[K\n')
              
            

    def start_recorder(self, recording=True):
          self.frames_written = 0 # reset the write frames counter
          self.recording_on = True   # set recording switch to on
          self.recording_start_time = time.time() # set the start time the recording  
          self.recording_elapsed_time = 0  # reset the start of the recording elapsed time         
          if self.recording_file_exists == True:
            pass
          else:
            # create a new recording file with time stamp.
            fileName = f"{cfg.storageDirectory}Output_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{cfg.videoRecsFiles}"    # file name with date,time stamping
            vsw.set_output_video_file_name(fileName)                        
            print(f"Recording file created: {fileName}", end='\033[K\n')
            vsw.recording_file_exists = True  # the recording file has been created


    def stop_recorder(self, recording=False):
        self.output_video.release()  # make sure the file with the recording will be closed properly
        print(f"Frames read => {self.frames_read} | {self.frames_written} <= Frames written", end='\033[K\n') 
        self.frames_read = 0 # reset the read frames counter    
        self.motionDetected = False # set camera motion detected switch to off
        self.recording_on = False   # set recording switch to off
        self.recording_file_exists = False # set switch on to make new recording file creation possible
        self.recording_elapsed_time = 0  # reset the recording elapsed time to zero  
        self.recording_start_time = 0 # reset the start time the recording  


    def show_frame(self):
        # Display frames in main program
        if self.status:
            the_frame = cv2.resize(self.frame, vsw.dimensions, interpolation=cv2.INTER_AREA)
            cv2.imshow('frame', the_frame)

        # Press Q on keyboard to stop recording
        key = cv2.waitKey(1)
        if key == ord('q'):
            cv2.destroyAllWindows()
            #exit(1)


    def set_output_video_file_name(self, output_video_file_name='output_video.avi'):
        # Save obtained frame into video output file
               # Set the name of the output video file
        self.output_video_file_name = output_video_file_name
        self.output_video = cv2.VideoWriter(self.output_video_file_name, self.codec, cfg.videoFps, (self.frame_width, self.frame_height))
        # print(f"Set video file: {self.output_video_file_name}")


    def AIObjectRecognition(self):
      if vsw.motionDetected:
        self.objectDeltaTime = time.time() - self.lastObjectDetectiontime
        # print(self.objectDeltaTime , '>', self.objectDetectionInterval)
        if self.objectDeltaTime > self.objectDetectionInterval: # every x seconds see cfg.objectDetectionInterval

            the_frame =  self.frame.copy() 
            if cfg.videoScale <= 1.0:   # downscale by configurable factor
              the_frame = cv2.resize(the_frame, vsw.dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
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
                self.lastObjectDetectiontime = time.time()


if __name__ == '__main__':
    print(f"Start of capturing @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 
    rtsp_stream_link = cfg.videoUrl 
    vsw = RTSPVideoWriterObject(rtsp_stream_link) # vsw means videos stream widget

    while True:
      try:
          # Tip see description at the top for explanation

          vsw.ret_message, vsw.cameraMessages = motionDetection()
          #print(vsw.cameraMessages , '\n')
          if vsw.ret_message == 'ok':     
            if vsw.cameraMessages['NotificationMessage'] != []:
              vsw.motionDetected = True
            else:
              vsw.motionDetected = False
          else:  # Server disconnected without sending a response, probably due to no cameraMessages.
            print(f"A check of the camera might be needed!\n{vsw.ret_message}", end='\033[K\n')
            exit(1) 

          # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
          print(f"frame: {vsw.frameCounter:n} prerecorded: {len(vsw.deque_of_frames)} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} motionDetected: {'yes' if vsw.motionDetected else 'no '} => Camera UTC time: {vsw.cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S') if vsw.cameraMessages else 'not available'}", end='\033[K\r') # with output include this \n{vsw.cameraMessages}", end='\033[K\r')  

            
          # simulate a motion detection
          if cfg.RunMotionSimulation_1:
            if 150 <= vsw.frameCounter <= 450: vsw.motionDetected=True
          if cfg.RunMotionSimulation_2:
            if 1050 <= vsw.frameCounter <= 1250: vsw.motionDetected=True

          # If a motion is detected the recording will be switched on and 
          # recording will happen as long as the cfg.recordDuration indicates
          # even if meanwhile no motion has been detected!
          # When de maximum recording time (cfg.recordDuration) is reached the recording will be switch off
          # a recording file will be created at the start of recording and closed(released) when max recording time is reached 
          if vsw.motionDetected:
               if vsw.recording_on == False:  
                  vsw.start_recorder(recording=True)     
  
          
          if vsw.recording_on == True:
              vsw.recording_elapsed_time = (time.time() - vsw.recording_start_time)
              #print(vsw.recording_elapsed_time)
              if vsw.recording_elapsed_time < vsw.recordDuration: 
                if vsw.recording_file_exists == True:  
                    vsw.write_frames()             
              else:
                vsw.stop_recorder(recording = False) # signal recorder to stop recording

          #vsw.show_frame()      # displays a window. use key q to quit, but it will reappear due to loop
          #print(f"{vsw.frameCounter} recording?: {vsw.recording_on}, rec.file?: {vsw.recording_file_exists}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, recording_elapsed_time: {vsw.recording_elapsed_time} < {vsw.recordDuration}?") 

      except Exception as e:
          print(f"error: \n{e}")


