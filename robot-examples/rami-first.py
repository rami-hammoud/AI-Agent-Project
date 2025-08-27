from vilib import Vilib
from time import sleep, time, strftime, localtime
import threading
from os import getlogin
import cv2

USERNAME = getlogin()
PICTURE_PATH = f"/home/{USERNAME}/Pictures/"

flag_face = False
flag_color = False
qr_code_flag = False

MANUAL = '''
Input key to call the function!
    q: Take photo
    1: Color detect : red
    2: Color detect : orange
    3: Color detect : yellow
    4: Color detect : green
    5: Color detect : blue
    6: Color detect : purple
    0: Switch off Color detect
    r: Scan the QR code
    f: Switch ON/OFF face detect
    s: Display detected object information
'''

color_list = ['close', 'red', 'orange', 'yellow',
              'green', 'blue', 'purple']


def face_detect(flag):
    print("Face Detect:" + str(flag))
    Vilib.face_detect_switch(flag)


def qrcode_detect():
    global qr_code_flag
    if qr_code_flag:
        Vilib.qrcode_detect_switch(True)
        print("Waiting for QR code")

    text = None
    while qr_code_flag:
        temp = Vilib.detect_obj_parameter['qr_data']
        if temp != "None" and temp != text:
            text = temp
            print('QR code:%s' % text)
        sleep(0.5)
    Vilib.qrcode_detect_switch(False)


def take_photo():
    _time = strftime('%Y-%m-%d-%H-%M-%S', localtime(time()))
    name = 'photo_%s' % _time
    # Grab a frame directly, fix colors, and save
    frame = Vilib.frame_array()
    if frame is not None:
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(f"{PICTURE_PATH}{name}.jpg", frame_bgr)
        print(f'photo saved as {PICTURE_PATH}{name}.jpg')
    else:
        print("Error: could not capture photo")


def object_show():
    global flag_color, flag_face

    if flag_color:
        if Vilib.detect_obj_parameter['color_n'] == 0:
            print('Color Detect: None')
        else:
            color_coodinate = (Vilib.detect_obj_parameter['color_x'],
                               Vilib.detect_obj_parameter['color_y'])
            color_size = (Vilib.detect_obj_parameter['color_w'],
                          Vilib.detect_obj_parameter['color_h'])
            print("[Color Detect] ", "Coordinate:", color_coodinate, "Size", color_size)

    if flag_face:
        if Vilib.detect_obj_parameter['human_n'] == 0:
            print('Face Detect: None')
        else:
            human_coodinate = (Vilib.detect_obj_parameter['human_x'],
                               Vilib.detect_obj_parameter['human_y'])
            human_size = (Vilib.detect_obj_parameter['human_w'],
                          Vilib.detect_obj_parameter['human_h'])
            print("[Face Detect] ", "Coordinate:", human_coodinate, "Size", human_size)


# 🔧 Fix color swap for local display
def fixed_frame_display(img):
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


# 🔧 Fix color swap for web streaming
def fixed_web_frame(img):
    if img is None:
        return None
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ret, jpeg = cv2.imencode('.jpg', img_bgr)
    if ret:
        return jpeg.tobytes()
    return None


# Apply patches
Vilib.frame_display = fixed_frame_display
Vilib.web_frame_display = fixed_web_frame


def main():
    global flag_face, flag_color, qr_code_flag
    qrcode_thread = None

    Vilib.camera_start(vflip=False, hflip=False)
    Vilib.display(local=True, web=True)   # now uses patched functions
    print(MANUAL)

    while True:
        key = input().lower()

        if key == 'q':
            take_photo()
        elif key in ('0123456'):
            index = int(key)
            if index == 0:
                flag_color = False
                Vilib.color_detect('close')
            else:
                flag_color = True
                Vilib.color_detect(color_list[index])
            print('Color detect : %s' % color_list[index])
        elif key == "f":
            flag_face = not flag_face
            face_detect(flag_face)
        elif key == "r":
            qr_code_flag = not qr_code_flag
            if qr_code_flag:
                if qrcode_thread is None or not qrcode_thread.is_alive():
                    qrcode_thread = threading.Thread(target=qrcode_detect, daemon=True)
                    qrcode_thread.start()
            else:
                if qrcode_thread and qrcode_thread.is_alive():
                    qrcode_thread.join()
                    print('QRcode Detect: close')
        elif key == "s":
            object_show()

        sleep(0.5)


if __name__ == "__main__":
    main()
