import tkinter as tk
from tkinter import ttk, messagebox
import serial, threading, time
from serial.tools import list_ports

# --- Modbus helpers ---
def calc_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

def build_frame(slave_id, start_reg, num_regs):
    frame = bytearray([slave_id, 0x03,
                       (start_reg >> 8) & 0xFF, start_reg & 0xFF,
                       (num_regs >> 8) & 0xFF, num_regs & 0xFF])
    crc = calc_crc(frame)
    frame.append(crc & 0xFF)
    frame.append((crc >> 8) & 0xFF)
    return bytes(frame)

def read_registers(port, baudrate, slave_id, start_reg, num_regs, ser=None):
    frame = build_frame(slave_id, start_reg, num_regs)
    if ser is not None:
        ser.timeout = 0.5
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(frame)
        return ser.read(64)

    with serial.Serial(port=port, baudrate=baudrate, bytesize=8, parity='N', stopbits=1, timeout=0.5) as ser_local:
        ser_local.write(frame)
        reply = ser_local.read(64)
        return reply

def decode_pressure(port, baudrate, slave_id, ser=None):
    # Read decimal point + pressure in one request (0x0003..0x0004)
    reply = read_registers(port, baudrate, slave_id, 0x0003, 2, ser=ser)
    if len(reply) < 9:
        raise ValueError(f"Bad response from slave {slave_id}: {reply}")

    decimal_points = (reply[3] << 8) | reply[4]
    if decimal_points < 0 or decimal_points > 6:
        raise ValueError(f"Invalid decimal points: {decimal_points}")

    raw_value = (reply[5] << 8) | reply[6]
    pressure = raw_value / (10 ** decimal_points)
    return f"{pressure:.{decimal_points}f} bar"

# --- UI logic ---
class ModbusUI:
    def __init__(self, root):
        self.root = root
        root.title("Modbus Pressure Reader")
        root.resizable(True, True)

        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#eff3f6')
        style.configure('TLabel', font=('Segoe UI', 10), background='#eff3f6', foreground='#1f2937')
        style.configure('Header.TLabel', font=('Segoe UI Semibold', 12), background='#eff3f6', foreground='#1f2937')
        style.configure('TButton', font=('Segoe UI Semibold', 10), padding=8, relief='flat', background='#0078D4', foreground='white')
        style.map('TButton', background=[('active', '#005a9e'), ('disabled', '#a5adb5')])
        style.configure('TEntry', font=('Segoe UI', 10), fieldbackground='white', background='white', foreground='#0f172a')
        style.configure('TCombobox', font=('Segoe UI', 10), fieldbackground='white', background='white', foreground='#0f172a')

        root.configure(bg='#eff3f6')

        container = ttk.Frame(root, padding=(16, 16, 16, 24), style='TFrame')
        container.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="COM Port:").grid(row=0, column=0, sticky='w', pady=5)
        ports = [p.device for p in list_ports.comports()]
        self.com_entry = ttk.Combobox(container, values=ports, state='normal', width=18)
        self.com_entry.set(ports[0] if ports else 'COM3')
        self.com_entry.grid(row=0, column=1, pady=5, padx=5)

        # modern-looking icon buttons (chain/unlink style)
        self.connect_button = ttk.Button(container, text="🔗", width=3, command=self.connect_toggle)
        self.connect_button.grid(row=0, column=2, padx=2, pady=2)

        self.refresh_button = ttk.Button(container, text="↻", width=3, command=self.refresh_ports)
        self.refresh_button.grid(row=1, column=2, padx=2, pady=2, sticky='nw')

        ttk.Label(container, text="Baudrate:").grid(row=1, column=0, sticky='w', pady=(5, 12))
        self.baud_entry = ttk.Combobox(container, values=['4800','9600','19200','38400','57600','115200'], state='normal', width=18)
        self.baud_entry.set('9600')
        self.baud_entry.grid(row=1, column=1, pady=(5, 12), padx=5)

        self.sensor1_label = ttk.Label(container, text="Sensor 1: ---", style='Header.TLabel')
        self.sensor1_label.grid(row=2, column=0, columnspan=2, pady=8, sticky='w')

        self.sensor2_label = ttk.Label(container, text="Sensor 2: ---", style='Header.TLabel')
        self.sensor2_label.grid(row=3, column=0, columnspan=2, pady=3, sticky='w')

        self.status_label = ttk.Label(container, text="Status: Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)

        self.indicator_label = ttk.Label(container, text="● Idle", foreground='gray')
        self.indicator_label.grid(row=5, column=0, columnspan=2, pady=5)

        self.read_button = ttk.Button(container, text="Read Once", command=self.read_once)
        self.read_button.grid(row=6, column=0, columnspan=2, pady=8, sticky='ew')

        ttk.Label(container, text="Interval (s):").grid(row=7, column=0, sticky='w', pady=5)
        self.interval_entry = ttk.Entry(container, width=18)
        self.interval_entry.insert(0, "5")
        self.interval_entry.grid(row=7, column=1, pady=5, padx=5)

        self.repeat_button = ttk.Button(container, text="Repeat Read", command=self.start_repeat)
        self.repeat_button.grid(row=8, column=0, pady=8, sticky='ew', padx=2)

        self.stop_button = ttk.Button(container, text="Stop", command=self.stop_repeat)
        self.stop_button.grid(row=8, column=1, pady=8, sticky='ew', padx=2)
        self.stop_button.config(state='disabled')

        self.serial_conn = None

        # Extra margin below lower buttons so buttons don't touch window edge
        container.rowconfigure(9, minsize=24)

        root.protocol('WM_DELETE_WINDOW', self.on_close)

        root.update_idletasks()
        width = max(root.winfo_reqwidth(), 460)
        height = max(root.winfo_reqheight(), 360)
        root.geometry(f"{width}x{height}")
        root.minsize(440, 340)

        self.running = False

    def set_status(self, text):
        self.status_label.config(text=text)

    def set_indicator(self, state):
        if state == 'idle':
            self.indicator_label.config(text='● Idle', foreground='gray')
        elif state == 'ongoing':
            self.indicator_label.config(text='● Ongoing', foreground='orange')
        elif state == 'success':
            self.indicator_label.config(text='● Success', foreground='green')
        elif state == 'error':
            self.indicator_label.config(text='● Error', foreground='red')

    def connect_toggle(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.disconnect()
            return

        port = self.com_entry.get().strip()
        try:
            baud = int(self.baud_entry.get())
        except ValueError:
            self.set_status("Status: Invalid baudrate")
            self.set_indicator('error')
            return

        if not port:
            self.set_status("Status: COM port is empty")
            self.set_indicator('error')
            return

        try:
            self.serial_conn = serial.Serial(port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=1)
            self.set_status(f"Status: Connected to {port}@{baud}")
            self.connect_button.config(text='⛓')
            self.set_indicator('success')
            self.set_controls_enabled(False)
        except Exception as e:
            self.serial_conn = None
            self.set_status(f"Status: Connect failed - {e}")
            self.set_indicator('error')
            messagebox.showerror('Connect error', str(e))

    def set_controls_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        self.com_entry.config(state=state)
        self.baud_entry.config(state=state)
        self.refresh_button.config(state=state)

    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None
        self.connect_button.config(text='🔗')
        self.set_status('Status: Disconnected')
        self.set_indicator('idle')
        self.set_controls_enabled(True)

    def on_close(self):
        self.disconnect()
        self.root.destroy()

    def refresh_ports(self):
        ports = [p.device for p in list_ports.comports()]
        self.com_entry['values'] = ports
        if ports and self.com_entry.get() not in ports:
            self.com_entry.set(ports[0])
        self.set_status('Status: Port list refreshed')

    def read_once(self):
        port = self.com_entry.get().strip()
        try:
            baud = int(self.baud_entry.get())
        except ValueError:
            self.set_status("Status: Invalid baudrate")
            self.set_indicator('error')
            return

        if not port:
            self.set_status("Status: COM port is empty")
            self.set_indicator('error')
            return

        self.set_status("Status: Reading...")
        self.set_indicator('ongoing')

        read_ser = self.serial_conn if self.serial_conn and self.serial_conn.is_open else None

        try:
            val1 = decode_pressure(port, baud, 1, ser=read_ser)
            self.sensor1_label.config(text=f"Sensor 1: {val1}")

            val2 = decode_pressure(port, baud, 2, ser=read_ser)
            self.sensor2_label.config(text=f"Sensor 2: {val2}")

            self.set_status("Status: Read success")
            self.set_indicator('success')
        except Exception as e:
            self.sensor1_label.config(text="Sensor 1: ---")
            self.sensor2_label.config(text="Sensor 2: ---")
            self.set_status(f"Status: Error - {e}")
            self.set_indicator('error')
            messagebox.showerror("Read error", str(e))

    def start_repeat(self):
        if self.running:
            return
        self.running = True
        self.repeat_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.interval_entry.config(state='disabled')
        self.set_status("Status: Repeating")
        self.set_indicator('ongoing')
        threading.Thread(target=self.repeat_loop, daemon=True).start()

    def stop_repeat(self):
        self.running = False
        self.repeat_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.interval_entry.config(state='normal')
        self.set_status("Status: Stopped")
        self.set_indicator('idle')

    def repeat_loop(self):
        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                raise ValueError("Interval must be > 0")
        except Exception as e:
            self.status_label.config(text=f"Status: Invalid interval - {e}")
            self.stop_repeat()
            return

        while self.running:
            self.read_once()
            for _ in range(int(interval * 10)):
                if not self.running:
                    break
                time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusUI(root)
    root.mainloop()