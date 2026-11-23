import tkinter as tk
import tkinter.filedialog, tkinter.scrolledtext, tkinter.messagebox, tkcolorpicker
from PIL import ImageTk, Image
import os, sys
from functools import partial
import webbrowser
import ui_theme as theme

import scripts, files, lp_colors, lp_events
from utils import launchpad_connector as lpcon

BUTTON_SIZE = 40
HS_SIZE = 200
V_WIDTH = 50
STAT_ACTIVE_COLOR = "#253c2e"
STAT_INACTIVE_COLOR = theme.PANEL
SELECT_COLOR = theme.ACCENT
DEFAULT_COLOR = [0, 0, 255]
MK1_DEFAULT_COLOR = [0, 255, 0]
INDICATOR_BPM = 480
BUTTON_FONT = (theme.FONT, 10)

PATH = None
PROG_PATH = None
USER_PATH = None

VERSION = None

PLATFORM = None

MAIN_ICON = None

launchpad = None

root = None
app = None
root_destroyed = None
restart = False
lp_object = None


load_layout_filetypes = [('LPHK layout files', [files.LAYOUT_EXT, files.LEGACY_LAYOUT_EXT])]
load_script_filetypes = [('LPHK script files', [files.SCRIPT_EXT, files.LEGACY_SCRIPT_EXT])]

save_layout_filetypes = [('LPHK layout files', [files.LAYOUT_EXT])]
save_script_filetypes = [('LPHK script files', [files.SCRIPT_EXT])]

lp_connected = False
lp_mode = None
colors_to_set = [[DEFAULT_COLOR for y in range(9)] for x in range(9)]


def init(lp_object_in, launchpad_in, path_in, prog_path_in, user_path_in, version_in, platform_in):
    global lp_object
    global launchpad
    global PATH
    global PROG_PATH
    global USER_PATH
    global VERSION
    global PLATFORM
    global MAIN_ICON
    lp_object = lp_object_in
    launchpad = launchpad_in
    PATH = path_in
    PROG_PATH = prog_path_in
    USER_PATH = user_path_in
    VERSION = version_in
    PLATFORM = platform_in

    if PLATFORM == "windows":
        MAIN_ICON = os.path.join(PATH, "resources", "LPHK.ico")
    else:
        MAIN_ICON = os.path.join(PATH, "resources", "LPHK.gif")

    make()


class Main_Window(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        self.button_mode = "edit"
        self.last_clicked = None
        self.outline_box = None
        self.grid_drawn = False
        self.grid_rects = [[None for y in range(9)] for x in range(9)]
        self.mode_buttons = {}
        self.layout_buttons = []
        self.init_window()

        self.about_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/LPHK-banner.png"))
        self.info_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/info.png"))
        self.warning_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/warning.png"))
        self.error_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/error.png"))
        self.alert_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/alert.png"))
        self.scare_image = ImageTk.PhotoImage(Image.open(PATH + "/resources/scare.png"))
        self.grid_drawn = False
        self.grid_rects = [[None for y in range(9)] for x in range(9)]
        self.button_mode = "edit"
        self.last_clicked = None
        self.outline_box = None

    def init_window(self):
        global root

        self.master.title("LPHK - Launchpad Hotkey")
        self.pack(fill="both", expand=1)

        self.m = tk.Menu(self.master)
        self.master.config(menu=self.m)

        self.m_Launchpad = tk.Menu(self.m, tearoff=False)
        self.m_Launchpad.add_command(label="Redetect (Restart)", command=self.redetect_lp)
        self.m.add_cascade(label="Launchpad", menu=self.m_Launchpad)

        self.m_Layout = tk.Menu(self.m, tearoff=False)
        self.m_Layout.add_command(label="New Layout", command=self.unbind_lp)
        self.m_Layout.add_command(label="Load Layout", command=self.load_layout)
        self.m_Layout.add_command(label="Save Layout", command=self.save_layout)
        self.m_Layout.add_command(label="Save Layout As...", command=self.save_layout_as)
        self.m.add_cascade(label="Layout", menu=self.m_Layout)

        self.disable_menu("Layout")

        self.m_Help = tk.Menu(self.m, tearoff=False)
        open_readme = lambda: self.show_help("LPHK", "README.md")
        self.m_Help.add_command(label="Open README...", command=open_readme)
        open_scripting = lambda: self.show_help("LPHKscript reference", "docs/SCRIPTING.md")
        self.m_Help.add_command(label="Scripting Help...", command=open_scripting)
        open_user_folder = lambda: files.open_file_folder(USER_PATH)
        self.m_Help.add_command(label="User Folder...", command=open_user_folder)
        open_prog_folder = lambda: files.open_file_folder(PROG_PATH)
        self.m_Help.add_command(label="Program Folder...", command=open_prog_folder)
        display_info = lambda: self.popup(self, "About LPHK", self.about_image, "A Novation Launchpad Macro Scripting System\nMade by Ella Jameson (nimaid)\n\nVersion: " + VERSION + "\nFile format version: " + files.FILE_VERSION, "Done")
        self.m_Help.add_command(label="About LPHK", command=display_info)
        self.m.add_cascade(label="Help", menu=self.m_Help)

        header = tk.Frame(self)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(22, 20))
        tk.Label(header, text="LPHK", font=(theme.FONT, 23, "bold")).pack(side="left")
        tk.Label(header, text="Launchpad Hotkey", fg=theme.MUTED).pack(side="left", padx=14, pady=(9, 0))
        theme.button(header, "Reconnect", self.redetect_lp).pack(side="right")

        c_gap = int(BUTTON_SIZE // 4)

        c_size = (BUTTON_SIZE * 9) + (c_gap * 9)
        self.c = tk.Canvas(self, width=c_size, height=c_size, bd=0)
        self.c.bind("<Button-1>", self.click)
        self.c.grid(row=1, column=0, padx=(24, 20), pady=(0, 20))
        self.draw_empty_state()

        sidebar = tk.Frame(self, width=220)
        sidebar.grid(row=1, column=1, sticky="nsew", padx=(0, 24), pady=(0, 20))
        sidebar.columnconfigure(0, weight=1)
        tk.Label(sidebar, text="LAYOUT", fg=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="ew")
        self.layout_name = tk.Label(sidebar, text="Untitled", anchor="w", wraplength=210,
                                    font=(theme.FONT, 12, "bold"))
        self.layout_name.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self.layout_count = tk.Label(sidebar, text="0 bound pads", fg=theme.MUTED, anchor="w")
        self.layout_count.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        actions = tk.Frame(sidebar)
        actions.grid(row=3, column=0, sticky="ew")
        for label, command in (("Open", self.load_layout), ("Save", self.save_layout)):
            button = theme.button(actions, label, command, width=7, state="disabled")
            button.pack(side="left", padx=(0, 8))
            self.layout_buttons.append(button)
        tk.Frame(sidebar, height=1, bg=theme.BORDER).grid(row=4, column=0, sticky="ew", pady=24)
        tk.Label(sidebar, text="PAD ACTION", fg=theme.MUTED, anchor="w").grid(row=5, column=0, sticky="ew")
        modes = tk.Frame(sidebar)
        modes.grid(row=6, column=0, sticky="ew", pady=(10, 12))
        for index, mode in enumerate(("edit", "move", "swap", "copy")):
            button = theme.button(modes, mode.capitalize(), partial(self.set_mode, mode), width=7)
            button.grid(row=index // 2, column=index % 2, padx=(0, 8), pady=(0, 8))
            self.mode_buttons[mode] = button
        self.mode_hint = tk.Label(sidebar, text="", fg=theme.MUTED, anchor="nw",
                                  justify="left", wraplength=205)
        self.mode_hint.grid(row=7, column=0, sticky="ew")
        sidebar.rowconfigure(8, weight=1)
        tk.Label(sidebar, text="Layouts, scripts and sounds", fg=theme.MUTED, anchor="w").grid(row=9, column=0, sticky="ew", pady=(20, 8))
        theme.button(sidebar, "Open user folder", open_user_folder).grid(row=10, column=0, sticky="ew")
        self.update_sidebar()

        self.stat = tk.Label(self, text="No Launchpad connected", bg=STAT_INACTIVE_COLOR,
                             fg=theme.MUTED, anchor="w", padx=24, pady=12)
        self.stat.grid(row=2, column=0, columnspan=2, sticky=tk.EW)

    def set_mode(self, mode):
        self.button_mode = mode
        self.last_clicked = None
        self.update_sidebar()
        if self.grid_drawn:
            self.draw_canvas()

    def update_sidebar(self):
        if not hasattr(self, "layout_name"):
            return
        name = os.path.basename(files.curr_layout) if files.curr_layout else "Untitled"
        self.layout_name.configure(text=name)
        count = sum(bool(value) for row in scripts.text for value in row)
        self.layout_count.configure(text=f"{count} bound pad{'s' if count != 1 else ''}")
        hints = {
            "edit": "Click a pad to edit its script and colour.",
            "move": "Choose a pad, then its destination. The original pad is cleared.",
            "swap": "Choose two pads to exchange their scripts and colours.",
            "copy": "Choose a pad, then a destination to copy it to.",
        }
        self.mode_hint.configure(text=hints[self.button_mode])
        for mode, button in self.mode_buttons.items():
            selected = mode == self.button_mode
            button.configure(bg=theme.ACCENT_BG if selected else theme.BUTTON,
                             fg=theme.ACCENT if selected else theme.TEXT)

    def draw_empty_state(self):
        size = (BUTTON_SIZE + BUTTON_SIZE // 4) * 9
        self.c.create_text(size / 2, size / 2 - 14, text="Connect a Launchpad",
                           fill=theme.TEXT, font=(theme.FONT, 15, "bold"), tags="empty")
        self.c.create_text(size / 2, size / 2 + 18, text="Your pads will appear here.",
                           fill=theme.MUTED, font=(theme.FONT, 10), tags="empty")

    def show_help(self, title, relative_path):
        help_window = tk.Toplevel(self)
        help_window.title(title)
        help_window.transient(self.master)
        text = tk.scrolledtext.ScrolledText(help_window, width=90, height=30,
                                           padx=18, pady=18, wrap="word", font="TkFixedFont")
        theme.dark_scrollbar(text)
        text.pack(fill="both", expand=True, padx=16, pady=16)
        try:
            with open(os.path.join(PATH, relative_path), encoding="utf-8") as source:
                text.insert("1.0", source.read())
        except OSError:
            text.insert("1.0", "Documentation is missing from this copy. See the README included in your download.")
        text.configure(state="disabled")
        theme.button(help_window, "Close", help_window.destroy).pack(anchor="e", padx=16, pady=(0, 16))

    def raise_above_all(self):
        self.master.attributes('-topmost', 1)
        self.master.attributes('-topmost', 0)

    def enable_menu(self, name):
        self.m.entryconfig(name, state="normal")
        if name == "Layout":
            for button in self.layout_buttons:
                button.configure(state="normal")

    def disable_menu(self, name):
        self.m.entryconfig(name, state="disabled")
        if name == "Layout":
            for button in self.layout_buttons:
                button.configure(state="disabled")

    def connect_dummy(self):
        # WIP
        global lp_connected
        global lp_mode
        global lp_object

        lp_connected = True
        lp_mode = "Dummy"
        self.draw_canvas()
        self.enable_menu("Layout")

    def connect_lp(self):
        global lp_connected
        global lp_mode
        global lp_object

        lp = lpcon.get_launchpad()

        if lp == -1:
            self.popup(self, "Connect to Unsupported Device", self.error_image,
                       """The device you are attempting to use is not currently supported by LPHK,
                       and there are no plans to add support for it.
                       Please voice your feature requests on the Discord or on GitHub.""",
                       "OK")

        if lp is None:
            self.popup_choice(self, "No Launchpad Detected...", self.error_image,
                              """Could not detect any connected Launchpads!
                              Disconnect and reconnect your USB cable,
                              then click 'Redetect Now'.""",
                              [["Ignore", None], ["Redetect Now", self.redetect_lp]]
                              )
            return

        if lpcon.connect(lp):
            lp_connected = True
            lp_object = lp
            lp_mode = lpcon.get_mode(lp)

            if lp_mode == "Pro":
                self.popup(self, "Connect to Launchpad Pro", self.error_image,
                           """This is a BETA feature! The Pro is not fully supported yet,as the bottom and left rows are not mappable currently.
                           I (nimaid) do not have a Launchpad Pro to test with, so let me know if this does or does not work on the Discord! (https://discord.gg/mDCzB8X)
                           You must first put your Launchpad Pro in Live (Session) mode. To do this, press and holde the 'Setup' key, press the green pad in the
                           upper left corner, then release the 'Setup' key. Please only continue once this step is completed.""",
                           "I am in Live mode.")

            lp_object.ButtonFlush()

            # special case?
            if lp_mode != "Mk1":
                lp_object.LedCtrlBpm(INDICATOR_BPM)

            lp_events.start(lp_object)
            self.draw_canvas()
            self.enable_menu("Layout")
            self.stat["text"] = f"Connected to {lpcon.get_display_name(lp)}"
            self.stat["bg"] = STAT_ACTIVE_COLOR
            self.stat["fg"] = theme.ACCENT
            # search for a startup layout and load it
            if os.path.isfile(os.path.join(files.LAYOUT_PATH, "startup.lpl")):
                files.load_layout_to_lp(os.path.join(files.LAYOUT_PATH, "startup.lpl"))

    def disconnect_lp(self):
        global lp_connected
        if lp_events.timer is not None:
            lp_events.timer.cancel()
        if lp_connected:
            try:
                scripts.unbind_all()
            except Exception as error:
                print("[window] Could not reset Launchpad:", error)
            finally:
                try:
                    lpcon.disconnect(lp_object)
                except Exception as error:
                    print("[window] Could not close Launchpad:", error)
        lp_connected = False

        self.clear_canvas()

        self.disable_menu("Layout")

        self.stat["text"] = "No Launchpad Connected"
        self.stat["bg"] = STAT_INACTIVE_COLOR
        self.stat["fg"] = theme.MUTED

    def redetect_lp(self):
        global restart
        restart = True
        close()

    def unbind_lp(self, prompt_save=True):
        if prompt_save:
            self.modified_layout_save_prompt()
        scripts.unbind_all()
        files.curr_layout = None
        self.draw_canvas()

    def load_layout(self):
        self.modified_layout_save_prompt()
        name = tk.filedialog.askopenfilename(parent=app,
                                          initialdir=files.LAYOUT_PATH,
                                          title="Load layout",
                                          filetypes=load_layout_filetypes)
        if name:
            files.load_layout_to_lp(name)

    def save_layout_as(self):
        name = tk.filedialog.asksaveasfilename(parent=app,
                                            initialdir=files.LAYOUT_PATH,
                                            title="Save layout as...",
                                            filetypes=save_layout_filetypes)
        if name:
            if files.LAYOUT_EXT not in name:
                name += files.LAYOUT_EXT
            files.save_lp_to_layout(name)
            files.load_layout_to_lp(name)

    def save_layout(self):
        if files.curr_layout == None:
            self.save_layout_as()
        else:
            files.save_lp_to_layout(files.curr_layout)
            files.load_layout_to_lp(files.curr_layout)

    def click(self, event):
        gap = int(BUTTON_SIZE // 4)


        column = min(8, int(event.x // (BUTTON_SIZE + gap)))
        row = min(8, int(event.y // (BUTTON_SIZE + gap)))

        if self.grid_drawn:
            if(column, row) == (8, 0):
            #mode change
                self.last_clicked = None
                if self.button_mode == "edit":
                    self.button_mode = "move"
                elif self.button_mode == "move":
                    self.button_mode = "swap"
                elif self.button_mode == "swap":
                    self.button_mode = "copy"
                else:
                    self.button_mode = "edit"
                self.draw_canvas()
            else:
                if self.button_mode == "edit":
                    self.last_clicked = (column, row)
                    self.draw_canvas()
                    self.script_entry_window(column, row)
                    self.last_clicked = None
                else:
                    if self.last_clicked == None:
                        self.last_clicked = (column, row)
                    else:
                        move_func = partial(scripts.move, self.last_clicked[0], self.last_clicked[1], column, row)
                        swap_func = partial(scripts.swap, self.last_clicked[0], self.last_clicked[1], column, row)
                        copy_func = partial(scripts.copy, self.last_clicked[0], self.last_clicked[1], column, row)

                        if self.button_mode == "move":
                            if scripts.is_bound(column, row) and ((self.last_clicked) != (column, row)):
                                self.popup_choice(self, "Button Already Bound", self.warning_image, "You are attempting to move a button to an already\nbound button. What would you like to do?", [["Overwrite", move_func], ["Swap", swap_func], ["Cancel", None]])
                            else:
                                move_func()
                        elif self.button_mode == "copy":
                            if scripts.is_bound(column, row) and ((self.last_clicked) != (column, row)):
                                self.popup_choice(self, "Button Already Bound", self.warning_image, "You are attempting to copy a button to an already\nbound button. What would you like to do?", [["Overwrite", copy_func], ["Swap", swap_func], ["Cancel", None]])
                            else:
                                copy_func()
                        elif self.button_mode == "swap":
                            swap_func()
                        self.last_clicked = None
                self.draw_canvas()

    def draw_button(self, column, row, color="#000000", shape="square"):
        color = theme.pad_color(color)
        gap = int(BUTTON_SIZE // 4)

        x_start = round((BUTTON_SIZE * column) + (gap * column) + (gap / 2))
        y_start = round((BUTTON_SIZE * row) + (gap * row) + (gap / 2))
        x_end = x_start + BUTTON_SIZE
        y_end = y_start + BUTTON_SIZE

        if shape == "square":
            radius = 5
            points = [x_start+radius, y_start, x_end-radius, y_start, x_end, y_start,
                      x_end, y_start+radius, x_end, y_end-radius, x_end, y_end,
                      x_end-radius, y_end, x_start+radius, y_end, x_start, y_end,
                      x_start, y_end-radius, x_start, y_start+radius, x_start, y_start]
            return self.c.create_polygon(points, smooth=True, splinesteps=16, fill=color,
                                         outline=theme.BORDER, width=1)
        elif shape == "circle":
            shrink = BUTTON_SIZE / 10
            return self.c.create_oval(x_start + shrink, y_start + shrink, x_end - shrink, y_end - shrink, fill=color, outline="")

    def draw_canvas(self):
        self.c.delete("empty")
        self.update_sidebar()
        if self.last_clicked != None:
            if self.outline_box == None:
                gap = int(BUTTON_SIZE // 4)

                x_start = round((BUTTON_SIZE * self.last_clicked[0]) + (gap * self.last_clicked[0]))
                y_start = round((BUTTON_SIZE * self.last_clicked[1]) + (gap * self.last_clicked[1]))
                x_end = round(x_start + BUTTON_SIZE + gap)
                y_end = round(y_start + BUTTON_SIZE + gap)

                if (self.last_clicked[1] == 0) or (self.last_clicked[0] == 8):
                    self.outline_box = self.c.create_oval(x_start + (gap // 2), y_start + (gap // 2), x_end - (gap // 2), y_end - (gap // 2), fill=SELECT_COLOR, outline="")
                else:
                    self.outline_box = self.c.create_rectangle(x_start, y_start, x_end, y_end, fill=SELECT_COLOR, outline="")
                self.c.tag_lower(self.outline_box)
        else:
            if self.outline_box != None:
                self.c.delete(self.outline_box)
                self.outline_box = None

        if self.grid_drawn:
            for x in range(8):
                y = 0
                self.c.itemconfig(self.grid_rects[x][y], fill=theme.pad_color(lp_colors.getXY_RGB(x, y)))

            for y in range(1, 9):
                x = 8
                self.c.itemconfig(self.grid_rects[x][y], fill=theme.pad_color(lp_colors.getXY_RGB(x, y)))

            for x in range(8):
                for y in range(1, 9):
                    self.c.itemconfig(self.grid_rects[x][y], fill=theme.pad_color(lp_colors.getXY_RGB(x, y)))

            self.c.itemconfig(self.grid_rects[8][0], text=self.button_mode.capitalize())
        else:
            for x in range(8):
                y = 0
                self.grid_rects[x][y] = self.draw_button(x, y, color=lp_colors.getXY_RGB(x, y), shape="circle")

            for y in range(1, 9):
                x = 8
                self.grid_rects[x][y] = self.draw_button(x, y, color=lp_colors.getXY_RGB(x, y), shape="circle")

            for x in range(8):
                for y in range(1, 9):
                    self.grid_rects[x][y] = self.draw_button(x, y, color=lp_colors.getXY_RGB(x, y))

            gap = int(BUTTON_SIZE // 4)
            text_x = round((BUTTON_SIZE * 8) + (gap * 8) + (BUTTON_SIZE / 2) + (gap / 2))
            text_y = round((BUTTON_SIZE / 2) + (gap / 2))
            self.grid_rects[8][0] = self.c.create_text(text_x, text_y, text=self.button_mode.capitalize(),
                                                    fill=theme.MUTED, font=(theme.FONT, 9))

            self.grid_drawn = True

    def clear_canvas(self):
        self.c.delete("all")
        self.grid_rects = [[None for y in range(9)] for x in range(9)]
        self.grid_drawn = False
        self.outline_box = None
        self.last_clicked = None
        self.draw_empty_state()
        self.update_sidebar()

    def script_entry_window(self, x, y, text_override=None, color_override=None):
        global color_to_set

        w = tk.Toplevel(self)
        w.transient(self.master)
        w.winfo_toplevel().title("Editing Script for Button (" + str(x) + ", " + str(y) + ")")
        w.resizable(False, False)

        if MAIN_ICON != None:
            if os.path.splitext(MAIN_ICON)[1].lower() == ".gif":
                dummy = None
                #w.call('wm', 'iconphoto', w._w, tk.PhotoImage(file=MAIN_ICON))
            else:
                w.iconbitmap(MAIN_ICON)

        def validate_func():
            nonlocal x, y, t

            text_string = t.get(1.0, tk.END)
            try:
                script_validate = scripts.validate_script(text_string)
            except:
                #self.save_script(w, x, y, text_string) # This will fail and throw a popup error
                self.popup(w, "Script Validation Error", self.error_image, "Fatal error while attempting to validate script.\nPlease see LPHK.log for more information.", "OK")
                raise
            if script_validate != True and files.in_error:
                self.save_script(w, x, y, text_string)
            else:
                w.destroy()
        w.protocol("WM_DELETE_WINDOW", validate_func)

        e_m = tk.Menu(w)
        w.config(menu=e_m)

        e_m_Script = tk.Menu(e_m, tearoff=False)

        tk.Label(w, text=f"Button {x}, {y}", font=(theme.FONT, 16, "bold"),
                 anchor="w").grid(column=0, row=0, sticky="ew", padx=20, pady=(20, 2))
        tk.Label(w, text="SCRIPT", fg=theme.MUTED, anchor="w").grid(
            column=0, row=1, sticky="ew", padx=20, pady=(8, 0))
        t = tk.scrolledtext.ScrolledText(w, width=60, height=21, font="TkFixedFont",
                                        padx=14, pady=12, spacing1=2, undo=True)
        theme.dark_scrollbar(t)
        t.grid(column=0, row=2, rowspan=3, padx=20, pady=(8, 16))
        tk.Label(w, text="LPHKscript  /  Commands are case sensitive", fg=theme.MUTED,
                 anchor="w").grid(column=0, row=5, sticky="ew", padx=20, pady=(0, 18))

        if text_override == None:
            t.insert(tk.INSERT, scripts.text[x][y])
        else:
            t.insert(tk.INSERT, text_override)
        t.bind("<<Paste>>", self.custom_paste)
        t.bind("<Control-Key-a>", self.select_all)

        import_script_func = lambda: self.import_script(t, w)
        e_m_Script.add_command(label="Import script", command=import_script_func)
        export_script_func = lambda: self.export_script(t, w)
        e_m_Script.add_command(label="Export script", command=export_script_func)
        e_m.add_cascade(label="Script", menu=e_m_Script)

        if color_override == None:
            colors_to_set[x][y] =  lp_colors.getXY(x, y)
        else:
            colors_to_set[x][y] = color_override

        if type(colors_to_set[x][y]) == int:
            colors_to_set[x][y] = lp_colors.code_to_RGB(colors_to_set[x][y])

        if all(c < 4 for c in colors_to_set[x][y]):
            if lp_mode == "Mk1":
                colors_to_set[x][y] = MK1_DEFAULT_COLOR
            else:
                colors_to_set[x][y] = DEFAULT_COLOR

        ask_color_func = lambda: self.ask_color(w, color_button, x, y, colors_to_set[x][y])
        properties = tk.Frame(w)
        properties.grid(column=1, row=2, rowspan=3, padx=(0, 20), pady=(8, 16), sticky="ns")
        color_button = tk.Button(properties, text="Select Color", command=ask_color_func)
        color_button.pack(fill="x", pady=(0, 20))
        color_button.config(font=BUTTON_FONT)
        start_color_str = lp_colors.list_RGB_to_string(colors_to_set[x][y])
        self.button_color_with_text_update(color_button, start_color_str)

        save_script_func = lambda: self.save_script(w, x, y, t.get(1.0, tk.END))
        save_button = tk.Button(properties, text="Bind Button (" + str(x) + ", " + str(y) + ")", command=save_script_func)
        save_button.pack(fill="x")
        save_button.config(font=BUTTON_FONT)
        save_button.config(bg=theme.ACCENT_BG, fg=theme.ACCENT)

        unbind_func = lambda: self.unbind_destroy(x, y, w)
        unbind_button = tk.Button(properties, text="Unbind Button (" + str(x) + ", " + str(y) + ")", command=unbind_func)
        unbind_button.pack(side="bottom", fill="x")
        unbind_button.config(font=BUTTON_FONT)
        unbind_button.config(bg=theme.BUTTON, fg=theme.DANGER)

        w.wait_visibility()
        w.grab_set()
        t.focus_set()
        w.wait_window()

    def classic_askcolor(self, color=(255, 0, 0), title="Color Chooser"):
        w = tk.Toplevel(self)
        w.winfo_toplevel().title(title)
        w.resizable(False, False)
        if MAIN_ICON != None:
            if os.path.splitext(MAIN_ICON)[1].lower() == ".gif":
                dummy = None
                #w.call('wm', 'iconphoto', popup._w, tk.PhotoImage(file=MAIN_ICON))
            else:
                w.iconbitmap(MAIN_ICON)

        w.protocol("WM_DELETE_WINDOW", w.destroy)

        color = ""

        def return_color(col):
            nonlocal color
            color = col
            w.destroy()

        button_frame = tk.Frame(w)
        button_frame.grid(padx=(10, 0), pady=(10, 0))

        def make_grid_button(column, row, color_hex, func=None, size=100):
            nonlocal w
            f = tk.Frame(button_frame, width=size, height=size)

            b = tk.Button(f, command=func)

            f.rowconfigure(0, weight = 1)
            f.columnconfigure(0, weight = 1)
            f.grid_propagate(0)

            f.grid(column=column, row=row)
            b.grid(padx=(0,10), pady=(0,10), sticky="nesw")
            b.config(bg=color_hex)

        def make_color_button(button_color, column, row, size=100):
            button_color_hex = "#%02x%02x%02x" % button_color

            b_func = lambda: return_color(button_color)
            make_grid_button(column, row, button_color_hex, b_func, size)

        for c in range(4):
            for r in range(4):
                if not (c == 0 and r == 3):
                    red = int(c * (255 / 3))
                    green = int((3 - r) * (255 / 3))

                    make_color_button((red, green, 0), c, r, size=75)

        w.wait_visibility()
        w.grab_set()
        w.wait_window()

        if color:
            hex = "#%02x%02x%02x" % color
            return color, hex
        else:
            return None, None

    def ask_color(self, window, button, x, y, default_color):
        global colors_to_set

        if lp_mode == "Mk1":
            color = self.classic_askcolor(color=tuple(default_color), title="Select Color for Button (" + str(x) + ", " + str(y) + ")")
        else:
            color = tkcolorpicker.askcolor(color=tuple(default_color), parent=window, title="Select Color for Button (" + str(x) + ", " + str(y) + ")")
        if color[0] != None:
            color_to_set = [int(min(255, max(0, c))) for c in color[0]]
            if all(c < 4 for c in color_to_set):
                rerun = lambda: self.ask_color(window, button, x, y, default_color)
                self.popup(window, "Invalid Color", self.warning_image, "That color is too dark to see.", "OK", rerun)
            else:
                colors_to_set[x][y] = color_to_set
                self.button_color_with_text_update(button, color[1])

    def button_color_with_text_update(self, button, color):
        button.configure(bg=color, activebackground=color)
        color_rgb = []
        for c in range(3):
            start_index = c * 2
            val = color[start_index + 1:start_index + 3]
            color_rgb.append(int(val, 16))
        luminance = lp_colors.luminance(color_rgb[0], color_rgb[1], color_rgb[2])
        if luminance > 0.5:
            button.configure(fg="black", activeforeground="black")
        else:
            button.configure(fg="white", activeforeground="white")

    def custom_paste(self, event):
        try:
            event.widget.delete("sel.first", "sel.last")
        except:
            pass
        event.widget.insert("insert", event.widget.clipboard_get())
        return "break"

    def select_all(self, event):
        event.widget.tag_add(tk.SEL, "1.0", tk.END)
        event.widget.mark_set(tk.INSERT, "1.0")
        event.widget.see(tk.INSERT)
        return "break"

    def unbind_destroy(self, x, y, window):
        scripts.unbind(x, y)
        self.draw_canvas()
        window.destroy()

    def save_script(self, window, x, y, script_text, open_editor = False, color=None):
        global colors_to_set

        script_text = script_text.strip()

        def open_editor_func():
            nonlocal x, y
            if open_editor:
                    self.script_entry_window(x, y, script_text, color)
        try:
            script_validate = scripts.validate_script(script_text)
        except:
            self.popup(window, "Script Validation Error", self.error_image, "Fatal error while attempting to validate script.\nPlease see LPHK.log for more information.", "OK", end_command = open_editor_func)
            raise
        if script_validate == True:
            if script_text != "":
                script_text = files.strip_lines(script_text)
                scripts.bind(x, y, script_text, colors_to_set[x][y])
                self.draw_canvas()
                lp_colors.updateXY(x, y)
                window.destroy()
            else:
                self.popup(window, "No Script Entered", self.info_image, "Please enter a script to bind.", "OK", end_command = open_editor_func)
        else:
            self.popup(window, "(" + str(x) + ", " + str(y) + ") Syntax Error", self.error_image, "Error in line: " + script_validate[1] + "\n" + script_validate[0], "OK", end_command = open_editor_func)

    def import_script(self, textbox, window):
        name = tk.filedialog.askopenfilename(parent=window,
                                             initialdir=files.SCRIPT_PATH,
                                             title="Import script",
                                             filetypes=load_script_filetypes)
        if name:
            text = files.import_script(name)
            text = files.strip_lines(text)
            textbox.delete("1.0", tk.END)
            textbox.insert(tk.INSERT, text)

    def export_script(self, textbox, window):
        name = tk.filedialog.asksaveasfilename(parent=window,
                                               initialdir=files.SCRIPT_PATH,
                                               title="Export script",
                                               filetypes=save_script_filetypes)
        if name:
            if files.SCRIPT_EXT not in name:
                name += files.SCRIPT_EXT
            text = textbox.get("1.0", tk.END)
            text = files.strip_lines(text)
            files.export_script(name, text)

    def popup(self, window, title, image, text, button_text, end_command=None):
        popup = tk.Toplevel(window)
        popup.resizable(False, False)
        if MAIN_ICON != None:
            if os.path.splitext(MAIN_ICON)[1].lower() == ".gif":
                dummy = None
                #popup.call('wm', 'iconphoto', popup._w, tk.PhotoImage(file=MAIN_ICON))
            else:
                popup.iconbitmap(MAIN_ICON)
        popup.wm_title(title)
        popup.tkraise(window)

        def run_end():
            popup.destroy()
            if end_command != None:
                end_command()

        picture_label = tk.Label(popup, image=image)
        picture_label.photo = image
        picture_label.grid(column=0, row=0, rowspan=2, padx=10, pady=10)
        tk.Label(popup, text=text, justify=tk.CENTER).grid(column=1, row=0, padx=10, pady=10)
        tk.Button(popup, text=button_text, command=run_end).grid(column=1, row=1, padx=10, pady=10)
        popup.wait_visibility()
        popup.grab_set()
        popup.wait_window()

    def popup_choice(self, window, title, image, text, choices):
        popup = tk.Toplevel(window)
        popup.resizable(False, False)
        if MAIN_ICON != None:
            if os.path.splitext(MAIN_ICON)[1].lower() == ".gif":
                dummy = None
                #popup.call('wm', 'iconphoto', popup._w, tk.PhotoImage(file=MAIN_ICON))
            else:
                popup.iconbitmap(MAIN_ICON)
        popup.wm_title(title)
        popup.tkraise(window)

        def run_end(func):
            popup.destroy()
            if func != None:
                func()

        picture_label = tk.Label(popup, image=image)
        picture_label.photo = image
        picture_label.grid(column=0, row=0, rowspan=2, padx=10, pady=10)
        tk.Label(popup, text=text, justify=tk.CENTER).grid(column=1, row=0, columnspan=len(choices), padx=10, pady=10)
        for idx, choice in enumerate(choices):
            run_end_func = partial(run_end, choice[1])
            tk.Button(popup, text=choice[0], command=run_end_func).grid(column=1 + idx, row=1, padx=10, pady=10)
        popup.wait_visibility()
        popup.grab_set()
        popup.wait_window()

    def modified_layout_save_prompt(self):
        if files.layout_changed_since_load == True:
            layout_empty = True
            for x_texts in scripts.text:
                for text in x_texts:
                    if text != "":
                        layout_empty = False
                        break

            if not layout_empty:
                self.popup_choice(self, "Save Changes?", self.warning_image, "You have made changes to this layout.\nWould you like to save this layout before exiting?", [["Save", self.save_layout], ["Save As...", self.save_layout_as], ["Discard", None]])

def make():
    global root
    global app
    global root_destroyed
    global redetect_before_start
    root = tk.Tk()
    theme.apply(root)
    root_destroyed = False
    root.protocol("WM_DELETE_WINDOW", close)
    root.resizable(False, False)
    if MAIN_ICON != None:
        if os.path.splitext(MAIN_ICON)[1].lower() == ".gif":
            root.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=MAIN_ICON))
        else:
            root.iconbitmap(MAIN_ICON)
    app = Main_Window(root)
    app.raise_above_all()
    if "--smoke-test" in sys.argv:
        app.after(300, close)
    else:
        app.after(100, app.connect_lp)
    app.mainloop()


def close():
    global root_destroyed, launchpad
    app.modified_layout_save_prompt()
    app.disconnect_lp()

    if not root_destroyed:
        root.destroy()
        root_destroyed = True
