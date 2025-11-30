import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from PIL import Image, ImageTk
import json, os, sys

CONJUNTOS_FILE = "conjuntos.json"
CATEGORIAS = ["chaqueta", "camisa", "accesorio", "pantalon", "zapatos"]
IMG_SIZE = (160, 160)
SLOT_WIDTH = 240
SLOT_HEIGHT = 220

BG_MAIN = "#fff0f6"
FRAME_BG = "#ffe6f0"
SLOT_BG = "#ffd6e8"
BTN_BG = "#ffb6d5"
BTN_ACTIVE = "#ff9fcf"
TEXT_COLOR = "#5a2b3a"

class ArmarioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Creador de outfits")
        self.root.geometry("840x840")

        try:
            self.root.state("zoomed")
        except Exception:
            pass

        # Ajustar tamaño de la ventana para que no supere la pantalla
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # dejar un margen para la barra de tareas y bordes
        max_w = max(400, min(840, screen_w - 40))
        max_h = max(400, min(840, screen_h - 80))
        self.root.geometry(f"{max_w}x{max_h}")
        # permitir redimensionar con un minumo
        self.root.minsize(840, 600)

        self.root.configure(bg=BG_MAIN)

        # Datos
        self.prendas = {cat: [] for cat in CATEGORIAS}
        self.prendas_nombres = {cat: [] for cat in CATEGORIAS}
        self.indices = {cat: None for cat in CATEGORIAS}  # None = slot no añadido / vacío

        # Widgets por categoría
        self.slot_frames = {}
        self.name_row = {}
        self.lbl_name = {}
        self.btn_x = {}
        self.btn_add = {}
        self.btn_prev = {}
        self.img_label = {}
        self.btn_next = {}

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass
        style.configure("TCombobox", fieldbackground=FRAME_BG, background=FRAME_BG, foreground=TEXT_COLOR)

        canvas = tk.Canvas(self.root, bg=BG_MAIN, highlightthickness=0)
        v_scroll = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        h_scroll = tk.Scrollbar(self.root, orient="horizontal", command=canvas.xview)

        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        # Frame interior donde se colocará todo el contenido
        content_frame = tk.Frame(canvas, bg=BG_MAIN)
        content_frame_id = canvas.create_window((0,0), window=content_frame, anchor="nw")

        # Actualizar el scrollregion cuando cambie el tamaño del contenido
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content_frame.bind("<Configure>", _on_frame_configure)

        # Ajustar el canvas cuando la ventana cambie de tamaño (mantener ancho)
        def _on_root_resize(event):
            # opcional: fijar el ancho del content_frame al ancho del canvas
            canvas.itemconfig(content_frame_id, width=canvas.winfo_width())
        self.root.bind("<Configure>", _on_root_resize)

        # Usar content_frame en lugar de main_frame para crear filas y slots
        main_frame = content_frame


        # Top row: chaqueta | camisa | accesorio
        top_row = tk.Frame(main_frame, bg=BG_MAIN)
        top_row.pack(pady=8)
        self._create_slot(parent=top_row, cat="chaqueta")
        self._create_slot(parent=top_row, cat="camisa")
        self._create_slot(parent=top_row, cat="accesorio")

        # Mid row: pantalon centered
        mid_row = tk.Frame(main_frame, bg=BG_MAIN)
        mid_row.pack(pady=18)
        self._create_slot(parent=mid_row, cat="pantalon", center=True)

        # Bottom row: zapatos centered
        bottom_row = tk.Frame(main_frame, bg=BG_MAIN)
        bottom_row.pack(pady=8)
        self._create_slot(parent=bottom_row, cat="zapatos", center=True)

        # Controls
        controls = tk.Frame(main_frame, bg=BG_MAIN)
        controls.pack(pady=12)
        btn_guardar = tk.Button(controls, text="Guardar outfit", command=self.guardar_conjunto,
                                bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        btn_guardar.grid(row=0, column=0, padx=6)
        self.combo = ttk.Combobox(controls, state="readonly", width=36)
        self.combo.grid(row=0, column=1, padx=6)
        btn_cargar = tk.Button(controls, text="Mostrar", command=self.cargar_conjunto,
                               bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        btn_cargar.grid(row=0, column=2, padx=6)
        btn_eliminar = tk.Button(controls, text="Eliminar", command=self.eliminar_conjunto,
                                 bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        btn_eliminar.grid(row=0, column=3, padx=6)

        # Cargar prendas y lista de conjuntos al iniciar (pero mantener slots vacíos)
        self.cargar_prendas_auto()
        self.cargar_lista_conjuntos()

    def _create_slot(self, parent, cat, center=False):
        # Frame del slot con tamaño fijo para que no se encoja al desinicializar
        frame = tk.Frame(parent, bg=FRAME_BG, bd=0, relief="flat", width=SLOT_WIDTH, height=SLOT_HEIGHT)
        frame.pack_propagate(False)
        if center:
            frame.pack(anchor="center", pady=4)
        else:
            frame.pack(side="left", padx=14, pady=4)
        self.slot_frames[cat] = frame

        # Nombre del slot (siempre visible)
        name_row = tk.Frame(frame, bg=FRAME_BG)
        name_row.pack(anchor="n", pady=(8,4))
        lbl = tk.Label(name_row, text=cat.capitalize(), bg=FRAME_BG, fg=TEXT_COLOR, font=("Helvetica", 10, "bold"))
        lbl.pack(side="left")
        self.name_row[cat] = name_row
        self.lbl_name[cat] = lbl

        # Botón + (ahora junto al nombre y con el mismo estilo que 'x')
        btn_add = tk.Button(name_row, text="+", width=3, command=lambda c=cat: self.add_slot(c),
                            bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        btn_add.pack(side="left", padx=(8,0))  # junto al nombre
        self.btn_add[cat] = btn_add

        # Botón x (oculto inicialmente; se mostrará junto al nombre cuando el slot esté añadido)
        btn_x = tk.Button(name_row, text="x", width=3, command=lambda c=cat: self.remove_slot(c),
                          bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        # no lo mostramos ahora; se mostrará en _set_slot_state cuando corresponda
        self.btn_x[cat] = btn_x

        # Contenedor de imagen con espacio reservado (mantiene espacio aunque esté vacío)
        img_row = tk.Frame(frame, bg=FRAME_BG)
        img_row.pack(anchor="center", pady=(6,6), expand=True)
        btn_prev = tk.Button(img_row, text="<", width=3, command=lambda c=cat: self.prev(c),
                             bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)
        lbl_img = tk.Label(img_row, bg=SLOT_BG, text="(vacío)", fg=TEXT_COLOR)
        btn_next = tk.Button(img_row, text=">", width=3, command=lambda c=cat: self.next(c),
                             bg=BTN_BG, activebackground=BTN_ACTIVE, fg=TEXT_COLOR)

        # Guardar referencias; no packear prev/img/next yet
        self.btn_prev[cat] = btn_prev
        self.img_label[cat] = lbl_img
        self.btn_next[cat] = btn_next

        # Inicial: slot vacío -> ocultar x, prev, next, imagen
        self._set_slot_state(cat, added=False)

    def _set_slot_state(self, cat, added):
        """
        Controla visibilidad:
        - added == False: mostrar nombre + btn_add
        - added == True: mostrar nombre + btn_x, y debajo prev + imagen + next
        """
        # Asegurar que el name_row (nombre) esté visible
        if not self.name_row[cat].winfo_ismapped():
            self.name_row[cat].pack(anchor="n", pady=(8,4))

        if added:
            # ocultar + (estaba junto al nombre)
            if self.btn_add[cat].winfo_ismapped():
                self.btn_add[cat].pack_forget()
            # mostrar botón x junto al nombre (si no está ya)
            if not self.btn_x[cat].winfo_ismapped():
                self.btn_x[cat].pack(side="left", padx=(8,0))
            # mostrar prev, imagen y next (empaquetar en el img_row)
            img_parent = self.img_label[cat].master  # el frame img_row
            # pack prev, img_label, next si no están visibles
            if not self.btn_prev[cat].winfo_ismapped():
                self.btn_prev[cat].pack(side="left")
            if not self.img_label[cat].winfo_ismapped():
                # configurar texto vacío antes de asignar imagen
                self.img_label[cat].config(text="(vacío)")
                self.img_label[cat].pack(side="left", padx=8)
            if not self.btn_next[cat].winfo_ismapped():
                self.btn_next[cat].pack(side="left")
        else:
            # ocultar x si está visible
            if self.btn_x[cat].winfo_ismapped():
                self.btn_x[cat].pack_forget()
            # ocultar prev, imagen, next si están visibles
            if self.btn_prev[cat].winfo_ismapped():
                self.btn_prev[cat].pack_forget()
            if self.img_label[cat].winfo_ismapped():
                self.img_label[cat].pack_forget()
            if self.btn_next[cat].winfo_ismapped():
                self.btn_next[cat].pack_forget()
            # mostrar + junto al nombre (si no está visible)
            if not self.btn_add[cat].winfo_ismapped():
                self.btn_add[cat].pack(side="left", padx=(8,0))
            # asegurar que la imagen-label no tenga imagen
            self.img_label[cat].config(image="", text="(vacío)")

    def cargar_prendas_auto(self):
        carpeta_base = "ropa"
        if not os.path.exists(carpeta_base):
            # no romper si no existe; slots quedan vacíos
            return

        for cat in CATEGORIAS:
            self.prendas[cat] = []
            self.prendas_nombres[cat] = []
            carpeta_cat = os.path.join(carpeta_base, cat)
            if os.path.exists(carpeta_cat):
                for archivo in sorted(os.listdir(carpeta_cat)):
                    ruta = os.path.join(carpeta_cat, archivo)
                    if os.path.isfile(ruta) and archivo.lower().endswith((".png", ".jpg", ".jpeg")):
                        try:
                            img = Image.open(ruta).resize(IMG_SIZE)
                            tk_img = ImageTk.PhotoImage(img)
                            self.prendas[cat].append(tk_img)
                            self.prendas_nombres[cat].append(archivo)
                        except Exception:
                            pass
            # mantener slots vacíos al iniciar
            self.indices[cat] = None
            self._set_slot_state(cat, added=False)

    def mostrar(self, cat):
        """Muestra la imagen si el slot está añadido; si no, deja texto '(vacío)'."""
        if self.indices[cat] is not None and self.prendas[cat]:
            idx = self.indices[cat] % len(self.prendas[cat])
            self.img_label[cat].config(image=self.prendas[cat][idx], text="")
            self.img_label[cat].image = self.prendas[cat][idx]
        else:
            self.img_label[cat].config(image="", text="(vacío)")

    def add_slot(self, cat):
        """Activa el slot: pone la primera prenda y cambia controles."""
        if self.prendas[cat]:
            self.indices[cat] = 0
            self._set_slot_state(cat, added=True)
            self.mostrar(cat)

    def remove_slot(self, cat):
        """Vacía el slot y vuelve al estado inicial (mostrar + junto al nombre)."""
        self.indices[cat] = None
        self._set_slot_state(cat, added=False)

    def prev(self, cat):
        if self.indices[cat] is not None and self.prendas[cat]:
            self.indices[cat] = (self.indices[cat] - 1) % len(self.prendas[cat])
            self.mostrar(cat)

    def next(self, cat):
        if self.indices[cat] is not None and self.prendas[cat]:
            self.indices[cat] = (self.indices[cat] + 1) % len(self.prendas[cat])
            self.mostrar(cat)

    def guardar_conjunto(self):
        nombre = simpledialog.askstring("Guardar", "Nombre del conjunto:")
        if not nombre:
            return
        conjunto = {
            "nombre": nombre,
            "archivos": {
                cat: (self.prendas_nombres[cat][self.indices[cat]] if self.indices[cat] is not None else None)
                for cat in CATEGORIAS
            }
        }
        data = []
        if os.path.exists(CONJUNTOS_FILE) and os.path.getsize(CONJUNTOS_FILE) > 0:
            try:
                with open(CONJUNTOS_FILE, "r") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    data = []
            except:
                data = []
        data.append(conjunto)
        with open(CONJUNTOS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        self.combo["values"] = [c["nombre"] for c in data]
        self.combo.set(nombre)
        messagebox.showinfo("Guardado", f"Conjunto '{nombre}' guardado correctamente")

    def cargar_lista_conjuntos(self):
        if os.path.exists(CONJUNTOS_FILE) and os.path.getsize(CONJUNTOS_FILE) > 0:
            try:
                with open(CONJUNTOS_FILE, "r") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    self.combo["values"] = [c["nombre"] for c in data]
                    self.combo.set(self.combo["values"][0])
            except:
                pass

    def cargar_conjunto(self):
        if not os.path.exists(CONJUNTOS_FILE) or os.path.getsize(CONJUNTOS_FILE) == 0:
            return
        with open(CONJUNTOS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return
        nombre = self.combo.get()
        if not nombre:
            return
        for c in data:
            if c["nombre"] == nombre:
                for cat in CATEGORIAS:
                    archivo = c["archivos"].get(cat)
                    if archivo and archivo in self.prendas_nombres[cat]:
                        idx = self.prendas_nombres[cat].index(archivo)
                        self.indices[cat] = idx
                        self._set_slot_state(cat, added=True)
                        self.mostrar(cat)
                    else:
                        self.indices[cat] = None
                        self._set_slot_state(cat, added=False)
                messagebox.showinfo("Cargado", f"Conjunto '{nombre}' cargado")
                return

    def eliminar_conjunto(self):
        if not os.path.exists(CONJUNTOS_FILE) or os.path.getsize(CONJUNTOS_FILE) == 0:
            return
        with open(CONJUNTOS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return
        nombre = self.combo.get()
        if not nombre:
            return
        data = [c for c in data if c["nombre"] != nombre]
        with open(CONJUNTOS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        if data:
            self.combo["values"] = [c["nombre"] for c in data]
            self.combo.set(self.combo["values"][0])
        else:
            self.combo["values"] = []
            self.combo.set("")
        messagebox.showinfo("Eliminado", f"Conjunto '{nombre}' eliminado")

if __name__ == "__main__":
    root = tk.Tk()
    app = ArmarioApp(root)
    root.mainloop()
