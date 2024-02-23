from astral import LocationInfo
import datetime
from datetime import date
from astral.sun import sun
import pytz
from myMPTapoMotionConfig import cfg

mycity = cfg.mycity
mycountry = cfg.mycountry
mytimezone = cfg.mytimezone
mytown_latitude = cfg.mytown_latitude
mytown_longitude = cfg.mytown_longitude
my_tz_land = pytz.timezone(mytimezone)
today = date.today()
city = LocationInfo(mycity, mycountry, mytimezone, mytown_latitude, mytown_longitude)

mycity = LocationInfo(city)
s = sun(city.observer, date=today, tzinfo=mycity.timezone)
my_dawn    = s["dawn"].astimezone(my_tz_land)
my_sunrise = s["sunrise"].astimezone(my_tz_land)
my_sunset  = s["sunset"].astimezone(my_tz_land)
my_dusk    = s["dusk"].astimezone(my_tz_land)
my_noon    = s["noon"].astimezone(my_tz_land)
#print(
#     f'Dawn/Ochtendgloren   : {my_dawn.strftime("%Y-%m-%d %H:%M:%S")}\n'
#     f'Sunrise/Zonsopkomst  : {my_sunrise.strftime("%Y-%m-%d %H:%M:%S")}\n'
#     f'Noon/Middag          : {my_noon.strftime("%Y-%m-%d %H:%M:%S")}\n'
#     f'Sunset/Zonsondergang : {my_sunset.strftime("%Y-%m-%d %H:%M:%S")}\n'
#     f'Dusk/Schemering      : {my_dusk.strftime("%Y-%m-%d %H:%M:%S")}\n'
#)

#print(f'{my_dawn}\n{my_sunrise}\n{my_sunset}\n{my_dusk}')

confidence_day   = cfg.min_confidence_day
confidence_night = cfg.min_confidence_night
#print(f'confidence_day  : {confidence_day}')
#print(f'confidence_night  : {confidence_night}')
delta_confidence = confidence_day - confidence_night
# DAWN
deltatime_dawn_sunrise = (my_sunrise - my_dawn).total_seconds()
confidence_change_per_second_morning = delta_confidence/deltatime_dawn_sunrise
#print (f'time between dawn and sunrise in seconds: {deltatime_dawn_sunrise:.0f}')
#print(f'confidence_change_per_second: {confidence_change_per_second_morning}')
# DUSK
deltatime_sunset_dusk = (my_dusk - my_sunset).total_seconds()
confidence_change_per_second_evening = delta_confidence/deltatime_sunset_dusk
#print (f'time between sunset and dusk in seconds: {deltatime_sunset_dusk:.0f}')
#print(f'confidence_change_per_second: {confidence_change_per_second_evening}')

def dawn(deltatime_dawn_sunrise, confidence_change_per_second_morning, confidence_day):
  for x, _ in enumerate(range(int(deltatime_dawn_sunrise))):
    changed_confidence = confidence_day - (confidence_change_per_second_morning*x)
    #print (f'{changed_confidence:.4f}')
    #return changed_confidence

def dusk(deltatime_sunset_dusk, confidence_change_per_second_evening, confidence_night):
  for x, _ in enumerate(range(int(deltatime_sunset_dusk))):
    changed_confidence = confidence_night + (confidence_change_per_second_evening*x)
    #print (f'{changed_confidence:.4f}')
    #return changed_confidence

dawn(deltatime_dawn_sunrise, confidence_change_per_second_morning, confidence_day)
#print ('*'*30)
dusk(deltatime_sunset_dusk, confidence_change_per_second_evening, confidence_night)



def get_adapted_confidence(this_time):

    hit_morning =  True if str(my_dawn) < str(this_time)  < str(my_sunrise) else  False

    hit_evening  =  True if str(my_sunset) < str(this_time)  < str(my_dusk) else  False

    hit_day  =  True if str(my_sunrise) < str(this_time)  < str(my_sunset) else  False

    if hit_morning: 
      code = 'M'   
      seconds = (this_time - my_dawn).total_seconds() 
      new_confidence = confidence_night +  ((confidence_change_per_second_morning * (this_time - my_dawn).total_seconds()))
#      print(f'Morning:{hit_morning} new_confidence:{new_confidence} + {this_time.strftime("%Y-%m-%d %H:%M:%S")} - {my_dawn.strftime("%Y-%m-%d %H:%M:%S")}')
    elif hit_evening: 
      code = 'E'
      seconds = (this_time - my_sunset).total_seconds()   
      new_confidence = confidence_day - ((confidence_change_per_second_evening * (this_time - my_sunset).total_seconds()))
#      print(f'Evening:{hit_evening} new_confidence:{new_confidence} - {this_time.strftime("%Y-%m-%d %H:%M:%S")} - {my_sunset.strftime("%Y-%m-%d %H:%M:%S")}')
    elif hit_day:
      code = 'D'
      seconds = 0
      new_confidence = confidence_day
#      print(f'Hit day time confidence: {new_confidence} - {this_time.strftime("%Y-%m-%d %H:%M:%S")}')
    else: #  hit_night:
      code = 'N'
      seconds = 0
      new_confidence = confidence_night
#      print(f'Hit night time confidence: {new_confidence} - {this_time.strftime("%Y-%m-%d %H:%M:%S")}')
#    print (code, new_confidence, seconds, confidence_change_per_second_morning)
    return code, new_confidence, seconds, confidence_change_per_second_morning


