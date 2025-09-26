# This file is for initiating a hard shutdown. You must log a critical error before using this file.
import os
import psutil


def hard():
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'gunicorn' and proc.info['pid'] != current_pid:
            try:
                os.kill(proc.info['pid'], 15) # SIGTERM
            except OSError as e:
                print(f"Error terminating process {proc.info['pid']}: {e}")
    
    os.kill(current_pid, 15) # SIGTERM