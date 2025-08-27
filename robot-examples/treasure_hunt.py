from picrawler import Picrawler
from time import sleep
from robot_hat import Music,TTS
from vilib import Vilib
import readchar
import random
import threading

crawler = Picrawler()


music = Music()
tts = TTS()

manual = '''
Press keys on keyboard to control Picrawler!
    w: Forward
    a: Turn left
    s: Backward
    d: Turn right
    space: Say the target again
    Ctrl^C: Quit
'''

color = "red"
color_list=["red","orange","yellow","green","blue","purple"]
key_dict = {
    'w': 'forward',
    's': 'backward',
    'a': 'turn_left',
    'd': 'turn_right',
}
def renew_color_detect():
    global color
    color = random.choice(color_list)
    Vilib.color_detect(color)
    tts.say("Look for " + color)

key = None
lock = threading.Lock()
def key_scan_thread():
    global key
    while True:
        key_temp = readchar.readkey()
        print('\r',end='')
        with lock:
            key = key_temp.lower()
            if key == readchar.key.SPACE:
                key = 'space'
            elif key == readchar.key.CTRL_C:
                key = 'quit'
                break
        sleep(0.01)

def main():
    global key
    action = None
    Vilib.camera_start(vflip=False,hflip=False)
    Vilib.display(local=False,web=True)
    sleep(0.8)
    speed = 80
    print(manual)

    sleep(1)
    _key_t = threading.Thread(target=key_scan_thread)
    _key_t.setDaemon(True)
    _key_t.start()

    tts.say("game start")
    sleep(0.05)   
    renew_color_detect()
    while True:

        if Vilib.detect_obj_parameter['color_n']!=0 and Vilib.detect_obj_parameter['color_w']>100:
            tts.say("will done")
            sleep(0.05)   
            renew_color_detect()

        with lock:
            if key != None and key in ('wsad'):
                action = key_dict[str(key)]
                key =  None
            elif key == 'space':
                tts.say("Look for " + color)
                key =  None
            elif key == 'quit':
                _key_t.join()
                Vilib.camera_close()
                print("\n\rQuit") 
                break 

        if action != None:
            crawler.do_action(action,1,speed)  
            action = None

        sleep(0.05)          
     

if __name__ == "__main__":
    main()

