import tkinter as tk
from tkinter import ttk, messagebox
import serial, threading, time, json
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

def read_registers(ser, slave_id, start_reg, num_regs):
    frame = build_frame(slave_id, start_reg, num_regs)
    ser.timeout = 0.5
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(frame)
    return ser.read(64)

class SensorTab(ttk.Frame):
    def __init__(self, parent, sensor, com_ports):
        super().__init__(parent)
        self.sensor = sensor
        self.com_ports = com_ports
        self.serial_conn = None
        self.running = False
        self._build_ui()

    def _build_ui(self):
        s = self.sensor
        # Title
        ttk.Label(self, text=s['name'], style='Header.TLabel').grid(row=0, column=0, columnspan=4, sticky='w', pady=(8,4))
        # COM port
        ttk.Label(self, text='COM Port:').grid(row=1, column=0, sticky='w')
        self.com_entry = ttk.Combobox(self, values=self.com_ports, state='normal', width=14)
        self.com_entry.set(self.com_ports[0] if self.com_ports else 'COM3')
        self.com_entry.grid(row=1, column=1, padx=4, pady=2)
        # Baudrate
        ttk.Label(self, text='Baudrate:').grid(row=1, column=2, sticky='w')
        self.baud_entry = ttk.Combobox(self, values=[str(s.get('baudrate',9600))], state='normal', width=10)
        self.baud_entry.set(str(s.get('baudrate',9600)))
        self.baud_entry.grid(row=1, column=3, padx=4, pady=2)
        # Slave ID
        ttk.Label(self, text='Slave ID:').grid(row=2, column=0, sticky='w')
        self.slave_entry = tk.Spinbox(self, from_=1, to=247, width=6, font=('Segoe UI', 10), justify='center')
        self.slave_entry.delete(0, 'end')
        self.slave_entry.insert(0, str(s.get('slave_id',1)))
        self.slave_entry.grid(row=2, column=1, padx=4, pady=2)
        # Status indicator
        self.indicator_label = ttk.Label(self, text="●", foreground='gray', font=('Segoe UI', 16))
        self.indicator_label.grid(row=0, column=3, sticky='e', padx=(0,8))
        # Register values
        self.reg_labels = []
        self.reg_values = []
        for idx, reg in enumerate(s['registers']):
            ttk.Label(self, text=reg['name']+':').grid(row=3+idx, column=0, sticky='w', padx=4)
            val_lbl = ttk.Label(self, text='---', font=('Segoe UI', 10, 'bold'))
            val_lbl.grid(row=3+idx, column=1, sticky='w', padx=4)
            unit_lbl = ttk.Label(self, text=reg.get('unit',''))
            unit_lbl.grid(row=3+idx, column=2, sticky='w', padx=4)
            self.reg_labels.append(val_lbl)
            self.reg_values.append(reg)
        # Read buttons
        self.read_button = ttk.Button(self, text='Read Once', command=self.read_once)
        self.read_button.grid(row=3+len(s['registers']), column=0, columnspan=2, pady=8, sticky='ew')
        self.repeat_button = ttk.Button(self, text='Repeat Read', command=self.start_repeat)
        self.repeat_button.grid(row=3+len(s['registers']), column=2, pady=8, sticky='ew')
        self.stop_button = ttk.Button(self, text='Stop', command=self.stop_repeat)
        self.stop_button.grid(row=3+len(s['registers']), column=3, pady=8, sticky='ew')
        self.stop_button.config(state='disabled')
        # Interval
        ttk.Label(self, text='Interval (s):').grid(row=4+len(s['registers']), column=0, sticky='w', pady=2)
        self.interval_entry = ttk.Entry(self, width=10)
        self.interval_entry.insert(0, "2")
        self.interval_entry.grid(row=4+len(s['registers']), column=1, pady=2)
        # Special notes
        if s.get('special'):
            ttk.Label(self, text=s['special'], foreground='#888').grid(row=5+len(s['registers']), column=0, columnspan=4, sticky='w', pady=(4,0))
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def set_indicator(self, state):
        colors = {'idle':'gray','ongoing':'orange','success':'green','error':'red'}
        self.indicator_label.config(foreground=colors.get(state,'gray'))

    def connect(self):
        port = self.com_entry.get().strip()
        try:
            baud = int(self.baud_entry.get())
        except ValueError:
            self.set_indicator('error')
            messagebox.showerror('Connect error', 'Invalid baudrate')
            return False
        try:
            self.serial_conn = serial.Serial(port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=1)
            return True
        except Exception as e:
            self.serial_conn = None
            self.set_indicator('error')
            messagebox.showerror('Connect error', str(e))
            return False

    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None

    def read_once(self):
        if not self.connect():
            return
        self.set_indicator('ongoing')
        try:
            slave_id = int(self.slave_entry.get())
            for idx, reg in enumerate(self.reg_values):
                addr = int(reg['address'],16) if isinstance(reg['address'],str) else reg['address']
                num_regs = 2 if reg.get('format','') in ['float32','uint32'] else 1
                reply = read_registers(self.serial_conn, slave_id, addr, num_regs)
                val = self.decode_value(reply, reg)
                self.reg_labels[idx].config(text=val)
            self.set_indicator('success')
        except Exception as e:
            for lbl in self.reg_labels:
                lbl.config(text='---')
            self.set_indicator('error')
            messagebox.showerror('Read error', str(e))
        finally:
            self.disconnect()

    def decode_value(self, reply, reg):
        if not reply or len(reply)<5:
            return '---'
        fmt = reg.get('format','int16')
        scaling = reg.get('scaling',1)
        if fmt=='int16':
            val = (reply[3]<<8) | reply[4]
            if val & 0x8000:
                val -= 0x10000
            return f"{val*scaling:.2f}"
        elif fmt=='uint16':
            val = (reply[3]<<8) | reply[4]
            return f"{val*scaling:.2f}"
        elif fmt=='float32':
            if len(reply)<7:
                return '---'
            b = reply[3:7]
            import struct
            val = struct.unpack('>f', bytes(b))[0]
            return f"{val:.2f}"
        elif fmt=='uint32':
            if len(reply)<7:
                return '---'
            val = (reply[3]<<24)|(reply[4]<<16)|(reply[5]<<8)|(reply[6])
            return f"{val}"
        else:
            return '---'

    def start_repeat(self):
        if self.running:
            return
        self.running = True
        self.repeat_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.interval_entry.config(state='disabled')
        threading.Thread(target=self.repeat_loop, daemon=True).start()

    def stop_repeat(self):
        self.running = False
        self.repeat_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.interval_entry.config(state='normal')

    def repeat_loop(self):
        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                raise ValueError("Interval must be > 0")
        except Exception as e:
            self.set_indicator('error')
            self.stop_repeat()
            return
        while self.running:
            self.read_once()
            for _ in range(int(interval*10)):
                if not self.running:
                    break
                time.sleep(0.1)

class ModbusMultiUI:
    def __init__(self, root):
        self.root = root
        root.title("Modbus Multi-Sensor Tool")
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
        # Load sensor details
        with open('sns_details.json','r') as f:
            sensors = json.load(f)
        ports = [p.device for p in list_ports.comports()]
        notebook = ttk.Notebook(container)
        notebook.grid(row=0, column=0, sticky='nsew')
        for sensor in sensors:
            tab = SensorTab(notebook, sensor, ports)
            notebook.add(tab, text=sensor.get('short_name',sensor['name']))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        root.protocol('WM_DELETE_WINDOW', self.on_close)
    def on_close(self):
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusMultiUI(root)
    root.mainloop()
