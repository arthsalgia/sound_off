#!/usr/bin/python3
import os, errno
import pyaudio
import spl_lib as spl
from scipy.signal import lfilter
import numpy
import geocoder
from datetime import datetime
import influxdb_client, time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

#-----------------
# configuration 
#-----------------
token = os.environ.get("INFLUXDB_TOKEN")
org = "salgia"
url = "http://localhost:8086"
bucket="sound_off"
measurement = "sound"
src = "src"
lat = "lat"
lng = "lng"
deviceName = "arthsiMac"
dbA = "dbA"
logFileLocation = "sound_off.line"
RATES = [44300, 48000] # Different mics have different rates. For example, Logitech HD 720p has rate 48000Hz
''' The following is similar to a basic CD quality
   When CHUNK size is 4096 it routinely throws an IOError.
   When it is set to 8192 it doesn't.
   IOError happens due to the small CHUNK size
   What is CHUNK? Let's say CHUNK = 4096
   math.pow(2, 12) => RATE / CHUNK = 100ms = 0.1 sec
'''
CHUNKS = [4096, 9600]       # Use what you need


#---------------------
# initialize globals
#---------------------
new_decibel = 0   # newly measured dbA
logFile = None    # file handle for logging data
pa  = None # pyAudio object
FORMAT = pyaudio.paInt16    # 16 bit
CHANNEL = 1    # 1 means mono. If stereo, put 2
CHUNK = CHUNKS[1]
NUMERATOR = 0
DENOMINATOR = 1
myLat = None
myLong = None
audioStream = None  # the audio stream
influxDb = None # the connection object to influxDb
LOG_TO_FILE = False  # controls whether we log data to file
RECORD_TO_INFLUXDB = True # controls whether to write to influxdb
token = os.environ.get("INFLUXDB_TOKEN")
org = "salgia"
url = "http://localhost:8086"

#---------------------
# initialize resources
#---------------------
def initialize():
    # first, create PyAudio object
    global pa 
    pa = pyaudio.PyAudio()
    rate = RATES[1]
    #rate = int(pa.get_default_input_device_info()['defaultSampleRate'])
    global NUMERATOR, DENOMINATOR
    NUMERATOR, DENOMINATOR = spl.A_weighting(rate)
    
    # now, listen to mic
    global audioStream
    audioStream = pa.open(format = FORMAT,
                channels = CHANNEL,
                rate = rate,
                input = True,
                frames_per_buffer = CHUNK)


    # fetch current location 
    g = geocoder.ip('me')
    global myLat, myLong
    myLat = str(g.latlng[0])
    myLong = str(g.latlng[1])
    

    if LOG_TO_FILE:
        # open the logfile
        global logFile
        logFile = open(logFileLocation, "a")
    
    if RECORD_TO_INFLUXDB:
        #TODO: create the influx client object
        global influxDb
        influxDb = influxdb_client.InfluxDBClient(url=url, token=token, org=org)



#------------------------------------
# record_sound: records the dbA
# and time to logFile and influxDb
#------------------------------------
def record_sound(dba):

    # get time since epoch
    dt = datetime.now()
    unix_time = round(dt.timestamp())  # round off to seconds
    unix_time = str(unix_time)
    #dba = str(dba)

    # either write the data to a flat file by calling the record_to_file()
    # or to influxdb by calling that func or any other function

    if RECORD_TO_INFLUXDB:
        #write to influx db using python client api
        write_api = influxDb.write_api(write_options=SYNCHRONOUS)
        p = influxdb_client.Point(measurement).tag(src, deviceName).tag(lat, myLat).tag(lng, myLong).field(dbA, dba)
        write_api.write(bucket=bucket, org=org, record=p)



    if LOG_TO_FILE:
        data = measurement + "," + src + "=" + deviceName + "," + \
            lat + "=" + myLat + "," + lng + "=" + myLong + \
            " " + dbA + "=" + str(dba) + " " + unix_time + "\n"
        logFile.writelines(data)
        logFile.flush()


# ignore db changes less than 1
def is_meaningful(old, new):
    #TODO: fix problem of multiple readings per second
    return abs(old - new) > 1

#----------------------------------------------------------------
# listen:  blocking call to read audio, process and write to db
#----------------------------------------------------------------
def listen(old=0, error_count=0, min_decibel=100, max_decibel=0):
    print("Listening")
    while True:
        try:
            ## read() returns string. You need to decode it into an array later.
            block = audioStream.read(CHUNK, exception_on_overflow=False)
        except IOError as e:
            error_count += 1
            print(" (%d) Error recording: %s" % (error_count, e))
        else:
            ## Int16 is a numpy data type which is Integer (-32768 to 32767)
            ## If you put Int8 or Int32, the result numbers will be ridiculous
            decoded_block = numpy.frombuffer(block, numpy.int16)
            ## This is where you apply A-weighted filter
            y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
            new_decibel = 20*numpy.log10(spl.rms_flat(y))
            if is_meaningful(old, new_decibel):
                old = new_decibel
                new_decibel = int(new_decibel)
                record_sound(new_decibel)
                print('A-weighted: {:+.2f} dB'.format(new_decibel))


#-------------------------------
# main entry point 
#-------------------------------
initialize()
listen()
audioStream.stop_stream()
audioStream.close()
if LOG_TO_FILE:
    logFile.close()
pa.terminate()

    
