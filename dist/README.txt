Modbus Pressure Sensor UI - Packaged Software Instructions
=========================================================

How to Run:
-----------
1. Locate the 'presense.exe' file in this folder.
2. Double-click 'presense.exe' to launch the application.

Operating Instructions:
-----------------------
- Select the correct COM port from the dropdown.
- Choose the baud rate matching your sensor (default: 9600).
- Set Modbus addresses for Sensor 1 and Sensor 2 using the spinboxes (default: 1 and 2).
- Click the chain icon (🔗) to connect. Click again (⛓) to disconnect.
- Click 'Read Once' to read both sensors.
- Set the interval (seconds) and click 'Repeat Read' for automatic reading. Click 'Stop' to end repeat mode.
- The colored dot in the top right shows status:
  - Gray: Idle
  - Orange: Ongoing
  - Green: Success
  - Red: Error
- To refresh the COM port list, click the refresh icon (↻).
- Close the window to exit the application.

Troubleshooting:
----------------
- If you see errors, check COM port, baud rate, and sensor addresses.
- Ensure sensors are powered and connected.
- Use the refresh button to update port list.

No installation is required. All dependencies are included in the .exe.
