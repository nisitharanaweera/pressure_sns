Modbus Multi-Sensor Tool - User Manual
======================================

Overview:
---------
This tool supports multiple Modbus sensors with different register maps, slave IDs, and communication settings. It reads sns_details.json for configuration and creates a tab for each sensor.

How to Use:
-----------
1. Launch the application:
   - If packaged, double-click the .exe file (after packaging modbus_multiui.py).
   - If running from source, use Python 3.13 and run 'modbus_multiui.py'.

2. Select the sensor tab:
   - Each tab represents a different sensor type.
   - The tab name matches the sensor's short name or model.

3. Set COM Port, Baudrate, Slave ID:
   - Choose the correct COM port and baudrate for your sensor.
   - Adjust Slave ID if needed.

4. Read Sensor Values:
   - Click 'Read Once' to read all registers for the sensor.
   - Values are shown with units and scaling as defined in sns_details.json.
   - The colored dot in the top right shows status:
     - Gray: Idle
     - Orange: Ongoing
     - Green: Success
     - Red: Error

5. Repeat Read:
   - Set the interval (seconds) and click 'Repeat Read' for automatic reading.
   - Click 'Stop' to end repeat mode.

6. Special Notes:
   - Any sensor-specific notes are shown at the bottom of each tab.

7. Exiting:
   - Close the window to exit the application.

Troubleshooting:
----------------
- If you see errors, check COM port, baudrate, slave ID, and sensor wiring.
- Ensure sensors are powered and connected.
- Use the refresh button to update port list (if available).

Requirements:
-------------
- Windows PC
- Python 3.13 (if running from source)
- pyserial package
- sns_details.json file in the same folder

Packaging:
----------
- To create a standalone .exe, use PyInstaller:
  pyinstaller --onefile --windowed modbus_multiui.py
- The .exe will be in the 'dist' folder.

Contact:
--------
For support or questions, contact your software provider or developer.
