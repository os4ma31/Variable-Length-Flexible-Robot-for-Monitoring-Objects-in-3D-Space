import customtkinter as ctk
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import threading
import time
import queue
import pygame
import math
import os
import collections
from tkinter import filedialog

# --- Matplotlib for Graphing ---
# Note: You may need to install this library: pip install matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- PIDController Class ---
class PIDController:
    """A basic PID controller."""
    def __init__(self, kp, ki, kd, output_limits=(-255, 255)):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.output_limits = output_limits
        self.setpoint = 0
        self.last_error = 0
        self.integral_error = 0
        self.last_time = None

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint
        self.integral_error = 0
        self.last_error = 0
        self.last_time = None

    def update(self, current_value):
        current_time = time.time()
        if self.last_time is None:
            self.last_time = current_time
            return 0
        dt = current_time - self.last_time
        if dt == 0: return 0
        error = self.setpoint - current_value
        self.integral_error += error * dt
        derivative_error = (error - self.last_error) / dt
        output = (self.kp * error) + (self.ki * self.integral_error) + (self.kd * derivative_error)
        self.last_error = error
        self.last_time = current_time
        return max(self.output_limits[0], min(self.output_limits[1], output))

# --- Graph Window Class ---
class GraphWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master # Reference to the main App
        self.title("Real-Time Encoder Graph")
        self.geometry("800x600")

        self.is_running = True
        self.data_points = 200 # Number of data points to show on the graph

        # --- Data Storage ---
        self.encoder_data = {f'E{i+1}': collections.deque(maxlen=self.data_points) for i in range(6)}
        self.time_data = collections.deque(maxlen=self.data_points)
        self.time_step = 0

        # --- Matplotlib Figure ---
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Encoder Values")
        self.ax.set_xlabel("Time Steps")
        self.ax.set_ylabel("Encoder Reading")

        self.lines = {}
        colors = plt.cm.get_cmap('viridis', 6)
        encoder_motor_map = {'E1': 'M1', 'E2': 'M2', 'E3': 'M3', 'E4': 'M4', 'E5': 'S2', 'E6': 'S3'}
        for i, (encoder, motor) in enumerate(encoder_motor_map.items()):
            line, = self.ax.plot([], [], label=f'{encoder} ({motor})', color=colors(i))
            self.lines[encoder] = line
        
        self.ax.legend()
        self.ax.grid(True, which='both', linestyle='--', linewidth=0.5)

        # --- Canvas to display the plot ---
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)

        # --- Control Buttons Frame ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10)

        self.toggle_button = ctk.CTkButton(button_frame, text="Pause", command=self.toggle_run)
        self.toggle_button.pack(side="left", padx=10)
        
        self.export_button = ctk.CTkButton(button_frame, text="Export Data", command=self.export_data)
        self.export_button.pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_style(ctk.get_appearance_mode().lower()) # Set initial theme
        self.update_graph()

    def toggle_run(self):
        self.is_running = not self.is_running
        self.toggle_button.configure(text="Pause" if self.is_running else "Resume")

    def export_data(self):
        """Exports the current graph data to a CSV file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Encoder Data"
        )
        if not filepath:
            self.master.gui_queue.put(("log_event", "Data export cancelled."))
            return

        try:
            with open(filepath, 'w', newline='') as f:
                header = "Time," + ",".join([f"E{i+1}" for i in range(6)]) + "\n"
                f.write(header)
                
                # Ensure all data lists are of the same length
                num_points = len(self.time_data)
                data_rows = [list(self.time_data)]
                for i in range(6):
                    data_rows.append(list(self.encoder_data[f'E{i+1}']))

                # Transpose data to write rows
                transposed_data = zip(*data_rows)
                
                for row in transposed_data:
                    f.write(','.join(map(str, row)) + '\n')
            
            self.master.gui_queue.put(("log_event", f"Graph data successfully exported to {os.path.basename(filepath)}"))
        except Exception as e:
            self.master.gui_queue.put(("log_event", f"Error exporting data: {e}"))


    def update_data(self, new_data):
        if not self.is_running:
            return
            
        self.time_data.append(self.time_step)
        self.time_step += 1
        
        for i in range(6):
            key = f'E{i+1}'
            self.encoder_data[key].append(new_data[i])

    def update_graph(self):
        if self.is_running:
            for encoder, line in self.lines.items():
                line.set_data(self.time_data, self.encoder_data[encoder])
            
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
        
        self.after(250, self.update_graph) # Update graph every 250ms

    def update_style(self, mode):
        is_dark = mode == "dark"
        
        # Set background colors
        self.fig.set_facecolor("#2B2B2B" if is_dark else "#EBEBEB")
        self.ax.set_facecolor("#1E1E1E" if is_dark else "#FFFFFF")
        
        # Set text/element colors
        text_color = "white" if is_dark else "black"
        self.ax.title.set_color(text_color)
        self.ax.xaxis.label.set_color(text_color)
        self.ax.yaxis.label.set_color(text_color)
        self.ax.tick_params(axis='x', colors=text_color)
        self.ax.tick_params(axis='y', colors=text_color)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(text_color)

        if self.ax.get_legend() is not None:
            for text in self.ax.get_legend().get_texts():
                text.set_color(text_color)
        
        self.canvas.draw()

    def on_closing(self):
        self.master.graph_window = None # Inform the main app that the window is closed
        self.destroy()


class App(ctk.CTk):
    """GUI to control the robotic arm with an Xbox controller and view feedback."""
    def __init__(self):
        super().__init__()

        # --- Appearance ---
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("Robotic Arm Xbox Controller Interface")
        self.geometry("1450x850")
        self.minsize(1300, 800)

        # --- Data & State ---
        self.serial_port = None
        self.joystick = None
        self.controller_thread = None
        self.serial_reader_thread = None
        self.stop_threads = threading.Event()
        self.gui_queue = queue.Queue()
        self.encoder_labels = {}
        self.controller_widgets = {} # To hold interactive controller widgets
        self.graph_window = None # To hold the graph window instance

        # --- PID Controllers & State ---
        self.pid_controllers = {
            'M1': PIDController(0.60, 0.005, 0.0001), 'M2': PIDController(0.8, 0.005, 0.1),
            'M3': PIDController(0.5, 0.005, 0.1), 'M4': PIDController(0.8, 0.005, 0.1),
            'S2': PIDController(0.80, 0.005, 0.1), 'S3': PIDController(0.95, 0.005, 0.01)
        }
        self.pid_states = {motor: {'enabled': False, 'target': 0} for motor in self.pid_controllers}
        self.current_encoders = {'M1': 0, 'M2': 0, 'M3': 0, 'M4': 0, 'S2': 0, 'S3': 0}

        # --- Debounce Timers ---
        self.last_press_times = {
            'dpad_down': 0, 'dpad_up': 0, 'dpad_right': 0, 'dpad_left': 0,
            'A': 0, 'B': 0, 'X': 0, 'Y': 0,
            'L_STICK': 0, 'R_STICK': 0, 'BACK': 0, 'LB': 0, 'RB': 0
        }
        self.DPAD_DEBOUNCE_DELAY = 0.5
        self.BUTTON_DEBOUNCE_DELAY = 0.3
        self._all_motors_zero_active = False

        # --- UI Construction ---
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)
        self._create_widgets()

        # --- Pygame & Closing Protocol ---
        pygame.init()
        self.after(100, self.process_gui_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_widgets(self):
        """Creates and lays out all the widgets."""
        self._create_controller_map_frame()
        self._create_data_frame()

    def _create_controller_map_frame(self):
        """Creates an interactive representation of the controller."""
        map_frame = ctk.CTkFrame(self, fg_color="gray14")
        map_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        title_label = ctk.CTkLabel(map_frame, text="Interactive Controller", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(10, 5))

        controller_canvas = ctk.CTkFrame(map_frame, fg_color="transparent")
        controller_canvas.pack(fill="both", expand=True, padx=20, pady=10)

        self.C_NORMAL = "gray30"
        self.C_PRESSED = "#3399FF"
        self.C_STICK_BG = "gray20"

        self.controller_widgets['LB'] = ctk.CTkLabel(controller_canvas, text="LB", fg_color=self.C_NORMAL, corner_radius=6, width=80, height=30)
        self.controller_widgets['LB'].place(relx=0.15, rely=0.1, anchor="center")
        self.controller_widgets['RB'] = ctk.CTkLabel(controller_canvas, text="RB", fg_color=self.C_NORMAL, corner_radius=6, width=80, height=30)
        self.controller_widgets['RB'].place(relx=0.85, rely=0.1, anchor="center")

        ls_bg = ctk.CTkFrame(controller_canvas, fg_color=self.C_STICK_BG, width=100, height=100, corner_radius=50)
        ls_bg.place(relx=0.2, rely=0.4, anchor="center")
        self.controller_widgets['L_STICK_VISUAL'] = ctk.CTkFrame(ls_bg, fg_color=self.C_NORMAL, width=50, height=50, corner_radius=25)
        self.controller_widgets['L_STICK_VISUAL'].place(relx=0.5, rely=0.5, anchor="center")
        self.controller_widgets['L_STICK_BTN'] = ctk.CTkLabel(controller_canvas, text="L3", fg_color=self.C_NORMAL, corner_radius=4)
        self.controller_widgets['L_STICK_BTN'].place(relx=0.2, rely=0.55, anchor="center")

        rs_bg = ctk.CTkFrame(controller_canvas, fg_color=self.C_STICK_BG, width=100, height=100, corner_radius=50)
        rs_bg.place(relx=0.65, rely=0.6, anchor="center")
        self.controller_widgets['R_STICK_VISUAL'] = ctk.CTkFrame(rs_bg, fg_color=self.C_NORMAL, width=50, height=50, corner_radius=25)
        self.controller_widgets['R_STICK_VISUAL'].place(relx=0.5, rely=0.5, anchor="center")
        self.controller_widgets['R_STICK_BTN'] = ctk.CTkLabel(controller_canvas, text="R3", fg_color=self.C_NORMAL, corner_radius=4)
        self.controller_widgets['R_STICK_BTN'].place(relx=0.65, rely=0.75, anchor="center")

        dpad_frame = ctk.CTkFrame(controller_canvas, fg_color="transparent")
        dpad_frame.place(relx=0.38, rely=0.6, anchor="center")
        self.controller_widgets['DPAD_UP'] = ctk.CTkLabel(dpad_frame, text="▲", width=30, height=30, fg_color=self.C_NORMAL)
        self.controller_widgets['DPAD_UP'].grid(row=0, column=1)
        self.controller_widgets['DPAD_LEFT'] = ctk.CTkLabel(dpad_frame, text="◀", width=30, height=30, fg_color=self.C_NORMAL)
        self.controller_widgets['DPAD_LEFT'].grid(row=1, column=0)
        ctk.CTkFrame(dpad_frame, width=30, height=30, fg_color="gray25").grid(row=1, column=1)
        self.controller_widgets['DPAD_RIGHT'] = ctk.CTkLabel(dpad_frame, text="▶", width=30, height=30, fg_color=self.C_NORMAL)
        self.controller_widgets['DPAD_RIGHT'].grid(row=1, column=2)
        self.controller_widgets['DPAD_DOWN'] = ctk.CTkLabel(dpad_frame, text="▼", width=30, height=30, fg_color=self.C_NORMAL)
        self.controller_widgets['DPAD_DOWN'].grid(row=2, column=1)

        self.controller_widgets['Y'] = ctk.CTkLabel(controller_canvas, text="Y", width=40, height=40, fg_color="#FBC02D", text_color="black", corner_radius=20)
        self.controller_widgets['Y'].place(relx=0.85, rely=0.3, anchor="center")
        self.controller_widgets['X'] = ctk.CTkLabel(controller_canvas, text="X", width=40, height=40, fg_color="#1976D2", text_color="white", corner_radius=20)
        self.controller_widgets['X'].place(relx=0.78, rely=0.4, anchor="center")
        self.controller_widgets['B'] = ctk.CTkLabel(controller_canvas, text="B", width=40, height=40, fg_color="#D32F2F", text_color="white", corner_radius=20)
        self.controller_widgets['B'].place(relx=0.92, rely=0.4, anchor="center")
        self.controller_widgets['A'] = ctk.CTkLabel(controller_canvas, text="A", width=40, height=40, fg_color="#388E3C", text_color="white", corner_radius=20)
        self.controller_widgets['A'].place(relx=0.85, rely=0.5, anchor="center")

        self.controller_widgets['BACK'] = ctk.CTkLabel(controller_canvas, text="Back", fg_color=self.C_NORMAL, corner_radius=10, height=25)
        self.controller_widgets['BACK'].place(relx=0.4, rely=0.3, anchor="center")

    def _create_data_frame(self):
        """Creates the right, scrollable frame for all dynamic data."""
        right_frame = ctk.CTkScrollableFrame(self, label_text="System Status & Control", label_font=ctk.CTkFont(size=16, weight="bold"))
        right_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        # --- Action Display ---
        action_display_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_display_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(action_display_frame, text="Last Action:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.action_display = ctk.CTkLabel(action_display_frame, text="---", font=ctk.CTkFont(size=32),
                                           fg_color="gray20", corner_radius=6, anchor="center", padx=10,
                                           text_color="#deffb3")
        self.action_display.pack(side="left", fill="x", expand=True, padx=(5,0))

        # --- Connection Header ---
        conn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        conn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(conn_frame, text="COM Port:").pack(side="left", padx=(0,5))
        self.com_var = ctk.StringVar()
        self.com_ports_combobox = ctk.CTkComboBox(conn_frame, variable=self.com_var, state="readonly", width=120)
        self.com_ports_combobox.pack(side="left", padx=5)
        self._refresh_com_ports()
        ctk.CTkButton(conn_frame, text="⟳", command=self._refresh_com_ports, width=30).pack(side="left", padx=5)
        self.connect_button = ctk.CTkButton(conn_frame, text="Connect", command=self.toggle_connection, width=100)
        self.connect_button.pack(side="left", padx=5)
        self.status_label = ctk.CTkLabel(conn_frame, text="Disconnected", text_color="orange")
        self.status_label.pack(side="left", padx=10)
        
        # --- Theme and Graph Buttons ---
        self.theme_switch = ctk.CTkSwitch(conn_frame, text="Light Mode", command=self._toggle_theme)
        self.theme_switch.pack(side="right", padx=(5, 10))
        ctk.CTkButton(conn_frame, text="Show Graph", command=self.open_graph_window).pack(side="right", padx=5)


        # --- Live Status Frame ---
        live_status_frame = ctk.CTkFrame(right_frame)
        live_status_frame.pack(fill="x", padx=10, pady=10)
        live_status_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(live_status_frame, text="Live Controller Status", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, pady=(5,10))
        self.controller_status_label = ctk.CTkLabel(live_status_frame, text="Controller Disconnected", text_color="orange", font=ctk.CTkFont(size=12))
        self.controller_status_label.grid(row=1, column=0, columnspan=4, pady=(0, 10))
        ctk.CTkLabel(live_status_frame, text="Control Axis", font=ctk.CTkFont(weight="bold", underline=True)).grid(row=2, column=0, padx=5)
        ctk.CTkLabel(live_status_frame, text="Active Motor", font=ctk.CTkFont(weight="bold", underline=True)).grid(row=2, column=1, padx=5)
        ctk.CTkLabel(live_status_frame, text="Speed", font=ctk.CTkFont(weight="bold", underline=True)).grid(row=2, column=2, padx=5)
        ctk.CTkLabel(live_status_frame, text="Direction", font=ctk.CTkFont(weight="bold", underline=True)).grid(row=2, column=3, padx=5)
        self.m1_speed_label = ctk.CTkLabel(live_status_frame, text="0"); self.m1_dir_label = ctk.CTkLabel(live_status_frame, text="STOP")
        self.m4s2_motor_label = ctk.CTkLabel(live_status_frame, text="---"); self.m4s2_speed_label = ctk.CTkLabel(live_status_frame, text="0")
        self.m2_speed_label = ctk.CTkLabel(live_status_frame, text="0"); self.m2_dir_label = ctk.CTkLabel(live_status_frame, text="STOP")
        self.m3s3_motor_label = ctk.CTkLabel(live_status_frame, text="---"); self.m3s3_speed_label = ctk.CTkLabel(live_status_frame, text="0")
        self.s1_dir_label = ctk.CTkLabel(live_status_frame, text="STOP")
        rows = [("End-Effector Up/Down (L-Stick Y)", "M1", self.m1_speed_label, self.m1_dir_label),
                ("End-Effector Bend (L-Stick X)", self.m4s2_motor_label, self.m4s2_speed_label, None),
                ("Lower Link Up/Down (R-Stick Y)", "M2", self.m2_speed_label, self.m2_dir_label),
                ("Lower Link Bend (R-Stick X)", self.m3s3_motor_label, self.m3s3_speed_label, None),
                ("Extend/Retract (Bumpers)", "S1", None, self.s1_dir_label)]
        for i, (axis, motor, speed, direction) in enumerate(rows):
            ctk.CTkLabel(live_status_frame, text=axis).grid(row=i+3, column=0, sticky="w", padx=5, pady=2)
            if isinstance(motor, str): ctk.CTkLabel(live_status_frame, text=motor).grid(row=i+3, column=1)
            else: motor.grid(row=i+3, column=1)
            if speed: speed.grid(row=i+3, column=2)
            if direction: direction.grid(row=i+3, column=3)

        # --- Encoder Feedback ---
        encoder_frame = ctk.CTkFrame(right_frame); encoder_frame.pack(fill="x", padx=10, pady=10)
        encoder_frame.grid_columnconfigure(tuple(range(6)), weight=1)
        ctk.CTkLabel(encoder_frame, text="Encoder Feedback", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=6, pady=5)
        for i in range(6):
            frame = ctk.CTkFrame(encoder_frame, fg_color="transparent"); frame.grid(row=1, column=i, padx=5, pady=5)
            ctk.CTkLabel(frame, text=f"E{i+1}:", font=ctk.CTkFont(weight="bold")).pack()
            self.encoder_labels[f"E{i+1}"] = ctk.CTkLabel(frame, text="0"); self.encoder_labels[f"E{i+1}"].pack()
        
        # --- PID Control Sections ---
        pid_grid_frame = ctk.CTkFrame(right_frame, fg_color="transparent"); pid_grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        pid_grid_frame.grid_columnconfigure(tuple(range(3)), weight=1)
        motor_map = [("M1 (End-Effector Up/Down)", 'M1'), ("M2 (Lower Link Up/Down)", 'M2'), ("M3 (Lower Link Left)", 'M3'),
                     ("M4 (End-Effector Left)", 'M4'), ("S2 (End-Effector Right)", 'S2'), ("S3 (Lower Link Right)", 'S3')]
        self.pid_ui_widgets = {}
        for i, (display_name, motor) in enumerate(motor_map):
            row, col = divmod(i, 3)
            pid_frame = ctk.CTkFrame(pid_grid_frame); pid_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self._create_pid_panel(pid_frame, display_name, motor)

        # --- Event Log ---
        ctk.CTkLabel(right_frame, text="Event Log", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=(5,5), anchor="w")
        self.event_log_textbox = ctk.CTkTextbox(right_frame, state="disabled", height=150, wrap="word")
        self.event_log_textbox.pack(pady=(0, 10), padx=10, fill="x", expand=True)

    def _create_pid_panel(self, parent, display_name, motor_name):
        parent.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(parent, text=display_name, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, columnspan=2, pady=5, padx=5)
        ctk.CTkLabel(parent, text="Status:").grid(row=1, column=0, padx=(5,0), pady=1, sticky="w")
        status = ctk.CTkLabel(parent, text="DISABLED", text_color="orange"); status.grid(row=1, column=1, padx=5, pady=1, sticky="w")
        ctk.CTkLabel(parent, text="Target Pos:").grid(row=2, column=0, padx=(5,0), pady=1, sticky="w")
        target = ctk.CTkLabel(parent, text="0"); target.grid(row=2, column=1, padx=5, pady=1, sticky="w")
        msg = ctk.CTkLabel(parent, text="PID Ready", text_color="gray", font=ctk.CTkFont(size=11), anchor="w"); msg.grid(row=3, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        self.pid_ui_widgets[motor_name] = {'status': status, 'target': target, 'message': msg}

    def open_graph_window(self):
        if self.graph_window is None or not self.graph_window.winfo_exists():
            self.graph_window = GraphWindow(self)
        else:
            self.graph_window.focus()

    def _toggle_theme(self):
        new_mode = "Light" if self.theme_switch.get() == 1 else "Dark"
        ctk.set_appearance_mode(new_mode)
        if self.graph_window is not None and self.graph_window.winfo_exists():
            self.graph_window.update_style(new_mode.lower())

    def _refresh_com_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.com_ports_combobox.configure(values=ports)
        self.com_var.set(ports[0] if ports else "")

    def send_command(self, command: str):
        if self.serial_port and self.serial_port.is_open:
            try: self.serial_port.write(command.encode('utf-8'))
            except serial.SerialException: self.disconnect()

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open: self.disconnect()
        else: self.connect()

    def connect(self):
        port = self.com_var.get()
        if not port: self.gui_queue.put(("log_event", "No COM port selected.")); return
        try:
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)
            self.connect_button.configure(text="Disconnect", fg_color="#D32F2F", hover_color="#E53935")
            self.status_label.configure(text=f"Connected to {port}", text_color="#4CAF50")
            self.stop_threads.clear()
            self.controller_thread = threading.Thread(target=self.controller_listener, daemon=True); self.controller_thread.start()
            self.serial_reader_thread = threading.Thread(target=self.read_from_serial, daemon=True); self.serial_reader_thread.start()
            self.gui_queue.put(("log_event", f"Successfully connected to {port}."))
        except serial.SerialException as e:
            self.status_label.configure(text="Error", text_color="orange")
            self.serial_port = None
            self.gui_queue.put(("log_event", f"Failed to connect: {e}"))

    def disconnect(self):
        self.stop_threads.set()
        if self.controller_thread and self.controller_thread.is_alive(): self.controller_thread.join(timeout=1)
        if self.serial_reader_thread and self.serial_reader_thread.is_alive(): self.serial_reader_thread.join(timeout=1)
        if self.serial_port and self.serial_port.is_open: self.serial_port.close()
        self.serial_port = None
        self.connect_button.configure(text="Connect", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
        self.status_label.configure(text="Disconnected", text_color="orange")
        self.controller_status_label.configure(text="Controller Disconnected", text_color="orange")
        self.gui_queue.put(("log_event", "Disconnected from serial port."))

    def _update_pid_ui(self, motor_name):
        state = self.pid_states[motor_name]
        widgets = self.pid_ui_widgets[motor_name]
        if state['enabled']:
            widgets['status'].configure(text="ENABLED", text_color="#4CAF50")
            widgets['message'].configure(text=f"Holding at {state['target']}")
        else:
            widgets['status'].configure(text="DISABLED", text_color="orange")
            widgets['message'].configure(text="Joystick Control")
            self.send_command(f"{ {'M1':1,'M2':2,'M3':3,'M4':4,'S1':5,'S2':6,'S3':7}[motor_name] }:s:0\n")
        widgets['target'].configure(text=str(state['target']))

    def _toggle_pid(self, motor_name, set_to_zero=False):
        state = self.pid_states[motor_name]
        state['enabled'] = not state['enabled']
        if state['enabled']:
            if set_to_zero: state['target'] = 0
            self.gui_queue.put(("log_event", f"PID for {motor_name} {'enabled, resetting to 0' if set_to_zero else 'toggled' }."))
            self.pid_controllers[motor_name].set_setpoint(state['target'])
        else:
            self.gui_queue.put(("log_event", f"PID disabled for {motor_name}."))
        self._update_pid_ui(motor_name)

    def _toggle_save_pos_pid(self, motor_name):
        """Toggles PID control for a motor, saving the current position if enabling."""
        state = self.pid_states[motor_name]
        if state['enabled']:
            state['enabled'] = False
            self.gui_queue.put(("log_event", f"PID disabled for {motor_name} via face button."))
        else:
            state['enabled'] = True
            state['target'] = self.current_encoders[motor_name]
            self.pid_controllers[motor_name].set_setpoint(state['target'])
            self.gui_queue.put(("log_event", f"{motor_name} holding position {state['target']} via PID."))
        
        self._update_pid_ui(motor_name)

    def toggle_all_pid_zero_mode(self):
        self._all_motors_zero_active = not self._all_motors_zero_active
        action = "Resetting all motors to zero" if self._all_motors_zero_active else "Disabling all PIDs"
        self.gui_queue.put(("log_event", f"BACK button: {action}."))
        for motor in self.pid_controllers:
            state = self.pid_states[motor]
            should_be_enabled = self._all_motors_zero_active
            if state['enabled'] != should_be_enabled:
                state['enabled'] = should_be_enabled
                if should_be_enabled: state['target'] = 0; self.pid_controllers[motor].set_setpoint(0)
                self._update_pid_ui(motor)

    def controller_listener(self):
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            self.gui_queue.put(("update_label", {'widget': self.controller_status_label, 'text': "No controller found!", 'color': "orange"}))
            return
        self.joystick = pygame.joystick.Joystick(0); self.joystick.init()
        self.gui_queue.put(("update_label", {'widget': self.controller_status_label, 'text': f"Connected: {self.joystick.get_name()}", 'color': "#4CAF50"}))

        JOYSTICK_DEADZONE, PID_TARGET_THRESHOLD = 0.15, 5
        AXIS_MAP = {'LX': 0, 'LY': 1, 'RX': 2, 'RY': 3}
        BTN_MAP = {'A': 0, 'B': 1, 'X': 2, 'Y': 3, 'LB': 4, 'RB': 5, 'BACK': 6, 'L_STICK': 8, 'R_STICK': 9}
        MOTOR_MAP = {'M1': 1, 'M2': 2, 'M3': 3, 'M4': 4, 'S1': 5, 'S2': 6, 'S3': 7}
        ACTION_TEXT = {'LB': 'Extend Actuator (S1)', 'RB': 'Retract Actuator (S1)', 'A': 'Toggle Hold: End-Effector Up/Down (M1)',
                       'B': 'Toggle Hold: Lower Link Right (S3)', 'X': 'Toggle Hold: Lower Link Left (M3)', 'Y': 'Toggle Hold: Lower Link Up/Down (M2)',
                       'L_STICK': 'Reset End-Effector Up/Down (M1)', 'R_STICK': 'Reset Lower Link Up/Down (M2)', 'BACK': 'Global Reset ALL Motors',
                       'DPAD_UP': 'Reset Lower Link Right (S3)', 'DPAD_DOWN': 'Reset Lower Link Left (M3)',
                       'DPAD_LEFT': 'Reset End-Effector Left (M4)', 'DPAD_RIGHT': 'Reset End-Effector Right (S2)'}
        last_commands = {motor: "" for motor in MOTOR_MAP}
        
        while not self.stop_threads.is_set():
            current_time = time.time()
            action_to_show = ""

            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.stop_threads.set(); return
                
                if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]:
                    for name, index in BTN_MAP.items():
                        if event.button == index:
                            is_down = event.type == pygame.JOYBUTTONDOWN
                            if name in ['A', 'B', 'X', 'Y']:
                                colors_normal = {'A': "#388E3C", 'B': "#D32F2F", 'X': "#1976D2", 'Y': "#FBC02D"}
                                colors_pressed = {'A': "#66BB6A", 'B': "#E57373", 'X': "#42A5F5", 'Y': "#FFEE58"}
                                color = colors_pressed[name] if is_down else colors_normal[name]
                                self.gui_queue.put(("update_widget_color", {'widget': self.controller_widgets[name], 'color': color}))
                            else:
                                color = self.C_PRESSED if is_down else self.C_NORMAL
                                widget_key = f"{name}_BTN" if "STICK" in name else name
                                self.gui_queue.put(("update_widget_color", {'widget': self.controller_widgets[widget_key], 'color': color}))
                
                if event.type == pygame.JOYBUTTONDOWN:
                    btn_name = next((name for name, i in BTN_MAP.items() if i == event.button), None)
                    if btn_name: action_to_show = ACTION_TEXT.get(btn_name, "")

                    if event.button == BTN_MAP['Y'] and current_time - self.last_press_times['Y'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['Y'] = current_time; self._toggle_save_pos_pid('M2')
                    elif event.button == BTN_MAP['B'] and current_time - self.last_press_times['B'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['B'] = current_time; self._toggle_save_pos_pid('S3')
                    elif event.button == BTN_MAP['X'] and current_time - self.last_press_times['X'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['X'] = current_time; self._toggle_save_pos_pid('M3')
                    elif event.button == BTN_MAP['A'] and current_time - self.last_press_times['A'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['A'] = current_time; self._toggle_save_pos_pid('M1')
                    elif event.button == BTN_MAP['R_STICK'] and current_time - self.last_press_times['R_STICK'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['R_STICK'] = current_time; self._toggle_pid('M2', set_to_zero=True)
                    elif event.button == BTN_MAP['L_STICK'] and current_time - self.last_press_times['L_STICK'] > self.BUTTON_DEBOUNCE_DELAY:
                        self.last_press_times['L_STICK'] = current_time; self._toggle_pid('M1', set_to_zero=True)
                    elif event.button == BTN_MAP['BACK'] and current_time - self.last_press_times['BACK'] > self.DPAD_DEBOUNCE_DELAY:
                        self.last_press_times['BACK'] = current_time; self.toggle_all_pid_zero_mode()

                if event.type == pygame.JOYHATMOTION and event.hat == 0:
                    hat_map = {(0,1): 'DPAD_UP', (0,-1): 'DPAD_DOWN', (-1,0): 'DPAD_LEFT', (1,0): 'DPAD_RIGHT'}
                    for val, name in hat_map.items():
                        is_pressed = event.value == val
                        self.gui_queue.put(("update_widget_color", {'widget': self.controller_widgets[name], 'color': self.C_PRESSED if is_pressed else self.C_NORMAL}))
                        if is_pressed: action_to_show = ACTION_TEXT.get(name, "")
                    
                    if event.value == (1, 0): self._toggle_pid('S2', set_to_zero=True)
                    elif event.value == (-1, 0): self._toggle_pid('M4', set_to_zero=True)
                    elif event.value == (0, 1): self._toggle_pid('S3', set_to_zero=True)
                    elif event.value == (0, -1): self._toggle_pid('M3', set_to_zero=True)

            for motor, state in self.pid_states.items():
                if state['enabled']:
                    pid_output = self.pid_controllers[motor].update(self.current_encoders[motor])
                    
                    if abs(state['target'] - self.current_encoders[motor]) > PID_TARGET_THRESHOLD:
                        speed = int(min(abs(pid_output), 255))
                        if motor == 'S2' or motor == 'S3':
                            direction = 'f' if pid_output > 0 else 'b' # Reversed for S2 and S3
                        else:
                            direction = 'b' if pid_output > 0 else 'f' # Normal
                    else:
                        speed, direction = 0, 's'

                    cmd = f"{MOTOR_MAP[motor]}:{direction}:{speed}\n"
                    if cmd != last_commands.get(motor):
                        self.send_command(cmd)
                        last_commands[motor] = cmd

            lx, ly = self.joystick.get_axis(AXIS_MAP['LX']), -self.joystick.get_axis(AXIS_MAP['LY'])
            rx, ry = self.joystick.get_axis(AXIS_MAP['RX']), -self.joystick.get_axis(AXIS_MAP['RY'])
            self.gui_queue.put(("update_joystick_visual", {'widget': self.controller_widgets['L_STICK_VISUAL'], 'x': lx, 'y': ly}))
            self.gui_queue.put(("update_joystick_visual", {'widget': self.controller_widgets['R_STICK_VISUAL'], 'x': rx, 'y': ry}))

            if not self.pid_states['M1']['enabled']:
                speed, d_text = (int(abs(ly)*255), "UP" if ly > JOYSTICK_DEADZONE else "DOWN" if ly < -JOYSTICK_DEADZONE else "STOP")
                direction = 'f' if ly > JOYSTICK_DEADZONE else 'b' if ly < -JOYSTICK_DEADZONE else 's'
                cmd = f"{MOTOR_MAP['M1']}:{direction}:{speed}\n";
                if cmd != last_commands['M1']: self.send_command(cmd); last_commands['M1'] = cmd
                self.gui_queue.put(("update_label", {'widget': self.m1_speed_label, 'text': str(speed)})); self.gui_queue.put(("update_label", {'widget': self.m1_dir_label, 'text': d_text}))
                if abs(ly) > JOYSTICK_DEADZONE: action_to_show = f"End-Effector Up/Down: {d_text}"

            if not self.pid_states['M4']['enabled'] and not self.pid_states['S2']['enabled']:
                speed, motor_text = int(abs(lx)*255), "---"
                if lx > JOYSTICK_DEADZONE: motor_text, cmd = "S2", f"{MOTOR_MAP['S2']}:f:{speed}\n"; action_to_show = "End-Effector Bend Right"
                elif lx < -JOYSTICK_DEADZONE: motor_text, cmd = "M4", f"{MOTOR_MAP['M4']}:f:{speed}\n"; action_to_show = "End-Effector Bend Left"
                else: cmd = "stop"
                if cmd == "stop" and (last_commands['M4']!="4:s:0\n" or last_commands['S2']!="6:s:0\n"): self.send_command("4:s:0\n"); self.send_command("6:s:0\n"); last_commands.update({'M4':"4:s:0\n", 'S2':"6:s:0\n"})
                elif cmd != "stop" and cmd != last_commands.get(motor_text): self.send_command("4:s:0\n" if motor_text=="S2" else "6:s:0\n"); self.send_command(cmd); last_commands.update({motor_text: cmd, ('M4' if motor_text=='S2' else 'S2'): "4:s:0\n" if motor_text=='S2' else "6:s:0\n"})
                self.gui_queue.put(("update_label", {'widget': self.m4s2_motor_label, 'text': motor_text})); self.gui_queue.put(("update_label", {'widget': self.m4s2_speed_label, 'text': str(speed if motor_text != "---" else 0)}))

            if not self.pid_states['M2']['enabled']:
                speed, d_text = (int(abs(ry)*255), "UP" if ry > JOYSTICK_DEADZONE else "DOWN" if ry < -JOYSTICK_DEADZONE else "STOP")
                direction = 'f' if ry > JOYSTICK_DEADZONE else 'b' if ry < -JOYSTICK_DEADZONE else 's'
                cmd = f"{MOTOR_MAP['M2']}:{direction}:{speed}\n";
                if cmd != last_commands['M2']: self.send_command(cmd); last_commands['M2'] = cmd
                self.gui_queue.put(("update_label", {'widget': self.m2_speed_label, 'text': str(speed)})); self.gui_queue.put(("update_label", {'widget': self.m2_dir_label, 'text': d_text}))
                if abs(ry) > JOYSTICK_DEADZONE: action_to_show = f"Lower Link Up/Down: {d_text}"

            if not self.pid_states['M3']['enabled'] and not self.pid_states['S3']['enabled']:
                speed, motor_text = int(abs(rx)*255), "---"
                if rx > JOYSTICK_DEADZONE: motor_text, cmd = "S3", f"{MOTOR_MAP['S3']}:f:{speed}\n"; action_to_show = "Lower Link Bend Right"
                elif rx < -JOYSTICK_DEADZONE: motor_text, cmd = "M3", f"{MOTOR_MAP['M3']}:f:{speed}\n"; action_to_show = "Lower Link Bend Left"
                else: cmd = "stop"
                if cmd == "stop" and (last_commands['M3']!="3:s:0\n" or last_commands['S3']!="7:s:0\n"): self.send_command("3:s:0\n"); self.send_command("7:s:0\n"); last_commands.update({'M3':"3:s:0\n", 'S3':"7:s:0\n"})
                elif cmd != "stop" and cmd != last_commands.get(motor_text): self.send_command("3:s:0\n" if motor_text=="S3" else "7:s:0\n"); self.send_command(cmd); last_commands.update({motor_text: cmd, ('M3' if motor_text=='S3' else 'S3'): "3:s:0\n" if motor_text=='S3' else "7:s:0\n"})
                self.gui_queue.put(("update_label", {'widget': self.m3s3_motor_label, 'text': motor_text})); self.gui_queue.put(("update_label", {'widget': self.m3s3_speed_label, 'text': str(speed if motor_text != "---" else 0)}))

            lb, rb = self.joystick.get_button(BTN_MAP['LB']), self.joystick.get_button(BTN_MAP['RB'])
            cmd, d_text = (f"{MOTOR_MAP['S1']}:f:255\n", "EXTEND") if lb else (f"{MOTOR_MAP['S1']}:b:255\n", "RETRACT") if rb else (f"{MOTOR_MAP['S1']}:s:0\n", "STOP")
            if cmd != last_commands['S1']: self.send_command(cmd); last_commands['S1'] = cmd; self.gui_queue.put(("update_label", {'widget': self.s1_dir_label, 'text': d_text}))
            
            if action_to_show: self.gui_queue.put(("update_label", {'widget': self.action_display, 'text': action_to_show}))

            time.sleep(0.02)

    def read_from_serial(self):
        while not self.stop_threads.is_set():
            if self.serial_port and self.serial_port.is_open:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line.startswith("E1:"): self.gui_queue.put(("update_encoders", line))
                except (serial.SerialException, UnicodeDecodeError) as e:
                    self.gui_queue.put(("log_event", f"Serial read error: {e}")); break
            else: time.sleep(0.1)

    def process_gui_queue(self):
        try:
            while True:
                msg_type, data = self.gui_queue.get_nowait()
                if msg_type == "update_label":
                    data['widget'].configure(text=data['text'])
                    if 'color' in data: data['widget'].configure(text_color=data['color'])
                elif msg_type == "log_event":
                    self.event_log_textbox.configure(state="normal")
                    self.event_log_textbox.insert("end", data + "\n"); self.event_log_textbox.see("end")
                    self.event_log_textbox.configure(state="disabled")
                elif msg_type == "update_encoders":
                    encoder_map = {'E1':'M1', 'E2':'M2', 'E3':'M3', 'E4':'M4', 'E5':'S2', 'E6':'S3'}
                    encoder_values = [0]*6
                    for part in data.split('|'):
                        try:
                            key, val_str = part.split(':')
                            if key in self.encoder_labels: self.encoder_labels[key].configure(text=val_str)
                            encoder_index = int(key[1:]) - 1
                            encoder_values[encoder_index] = int(val_str)
                            if (motor := encoder_map.get(key)): self.current_encoders[motor] = int(val_str)
                        except (ValueError, KeyError, IndexError): continue
                    if self.graph_window:
                        self.graph_window.update_data(encoder_values)
                elif msg_type == "update_widget_color":
                    data['widget'].configure(fg_color=data['color'])
                elif msg_type == "update_joystick_visual":
                    data['widget'].place(relx=0.5 + data['x']*0.4, rely=0.5 - data['y']*0.4, anchor="center")
        except queue.Empty: pass
        finally: self.after(50, self.process_gui_queue)

    def on_closing(self):
        self.stop_threads.set()
        if self.controller_thread: self.controller_thread.join(timeout=1)
        if self.serial_reader_thread: self.serial_reader_thread.join(timeout=1)
        if self.serial_port and self.serial_port.is_open: self.serial_port.close()
        pygame.quit()
        if self.graph_window: self.graph_window.destroy()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
