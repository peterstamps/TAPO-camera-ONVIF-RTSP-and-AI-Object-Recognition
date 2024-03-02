import cv2
import numpy as np
import time
from datetime import datetime
from collections import deque
import io
import urllib3
import json
import locale
locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')  # prints numbers etc in the Dutch style

############# Settings for BEHAVIOR OF THIS PROGRAM ############# 
# show Window?
showWindow = False
# show Motions on video? Rectangles willl be drawn around area's where motion has been detected
showMotionOnVideo = True
# AI Object Detection installed/ Create pictures when an AI object detection happened
createAIObjectDetectionPictures = True
# set to true to design/create a mask image!
create_mask = False # design/create a mask image


#############  Settings for IP CAMERA ############# 
# IP camera URL
url = "rtsp://<user>:<password>@<IP address camera>:<port>/stream2"  # port 554 for Tapo C225, stream1 or stream 2


#############  Settings for MOTION DETECTION ############# 
# camera warming up time before motion can be detected (to get the frames mask applied and prevent initial recording due to the applied mask  frame differences
warming_up_time = 4 # in seconds
# Thresholds for motion detection
min_contour_area = 450
# Background subtraction method (choose between "KNN" or "MOG2")
background_subtractor_method = "KNN"
# Path to the mask file
mask_path = "/<path_to_mask>/roi_mask.png"
# Record duration in seconds
record_duration = 10
# Time to check for new motion before the end of the set record duration
check_motion_time = 3


#############  Settings for RECORDING OF VIDEO ############# 
# Extra time to add to the record duration if new motion is detected
extra_record_time = 1
# Pre-motion recording duration in seconds
pre_motion_duration = 3
# Output video parameters
output_video_extension = ".avi"
output_video_prefix_name = "output_video_"
output_video_path = "/<path_to_Videos>/"
output_video_full_name = None
frame_width = 640  # default, will be overwritten later on
frame_height = 480 # default, will be overwritten later on
fps = 15  # the frames per second of your camera


#############  Settings for AI OBJECT DETECTION
# used to set motion storage location parameters
output_picture_extension = ".jpg"
output_picture_prefix_name = "output_picture_"
output_picture_path = "./"
output_picture_full_name = None
# used to set AI server related parameters
AIserverInstalled = True # set to False when no AI server is available
AIserverUrl    = "http://<IP_address_of_AI_server:<port>/v1/vision/detection" # port 32168 for CodeProject AI server
AIpictureResolutionFactor = 1.0 # down-scales frames for AI purposes, for stream 1 recommended 0.3 to max 1.0
objectDetectionInterval = 2.0 ## every x seconds when recording is on. TESTED WITH YOLOv5 3.1. USE SMALL MODEL IN CODEPROEJCT AI
font_scale_Label = 0.35 # the font size in the label of the detected object. Font is  cv2.FONT_HERSHEY_SIMPLEX 
colorObjectRectangle = (230, 159, 22) # BGR notation (blue , green, red) ; Code for shade of waterblue => (230, 159, 22) ; code light green => (0, 255, 124)                        
colorLabelRectangle = (230, 159, 22)
colorLabelText = (0,0,0)
min_confidence= 0.4 ##  min_confidence (Float): The minimum confidence level for an object will be detected. In the range 0.0 to 1.0. Default 0.4.
ObjectsToDetect = ("person","bicycle" ,"dog", "cat", "car")  # Must be in a tuple format! Like ("person", "car", "dog", "cat") => Check the AI server models which object are supported


class createMask():
    def __init__(self, cap):
        hasframes, frame = cap.read()
        name = "ROI mask | (r)Rectangles (p)Paint (1-9)Brush size (Right-click)Undo last (Middle-click)Erase all (q)Exit and Save"
        cv2.namedWindow(name,cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(name, self.draw_mask)
        self.rectangles = []
        self.currentRectangle = []
        self.circles = []
        self.draw = False
        self.brush_size = 5
        self.paint_option = 'paint'

        while(True):
            # ROI mask
            frame_mask = frame.copy()
            roi_mask = np.full(frame.shape, 255, dtype="uint8")
        
            # Draw rectangle around ROI
            for rectangle in self.rectangles:
                cv2.rectangle(frame_mask, rectangle[0], rectangle[1], (0,255,0), cv2.FILLED)
                cv2.rectangle(roi_mask, rectangle[0], rectangle[1], (0,0,0), cv2.FILLED)
            # Draw circles from Paint
            for circle in self.circles:
                cv2.circle(frame_mask, circle[0], circle[1], (0,255,0), cv2.FILLED)
                cv2.circle(roi_mask, circle[0], circle[1], (0,0,0), cv2.FILLED)

            cv2.imshow(name, frame_mask)

            # Wait 1ms
            key = chr(cv2.waitKey(1) & 0xFF)
            if( key == 'q' ):
                break
            elif( key == 'r' ):
                  self.paint_option = 'rectangles'
            elif( key == 'p' ):
                  self.paint_option = 'paint'
            elif( key in "123456789" ):
                  self.brush_size = int(key)

        # Save it as image
        if(self.rectangles != [] or self.circles != []):
            roi_mask = cv2.cvtColor(roi_mask, cv2.COLOR_BGR2GRAY)
            mask_filename = f'roi_mask_{cfg.cameraStream}.png'
            cv2.imwrite(mask_filename, roi_mask)

        # Write last mask into archive
        sys.exit(0)

    def draw_mask(self, event, x, y, flags, param):
        if(self.paint_option == 'rectangles'):
            # Record starting (x,y) coordinates on left mouse button click
            if event == cv2.EVENT_LBUTTONDOWN:
                self.currentRectangle = [(x,y)]
            # Record ending (x,y) coordintes on left mouse bottom release
            elif event == cv2.EVENT_LBUTTONUP:
                self.currentRectangle.append((x,y))
                # Add to list
                self.rectangles.append(self.currentRectangle)
            # Right click to empty rectangles
            elif event == cv2.EVENT_MBUTTONDOWN:
                self.rectangles = []
            elif event == cv2.EVENT_RBUTTONDOWN:
                self.rectangles.pop()

        elif(self.paint_option == 'paint'):
            # Record starting (x,y) coordinates on left mouse button click
            if event == cv2.EVENT_LBUTTONDOWN:
                self.draw = True
            # Record ending (x,y) coordinates on left mouse bottom release
            elif event == cv2.EVENT_LBUTTONUP:
                self.draw = False
            # Right click to empty circles
            elif event == cv2.EVENT_MBUTTONDOWN:
                self.circles = []
            # Draw circles on mouse move
            elif event == cv2.EVENT_MOUSEMOVE and self.draw:
                self.circles.append([(x, y), self.brush_size*5])
            elif event == cv2.EVENT_RBUTTONDOWN:
                self.circles.pop()

# Initialize camera
cap = cv2.VideoCapture(url)
if create_mask:
    createMask(cap)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  

# Load the mask
mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
 
# Set the AI picture dimensions
AI_picture_dimensions = (int(frame_width * AIpictureResolutionFactor), int(frame_height * AIpictureResolutionFactor))  

# Initialize background subtractor
if background_subtractor_method == "KNN":
    back_sub = cv2.createBackgroundSubtractorKNN()
else:
    back_sub = cv2.createBackgroundSubtractorMOG2()

# Initialize variables for recording
start_time = None
end_time = None
out = None
frame_buffer = []
max_buffersize = fps * pre_motion_duration
frame_buffer = deque(maxlen=max_buffersize )
recording_on = False
camera_start_time = time.time()
frameCounter = 0
# initialize variables for ObjectDetection
http = urllib3.PoolManager()
lastTimeObjectDetection = 0

print(f"Start of capturing @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 
while True:
    # Read frame from the camera
    ret, frame = cap.read()
    frameCounter += 1
    print(f'@frame: {frameCounter:n}, buffersize: {len(frame_buffer)}', end='\033[K\r')
    if not ret:
        break

    # Resize the mask to match the frame size
    mask_gray_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]))

    # Create a 3-channel mask (BGR) from the grayscale mask
    mask_bgr = cv2.merge([mask_gray_resized, mask_gray_resized, mask_gray_resized])

    # we are not inverting now!
    # Invert the mask so that white areas become non-transparent and black areas remain transparent
    # mask_inverted = cv2.bitwise_not(mask_bgr)

    # Overlay the mask onto the frame
    overlay = cv2.bitwise_and(frame, mask_bgr)
    #background = cv2.bitwise_and(frame, mask_inverted)
    background = cv2.bitwise_and(frame, mask_bgr)
    frame_with_mask_overlay = cv2.add(overlay, background)
    # cv2.imshow('Background', background)
    # Apply background subtraction
    fg_mask = back_sub.apply(frame_with_mask_overlay)
    
    # Apply morphological operations to clean up the mask
    fg_mask = cv2.erode(fg_mask, None, iterations=2)
    fg_mask = cv2.dilate(fg_mask, None, iterations=2)
    # Resize the mask to match the frame size

    # cv2.imshow('Foreground mask', fg_mask)
    # Find contours in the mask
    contours, _ = cv2.findContours(fg_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #if len(contours) > 0:
    #  contours = contours[0] 
    #  contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]     # take the top 5 largest moving objects
      # Check for motion
    motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) < min_contour_area:
            continue
        # warming up time must be passed to allow motion detection    
        if time.time() > camera_start_time  +  warming_up_time:
          motion_detected = True
          print(f'Motion detected @ {datetime.now().strftime("%Y-%m-%d_%H:%M:%S")} contour area size: {cv2.contourArea(contour):.2f}', end='\033[K\r')
        if showMotionOnVideo:
          # Motion detected, do something
          (x, y, w, h) = cv2.boundingRect(contour)
          cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)   
  #      break
        
    # Keep frames x seonds before a motion is detected
    # Add only a frame to the buffer when recording is off else frames will be directly written
    # When max_buffersize has been reached the first frame will be dropped according to FiFo: First in First Out
    if not recording_on:
      frame_buffer.append(frame.copy())
      
    
    # If motion detected, start recording and write first the buffered frames
    if motion_detected:
        recording_on = True
        if start_time is None:
            start_time = time.time()
            end_time = start_time + record_duration
            #print('start_time is None', end_time, start_time , record_duration)
            # Define the codec and create VideoWriter object
            output_video_full_name = f'{output_video_path}{output_video_prefix_name}{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}{output_video_extension}'
            out = cv2.VideoWriter(output_video_full_name, cv2.VideoWriter_fourcc(*'H264'), fps, (frame_width, frame_height))
            # Write frames from buffer to the output video file
            if len(frame_buffer) > 0:
                n = 0
                for buf_frame in frame_buffer:
                    n += 1
                    out.write(buf_frame)
                # Clear the frame buffer
                frame_buffer.clear()   
                #print(f'{n} frames have been written from buffer', end='\n') 
        else:
            if time.time() > end_time - check_motion_time:
              end_time += extra_record_time
            #print('start_time is NOT None', end_time, start_time , record_duration, extra_record_time)
    
    # Check if it's time to stop recording
    if start_time is not None and time.time() >= end_time:
        #print('REC', end_time, start_time , record_duration)
        print(f"Recording stopped created: {output_video_full_name}", end='\n')
        start_time = None
        end_time = None
        recording_on = False
        if out is not None:
            # Release the VideoWriter object
            out.release()
            out = None

    # Write frame to the output video
    if out is not None:
        out.write(frame)

    if recording_on and createAIObjectDetectionPictures:
      objectDeltaTime = time.time() - lastTimeObjectDetection
      #print(objectDeltaTime , '>', objectDetectionInterval)
      if objectDeltaTime > objectDetectionInterval: # every x seconds see objectDetectionInterval
          the_frame =  frame.copy()
          if AIpictureResolutionFactor < 1.0:   # scale by configurable factor
            the_frame = cv2.resize(the_frame, AI_picture_dimensions, interpolation=cv2.INTER_AREA)  # rescaling using OpenCV
          is_success, buffer = cv2.imencode(".jpg", the_frame)
          io_buf = io.BytesIO(buffer)
          response = http.request_encode_body(
              'POST',
              AIserverUrl,  headers=None, encode_multipart=True, multipart_boundary=None,
              fields = {'min_confidence': f'{min_confidence}', 'typedfile': (f"output_picture.jpg", io_buf.getbuffer(),'image/jpg'),}   #open(image_path,"rb").read(),'image/jpg'),}
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
                      lastTimeObjectDetection = time.time()
                      labels = []
                      for object in res["predictions"]:
                          #print(object) #["label"])
                          label = object["label"]  
                          confidence = object["confidence"]  
                          label_confidence = f'{label}-{(confidence*100.0):.01f}%'                            
                          if label in ObjectsToDetect: # we capture picture(s) only for these objects see myTapoMotionConfig.py file
                            object_rect_line_thickness = 1 # line thickness around detected object   
                            font_scale = font_scale_Label
                            (text_width, text_height) = cv2.getTextSize(label_confidence, cv2.FONT_HERSHEY_SIMPLEX, font_scale, object_rect_line_thickness)[0]
                            # set the text color (foreground) 
                            text_thickness = 0 #  thickness of the text in the box
                            # set the text color (foreground) 
                            text_color = colorLabelText # black or white are usual colors
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
                            cv2.rectangle(the_frame, box_coords[0], box_coords[1], colorLabelRectangle, -1)     # light green color = (0, 255, 124), lightblue = (0, 190, 255)
                            # linestypes: Filled=cv2.FILLED, 4-connected=line LINE_4 cv2.LINE_4 8-connected line=cv2.LINE_8, antialiased line=cv2.LINE_AA
                            # put text the filled label box
                            cv2.putText(the_frame, label_confidence, (startX, bottom_line_labelbox ), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, text_thickness, cv2.LINE_AA)                                                                                        
                            # draw the boax around the detected object
                            cv2.rectangle(the_frame, (startX - object_rect_line_thickness, startY + object_rect_line_thickness), (endX + object_rect_line_thickness, endY + 2*(object_rect_line_thickness)), colorObjectRectangle , object_rect_line_thickness)
                            output_picture_full_name = f'{output_picture_path}{output_picture_prefix_name}{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}_{object["label"]}{output_picture_extension}'
                            cv2.imwrite(f'{output_picture_full_name}', the_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                                    
                            # print(f" .......", end='\033[K\r') # cleans the whole line but no new line 
                            print(f"{output_picture_full_name} - objectDetected: {object['label']}", end='\033[K\n') 

                            #break # with break active only one image will be created per detection round
                              
                  elif "message" in res:
                      print(res["message"])
                  elif "error" in res:
                      print(res["error"])
                  else:
                      pass


        
    frame = cv2.resize(frame.copy(), (int(frame_width*0.75), int(frame_height*0.75)), interpolation=cv2.INTER_AREA)  # rescaling using OpenCV

    # Display the resulting frame
    if showWindow:
      cv2.imshow('Motion Detection YES', frame)
      
      # Check for key press to exit
      if cv2.waitKey(1) & 0xFF == ord('q'):
          break

# Release the camera and close all windows
cap.release()
cv2.destroyAllWindows()
