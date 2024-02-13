# SEE DESCRIPTION IN myTapoVideoCapture and myTapoMotionConfig as well
#
from myTapoMotionConfig import cfg
import asyncio
import datetime as dt
import logging
from datetime import datetime, timedelta
from pytz import UTC
from zeep import xsd
from typing import Any, Callable
from onvif import ONVIFCamera

if cfg.cameraLogMessages.lower()  == "debug":
  logging.getLogger("zeep").setLevel(logging.DEBUG)
  logging.getLogger("httpx").setLevel(logging.DEBUG)
elif cfg.cameraLogMessages.lower()  == "info":
  logging.getLogger("zeep").setLevel(logging.INFO)
  logging.getLogger("httpx").setLevel(logging.INFO)
elif cfg.cameraLogMessages.lower() == "critical":
  logging.getLogger("zeep").setLevel(logging.CRITICAL)
  logging.getLogger("httpx").setLevel(logging.CRITICAL)


async def myTapo(continuously=False):
###  lines marked with ###  have been tested and are working fine, but not needed here  
  mycam = ONVIFCamera(
      cfg.cameraIP,
      int(cfg.cameraOnvifPort) ,
      cfg.cameraUser,
      cfg.cameraPassw,  
      cfg.cameraOnvif_wsdl_dir,
      )
  # Update xaddrs for services 
  await mycam.update_xaddrs() 
  
###  # Get the capabilities of the camera
###   capabilities = await mycam.get_capabilities()
###   for capability in capabilities:
###    print(f"\ncapability: {capability}")  
    
  # Create a pullpoint manager. 
  interval_time = (dt.timedelta(seconds=60))
  pullpoint_mngr = await mycam.create_pullpoint_manager(interval_time, subscription_lost_callback = Callable[[], None],)
###  print (f"pullpoint_mngr: {pullpoint_mngr}")  # returns pullpoint_mngr: <onvif.managers.PullPointManager object>
  
  # create the subscription 
  subscription = await mycam.create_subscription_service("PullPointSubscription")
### print(f"subscription: {subscription}")  print(f"subscription: {subscription}")

  # create the pullpoint  
  pullpoint = await mycam.create_pullpoint_service()
  
  # call SetSynchronizationPoint to generate a notification message too ensure the webhooks are working.
  await pullpoint.SetSynchronizationPoint()
 
  # pull the cameraMessages from the camera, set the request parameters
  # by setting the pullpoint_req.Timeout you define the refreshment speed of the pulls
  pullpoint_req = pullpoint.create_type('PullMessages') 
  pullpoint_req.MessageLimit=100
  pullpoint_req.Timeout = (dt.timedelta(days=0,hours=0,seconds=1))
  if continuously == True:
    while True:
      # START here we could loop endless over the cameraMessages with --> while True: and print(cameraMessages) at the end of while loop
      cameraMessages = await pullpoint.PullMessages(pullpoint_req)
      #print(cameraMessages)
      # renew the subscription makes sense when looping over 
      termination_time = (
         (dt.datetime.utcnow() + dt.timedelta(days=1,hours=1,seconds=3))
            .isoformat(timespec="seconds").replace("+00:00", "Z")
        )  
      # Only use this line in a while loop: await subscription.Renew(termination_time)
      # END here we could loop endless over the cameraMessages with --> while True:  and print(cameraMessages) at the end of while loop
  else:
      # START here we could loop endless over the cameraMessages with --> while True: and print(cameraMessages) at the end of while loop
      cameraMessages = await pullpoint.PullMessages(pullpoint_req)
      # print(cameraMessages)
      # renew the subscription makes sense when looping over 
      termination_time = (
         (dt.datetime.utcnow() + dt.timedelta(days=1,hours=1,seconds=3))
            .isoformat(timespec="seconds").replace("+00:00", "Z")
        )  
      # Only use this line in a while loop: await subscription.Renew(termination_time)
      # END here we could loop endless over the cameraMessages with --> while True:  and print(cameraMessages) at the end of while loop    
      # we close the pullpoint . This makes sense when no While loop is used  
      await pullpoint.close()
      await mycam.close()  
      return cameraMessages

def motionDetection():
  while True: 

    loop = asyncio.get_event_loop()
    cameraMessages = loop.run_until_complete(myTapo(continuously=False))
    ret_message = "ok"
  #  except Exception as err:
  #    cameraMessages = []
  #    ret_message = "Server disconnected without sending a response, probably due to no cameraMessages."
    return ret_message, cameraMessages




if __name__ == "__main__":
  prt = True
  motionDetected=False
  prtline0 = ''
  prtline1 = "="*48
  prtline2 = "- -"*16  
  now = datetime.now()   
  while True:
    ret_message, cameraMessages = motionDetection()
    now2 = datetime.now()
    time_passed_seconds = now2 - now
    if prt: print(f"Passed time in total seconds: {time_passed_seconds}")        
    if cameraMessages:
      if prt: print (f"{prtline1}\nCamera Current Time: {cameraMessages['CurrentTime'].strftime('%Y-%m-%d %H:%M:%S')}\n{prtline0}", end='')
      if cameraMessages['NotificationMessage'] != []:
        motionDetected = True
        ret_message = cameraMessages['NotificationMessage']
        if prt: print (f"{prtline2}\n{cameraMessages['NotificationMessage']}\n{prtline0}", end='')
      else:
        motionDetected = False
        ret_message = "No Notification received"   
        if prt: print(f"{prtline2}\n{ret_message}\n", end='') 
    else:
      ret_message = "No cameraMessages received" 
      if prt: print(f"{prtline2}\n{ret_message}\n", end='')    
    #except Exception as err:
      ret_message = "Server disconnected without sending a response."
      #if prt: print(f"Error: {err}\n{ret_message}")      

   # if prt: print (f"{prtline2}\n{cameraMessages}\n{prtline1}")    


