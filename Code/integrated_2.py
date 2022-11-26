import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from firebase_admin import db
import serial
import time
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming  
import io 
import picamera 
import logging 
import socketserver 
from threading import Condition 
from http import server
import Adafruit_DHT
from mpu6050 import mpu6050
import RPi.GPIO as GPIO


trial = "france"
 
PAGE="""\ 
<html> 
<head> 
<title>Raspberry Pi - Surveillance Camera</title> 
</head> 
<body> 
<center><img src="stream.mjpg" width="640" height="480"></center>
</body> 
</html> 
""" 

mpu = mpu6050(0x68) 

GPIO.setwarnings(False)

#GPIO Pins Buzzer
buzzPin =22

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

#GPIO Pins(Straight)
GPIO_TRIGGER_ST = 18
GPIO_ECHO_ST = 24

#GPIO Pins(Right)
GPIO_TRIGGER_RI = 20
GPIO_ECHO_RI = 21

#GPIO Pins(Left)
GPIO_TRIGGER_LE = 5
GPIO_ECHO_LE = 6

#GPIO Pins(Back)
GPIO_TRIGGER_BK = 7
GPIO_ECHO_BK = 8

GPIO.setup(buzzPin, GPIO.OUT)

GPIO.setup(GPIO_TRIGGER_BK, GPIO.OUT)
GPIO.setup(GPIO_ECHO_BK, GPIO.IN)

#GPIO Pin (IN / OUT)
GPIO.setup(GPIO_TRIGGER_ST, GPIO.OUT)
GPIO.setup(GPIO_ECHO_ST, GPIO.IN)

GPIO.setup(GPIO_TRIGGER_RI, GPIO.OUT)
GPIO.setup(GPIO_ECHO_RI, GPIO.IN)

GPIO.setup(GPIO_TRIGGER_LE, GPIO.OUT)
GPIO.setup(GPIO_ECHO_LE, GPIO.IN)

aqi=""
flag=0

arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=.1)
def write_read(x):
    print(x)
    arduino.write(bytes(x, 'utf-8'))
    time.sleep(0.05)
    data = arduino.readline()
    return data

# Fetch the service account key JSON file contents
cred = credentials.Certificate('fyp1-86727-firebase-adminsdk-hbuz9-8abb2d102c.json')

def listener(event):
    global flag
    global aqi
    #print(event.event_type)  # can be 'put' or 'patch'
    temp=str(event.path)
    temp=temp.split("/")
    #print(event.path)  # relative to the reference, it seems
    #print(event.data)  # new data at /reference/event.path. None if deleted
    val=str(event.data)
    if val=="1":
        if temp[1]=="Left":
            dir = "4"
            value = write_read(dir)
            aqi=value[3]
            print(value)
            print('moving left!')
        elif temp[1]=="Right":
            dir = "3"
            value = write_read(dir)
            aqi=value[2]
            print(value)
            print('moving right!')
        elif temp[1]=="Backward":
            dir = "2"
            value = write_read(dir)
            aqi=value[2]
            print(value)
            print('moving backward!')
        elif temp[1]=="Forward":
            dir = "1"
            value = write_read(dir)
            aqi=value[3]
            print(value)
            print('moving forward!')
        elif temp[1]=="Self":
            move(0)
            users_ref = ref1.child('Self')
            users_ref.set({'Self':0})
                
        distStraight = distance_straight()
        print ("Straight Distance = %.1f cm" % distStraight)
        distRight = distance_right()
        print ("Right Distance = %.1f cm" % distRight)
        distLeft = distance_left()
        print ("Left Distance = %.1f cm" % distLeft)
        distBack = distance_back()
        print ("Back Distance = %.1f cm" % distBack) 
        if flag%30 == 0:
            humidity, temperature = Adafruit_DHT.read_retry(11, 17)
            print('Temp: {0:0.1f} C  Humidity: {1:0.1f} %'.format(temperature, humidity))
            save_temp(temperature)
            save_hum(humidity)
            save_aqi(aqi)
        print("")
        flag += 1
        gyro_data = mpu.get_gyro_data() 
        # print("Gyro X : "+str(gyro_data['x'])) 
        # print("Gyro Y : "+str(gyro_data['y'])) 
        print("Gyro Z : "+str(gyro_data['z'])) 
        print(aqi) 
        print("-------------------------------")
        save_frontdist(distStraight)
        save_revdist(distBack)
        save_gyro(gyro_data['z'])
        
    if val=="0":
        dir = "0"
        value = write_read(dir)
        aqi=value[2]
        print(value)
        print('not moving!')
        
    # print("Temp : "+str(mpu.get_temp())) 
    # print() 

    # accel_data = mpu.get_accel_data() 
    # print("Acc X : "+str(accel_data['x'])) 
    # print("Acc Y : "+str(accel_data['y'])) 
    # print("Acc Z : "+str(accel_data['z'])) 
    # print() 


# firebase_admin.db.reference('https://fyp1-86727-default-rtdb.firebaseio.com').listen(listener)
# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://fyp1-86727-default-rtdb.firebaseio.com'
})

# As an admin, the app has access to read and write all data, regradless of Security Rules
ref=firebase_admin.db.reference('').listen(listener)
# ref = db.reference('')
# print(ref)

ref1=firebase_admin.db.reference('')
#db1=firestore.client()

def save_frontdist(fdist):
    users_ref = ref1.child('Front Distance')
    users_ref.set({'Front Distance':fdist})

def save_revdist(revdist):
    users_ref = ref1.child('Back Distance')
    users_ref.set({'Back Distance':revdist})

def save_gyro(gyro):
    users_ref = ref1.child('Gyro')
    users_ref.set({'Gyro':gyro})

def save_temp(temp):
    users_ref = ref1.child('Temperature')
    users_ref.set({'Temperature':temp})
    
def save_hum(hum):
    users_ref = ref1.child('Humidity')
    users_ref.set({'Humidity':hum})

def save_aqi(aqi):
    users_ref = ref1.child('Air Quality')
    users_ref.set({'Air Quality':aqi})

def distance_straight():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER_ST, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER_ST, False)

    StartTime_S = time.time()
    StopTime_S = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO_ST) == 0:
        StartTime_S = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO_ST) == 1:
        StopTime_S = time.time()

    # time difference between start and arrival
    TimeElapsed_S = StopTime_S - StartTime_S
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance_st = (TimeElapsed_S * 34300) / 2

    return distance_st

def distance_right():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER_RI, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER_RI, False)

    StartTime_R = time.time()
    StopTime_R = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO_RI) == 0:
        StartTime_R = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO_RI) == 1:
        StopTime_R = time.time()

    # time difference between start and arrival
    TimeElapsed_R = StopTime_R - StartTime_R
    
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance_r = (TimeElapsed_R * 34300) / 2

    return distance_r

def distance_back():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER_BK, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER_BK, False)

    StartTime_B = time.time()
    StopTime_B = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO_BK) == 0:
        StartTime_B = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO_BK) == 1:
        StopTime_B = time.time()

    # time difference between start and arrival
    TimeElapsed_B = StopTime_B - StartTime_B
    
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance_b = (TimeElapsed_B * 34300) / 2

    return distance_b

def distance_left():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER_LE, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER_LE, False)

    StartTime_L = time.time()
    StopTime_L = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO_LE) == 0:
        StartTime_L = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO_LE) == 1:
        StopTime_L = time.time()

    # time difference between start and arrival
    TimeElapsed_L = StopTime_L - StartTime_L
    
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance_l = (TimeElapsed_L * 34300) / 2

    return distance_l

def stop():
    dir = "0"
    value = write_read(dir)
    print(value)
    print('not moving!')

def auto_move_left():
    t1=int(60-time.time()%60)
    temp=int(60-time.time()%60)
    while t1-temp!=1:
        temp=int(60-time.time()%60)
        dir = "4"
        value = write_read(dir)
        print(value)
        print('moving left!')
    stop()

def auto_move_right():
    t1=int(60-time.time()%60)
    temp=int(60-time.time()%60)
    while t1-temp!=1:
        temp=int(60-time.time()%60)
        dir = "3"
        value = write_read(dir)
        print(value)
        print('moving right!')
    stop()

def auto_move_forward():
    t1=int(60-time.time()%60)
    temp=int(60-time.time()%60)
    while t1-temp!=1:
        temp=int(60-time.time()%60)
        dir = "1"
        value = write_read(dir)
        print(value)
        print('moving forward!')
    stop()

def move(i):
    try:
        distStraight = distance_straight()
        print ("Straight Distance = %.1f cm" % distStraight)
        distRight = distance_right()
        print ("Right Distance = %.1f cm" % distRight)
        distLeft = distance_left()
        print ("Left Distance = %.1f cm" % distLeft)
        if distStraight<=20:
            if distRight>20:
                auto_move_right()
            elif distLeft>20:
                auto_move_left()
            else:
                auto_move_right()
        elif distLeft<=20:
            auto_move_right()
        elif distRight<=20:
            auto_move_left()
        elif distStraight > 20 and distRight > 20 and distLeft > 20:
            auto_move_forward()
        else:
            stop()
        time.sleep(2)
        if i<10:
            i+=1
            print(i)
        else:
            return 1
        move(i)
    finally:
        stop()

class StreamingOutput(object): 
    def __init__(self): 
        self.frame = None 
        self.buffer = io.BytesIO() 
        self.condition = Condition() 
 
    def write(self, buf): 
        if buf.startswith(b'\xff\xd8'): 
            # New frame, copy the existing buffer's content and notify all 
            # clients it's available 
            self.buffer.truncate() 
            with self.condition: 
                self.frame = self.buffer.getvalue() 
                self.condition.notify_all() 
            self.buffer.seek(0) 
        return self.buffer.write(buf) 
 
class StreamingHandler(server.BaseHTTPRequestHandler): 
    def do_GET(self): 
        if self.path == '/': 
            self.send_response(301) 
            self.send_header('Location', '/index.html') 
            self.end_headers() 
        elif self.path == '/index.html': 
            content = PAGE.encode('utf-8')
            self.send_response(200) 
            self.send_header('Content-Type', 'text/html') 
            self.send_header('Content-Length', len(content)) 
            self.end_headers() 
            self.wfile.write(content) 
        elif self.path == '/stream.mjpg': 
            self.send_response(200) 
            self.send_header('Age', 0) 
            self.send_header('Cache-Control', 'no-cache, private') 
            self.send_header('Pragma', 'no-cache') 
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME') 
            self.end_headers() 
            try: 
                while True: 
                    with output.condition: 
                        output.condition.wait() 
                        frame = output.frame 
                    self.wfile.write(b'--FRAME\r\n') 
                    self.send_header('Content-Type', 'image/jpeg') 
                    self.send_header('Content-Length', len(frame)) 
                    self.end_headers() 
                    self.wfile.write(frame) 
                    self.wfile.write(b'\r\n') 
            except Exception as e: 
                logging.warning( 
                    'Removed streaming client %s: %s', 
                    self.client_address, str(e)) 
        else: 
            self.send_error(404) 
            self.end_headers() 
 
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer): 
    allow_reuse_address = True 
    daemon_threads = True 
 

with picamera.PiCamera(resolution='640x480', framerate=24) as camera: 
    output = StreamingOutput() 
    #Uncomment the next line to change your Pi's Camera rotation (in degrees) 
    camera.rotation = 180 
    camera.start_recording(output, format='mjpeg') 
    try: 
        address = ('', 8000) 
        server = StreamingServer(address, StreamingHandler) 
        server.serve_forever()
    except:
        camera.stop_recording() 
    finally:
        camera.stop_recording()
