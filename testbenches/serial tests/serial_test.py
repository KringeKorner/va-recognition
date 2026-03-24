import serial
import serial.tools.list_ports
import random
import time

# List available ports
ports = serial.tools.list_ports.comports()
for port in ports:
    print(port.device, port.description)

PORT = "COM11"
# PORT = "COM4"
BAUD = 115200

# Open serial port
ser = serial.Serial(PORT, BAUD, timeout=1)

# Reset Arduino
time.sleep(2)
ser.setDTR(False)
time.sleep(1)
ser.reset_input_buffer()
ser.reset_output_buffer()
ser.setDTR(True)
print("ONLINE")

try:
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            print("ARDUINO:", line)
        if line == "READY":
            src = random.randint(0, 3)
            if src == 0:
                mood = 0
            else:
                mood = random.randint(1, 7)
            print("Sending:", src, mood)
            ser.write(bytes([src, mood]))
except KeyboardInterrupt:
    print("SHUTTING DOWN")
finally:
    ser.close()