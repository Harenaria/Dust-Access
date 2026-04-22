import subprocess
import time
import os
import sys
import shutil

def clean_up():
    print("--- Cleaning logs and caches ---")
    log_dir = ".runlogs"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir)
    
    # Optional: clean __pycache__
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))

def run_all():
    clean_up()
    
    # Use 'poetry run' to call the scripts defined in pyproject.toml
    # This works on both Windows and Linux
    
    print("--- Starting Server ---")
    with open(".runlogs/server.log", "w") as f:
        server_proc = subprocess.Popen(["poetry", "run", "server"], 
                                      stdout=f, stderr=subprocess.STDOUT)
    
    time.sleep(3)
    
    print("--- Starting Clients ---")
    with open(".runlogs/client1.log", "w") as f1, open(".runlogs/client2.log", "w") as f2:
        client1_proc = subprocess.Popen(["poetry", "run", "client"], 
                                       stdout=f1, stderr=subprocess.STDOUT)
        time.sleep(1)
        client2_proc = subprocess.Popen(["poetry", "run", "client"], 
                                       stdout=f2, stderr=subprocess.STDOUT)
    
    print("--- System Running ---")
    print("Logs are in .runlogs/")
    print("Press Ctrl+C to stop everything.")
    
    try:
        while True:
            time.sleep(1)
            if server_proc.poll() is not None:
                print("Server stopped.")
                break
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server_proc.terminate()
        client1_proc.terminate()
        client2_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    run_all()
