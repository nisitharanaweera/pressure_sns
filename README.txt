Modbus Pressure Sensor UI - User Manual
=======================================

Overview:
---------
This software provides a graphical interface to read pressure values from Modbus RTU sensors via a serial port. It allows you to select COM port, baud rate, sensor addresses, and read pressure values either once or repeatedly.

How to Use:
-----------
1. Launch the application:
   - If packaged, double-click the .exe file in the 'dist' folder.
   - If running from source, use Python 3.13 and run 'presense.py'.

2. Select COM Port:
   - Use the dropdown to choose the correct serial port (e.g., COM3).
   - Click the refresh icon (↻) to update the port list if needed.

3. Set Baud Rate:
   - Choose the baud rate matching your sensor (default is 9600).

4. Set Sensor Addresses:
   - Use the spinboxes to set Modbus addresses for Sensor 1 and Sensor 2 (default: 1 and 2).
   - Only numbers between 1 and 247 are allowed.

5. Connect/Disconnect:
   - Click the chain icon (🔗) to connect to the selected port.
   - Once connected, the icon changes (⛓); click again to disconnect.
   - COM port and baud rate are locked while connected.

6. Read Pressure:
   - Click 'Read Once' to read both sensors.
   - Pressure values are shown next to each sensor.
   - Status indicator (colored dot, top right) shows:
     - Gray: Idle
     - Orange: Ongoing
     - Green: Success
     - Red: Error

7. Repeat Read:
   - Set the interval (seconds) in the entry box (default: 2).
   - Click 'Repeat Read' to start automatic reading.
   - Click 'Stop' to end repeat mode.
   - Interval and sensor address fields are locked during repeat.

8. Exiting:
   - Close the window or click the close button; the app will disconnect and exit.

Troubleshooting:
----------------
- If you see errors, check COM port, baud rate, and sensor addresses.
- Ensure sensors are powered and connected.
- Use the refresh button to update port list.

Requirements:
-------------
- Windows PC
- Python 3.13 (if running from source)
- pyserial package

Packaging:
----------
- To create a standalone .exe, use PyInstaller:
  pyinstaller --onefile --windowed presense.py
- The .exe will be in the 'dist' folder.

Contact:
--------
For support or questions, contact your software provider or developer.
