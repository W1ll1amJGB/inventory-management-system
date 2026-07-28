# ============================================
# main.py (con mejoras: precio en selección y edición de movimientos)
# ============================================
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from fpdf import FPDF
import os
import re
import sys

from db_manager import InventoryManager

# ------------------------------------------------------------
# Configuración de colores y estilos (sin cambios)
# ------------------------------------------------------------
COLOR_FONDO = "#1a2634"
COLOR_TARJETA = "#2c3e50"
COLOR_BOTON = "#3498db"
COLOR_BOTON_ACTIVO = "#2980b9"
COLOR_TEXTO = "#ecf0f1"
COLOR_TEXTO_SECUNDARIO = "#bdc3c7"

FUENTE_TITULO = ("Arial", 32, "bold")
FUENTE_SUBTITULO = ("Arial", 18)
FUENTE_NORMAL = ("Arial", 14)
FUENTE_TARJETA_NUM = ("Arial", 36, "bold")
FUENTE_TARJETA_LABEL = ("Arial", 16)
FUENTE_BOTON = ("Arial", 16)

# ------------------------------------------------------------
# Ventana base para todas las secundarias (sin cambios)
# ------------------------------------------------------------
class VentanaSecundaria(tk.Toplevel):
    def __init__(self, main_app, manager, titulo):
        super().__init__(main_app)
        self.main_app = main_app
        self.manager = manager
        self.title(titulo)
        self.state('zoomed')
        self.configure(bg=COLOR_FONDO)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.bind("<Escape>", lambda e: self.cerrar())

        frame_superior = tk.Frame(self, bg=COLOR_FONDO)
        frame_superior.pack(fill=tk.X, padx=10, pady=5)
        btn_volver = tk.Button(frame_superior, text="🔙 Volver (ESC)", command=self.cerrar,
                               bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                               fg=COLOR_TEXTO, font=FUENTE_NORMAL)
        btn_volver.pack(side=tk.LEFT)

        separator = ttk.Separator(self, orient='horizontal')
        separator.pack(fill=tk.X, padx=10)

    def cerrar(self):
        self.main_app.mostrar()
        self.destroy()

# ------------------------------------------------------------
# Ventana de selección de producto con filtro (AHORA MUESTRA PRECIO)
# ------------------------------------------------------------
class SeleccionarProductoDialog(tk.Toplevel):
    def __init__(self, parent, manager, titulo="Seleccionar producto"):
        super().__init__(parent)
        self.manager = manager
        self.title(titulo)
        self.geometry("800x800")
        self.configure(bg=COLOR_FONDO)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.producto_seleccionado = None

        tk.Label(self, text="🔍 Buscar por nombre:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_filtro = tk.Entry(self, font=FUENTE_NORMAL)
        self.entry_filtro.pack(fill=tk.X, padx=10)
        self.entry_filtro.bind("<KeyRelease>", self.filtrar)

        self.listbox = tk.Listbox(self, font=FUENTE_NORMAL, bg=COLOR_TARJETA, fg=COLOR_TEXTO, height=12)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.listbox.bind("<Double-Button-1>", self.seleccionar)

        frame_botones = tk.Frame(self, bg=COLOR_FONDO)
        frame_botones.pack(pady=5)
        tk.Button(frame_botones, text="✅ Seleccionar", command=self.seleccionar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="❌ Cancelar", command=self.destroy,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(side=tk.LEFT, padx=5)

        self.cargar_productos()

    def cargar_productos(self, filtro_nombre=""):
        self.listbox.delete(0, tk.END)
        productos = self.manager.obtener_todos_productos(
            {"nombre": filtro_nombre} if filtro_nombre else None
        )
        self.productos = productos
        for p in productos:
            # MODIFICACIÓN: se muestra el precio junto al nombre
            self.listbox.insert(tk.END, f"📦 {p['nombre']} - ${p['precio']:.2f} (Stock: {p['cantidad']})")

    def filtrar(self, event=None):
        texto = self.entry_filtro.get()
        self.cargar_productos(texto)

    def seleccionar(self, event=None):
        seleccion = self.listbox.curselection()
        if seleccion:
            idx = seleccion[0]
            self.producto_seleccionado = self.productos[idx]
            self.destroy()
        else:
            messagebox.showwarning("Selección", "Por favor seleccione un producto.")

# ------------------------------------------------------------
# Ventana para añadir producto (sin cambios)
# ------------------------------------------------------------
class AddProductWindow(VentanaSecundaria):
    def __init__(self, main_app, manager):
        super().__init__(main_app, manager, "➕ Añadir Producto")
        self.frame = tk.Frame(self, bg=COLOR_FONDO)
        self.frame.pack(expand=True)

        tk.Label(self.frame, text="📛 Nombre:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_nombre = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_nombre.pack()

        tk.Label(self.frame, text="💰 Precio:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_precio = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_precio.pack()

        tk.Label(self.frame, text="🔢 Cantidad:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_cantidad = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_cantidad.pack()

        tk.Button(self.frame, text="💾 Guardar", command=self.guardar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON, width=20).pack(pady=10)

    def guardar(self):
        nombre = self.entry_nombre.get().strip()
        precio = self.entry_precio.get().strip()
        cantidad = self.entry_cantidad.get().strip()
        if not nombre or not precio or not cantidad:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return
        try:
            precio = float(precio)
            cantidad = int(cantidad)
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser número y cantidad entero")
            return
        self.manager.agregar_producto(nombre, precio, cantidad)
        messagebox.showinfo("Éxito", "✅ Producto agregado correctamente")
        self.entry_nombre.delete(0, tk.END)
        self.entry_precio.delete(0, tk.END)
        self.entry_cantidad.delete(0, tk.END)

# ------------------------------------------------------------
# Ventana para registrar entrada/venta (sin cambios, pero ya usa el diálogo modificado)
# ------------------------------------------------------------
class MovimientoWindow(VentanaSecundaria):
    def __init__(self, main_app, manager, tipo):
        emoji = "📥" if tipo == "entrada" else "📤"
        super().__init__(main_app, manager, f"{emoji} Registrar {tipo.capitalize()}")
        self.tipo = tipo
        self.producto = None

        self.frame = tk.Frame(self, bg=COLOR_FONDO)
        self.frame.pack(expand=True)

        tk.Label(self.frame, text="📦 Producto:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.btn_seleccionar = tk.Button(self.frame, text="🔍 Seleccionar producto", command=self.seleccionar_producto,
                                          bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                          fg=COLOR_TEXTO, font=FUENTE_BOTON, width=25)
        self.btn_seleccionar.pack()
        self.lbl_producto = tk.Label(self.frame, text="Ninguno seleccionado", bg=COLOR_FONDO,
                                     fg=COLOR_TEXTO_SECUNDARIO, font=FUENTE_NORMAL)
        self.lbl_producto.pack()

        tk.Label(self.frame, text="📅 Fecha (YYYY-MM-DD):", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_fecha = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entry_fecha.pack()

        tk.Label(self.frame, text="🔢 Cantidad:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_cantidad = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_cantidad.pack()

        tk.Button(self.frame, text="✅ Registrar", command=self.registrar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON, width=20).pack(pady=10)

    def seleccionar_producto(self):
        dlg = SeleccionarProductoDialog(self, self.manager, f"Seleccionar producto para {self.tipo}")
        self.wait_window(dlg)
        if dlg.producto_seleccionado:
            self.producto = dlg.producto_seleccionado
            self.lbl_producto.config(text=f"📦 {self.producto['nombre']} - ${self.producto['precio']:.2f} (Stock: {self.producto['cantidad']})",
                                     fg=COLOR_TEXTO)

    def registrar(self):
        if not self.producto:
            messagebox.showerror("Error", "Debe seleccionar un producto")
            return
        fecha = self.entry_fecha.get().strip()
        cantidad_str = self.entry_cantidad.get().strip()
        if not fecha or not cantidad_str:
            messagebox.showerror("Error", "Complete todos los campos")
            return
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
            messagebox.showerror("Error", "La fecha debe tener formato YYYY-MM-DD")
            return
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "La fecha no es válida")
            return
        try:
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Cantidad debe ser un entero positivo")
            return
        try:
            self.manager.registrar_movimiento(self.producto["id"], self.tipo, fecha, cantidad)
            messagebox.showinfo("Éxito", f"✅ {self.tipo.capitalize()} registrada correctamente")
            self.producto = None
            self.lbl_producto.config(text="Ninguno seleccionado", fg=COLOR_TEXTO_SECUNDARIO)
            self.entry_cantidad.delete(0, tk.END)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

# ------------------------------------------------------------
# Ventana para editar/eliminar producto (sin cambios, pero ya usa el diálogo modificado)
# ------------------------------------------------------------
class EditDeleteProductWindow(VentanaSecundaria):
    def __init__(self, main_app, manager):
        super().__init__(main_app, manager, "✏️ Editar / Eliminar Producto")
        self.producto = None

        self.frame = tk.Frame(self, bg=COLOR_FONDO)
        self.frame.pack(expand=True)

        tk.Label(self.frame, text="🔍 Seleccione producto:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.btn_seleccionar = tk.Button(self.frame, text="Elegir producto", command=self.seleccionar_producto,
                                          bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                          fg=COLOR_TEXTO, font=FUENTE_BOTON, width=20)
        self.btn_seleccionar.pack()
        self.lbl_producto = tk.Label(self.frame, text="Ninguno", bg=COLOR_FONDO, fg=COLOR_TEXTO_SECUNDARIO, font=FUENTE_NORMAL)
        self.lbl_producto.pack()

        tk.Label(self.frame, text="📛 Nuevo nombre:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_nombre = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_nombre.pack()
        self.entry_nombre.config(state=tk.DISABLED)

        tk.Label(self.frame, text="💰 Nuevo precio:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_precio = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_precio.pack()
        self.entry_precio.config(state=tk.DISABLED)

        tk.Label(self.frame, text="🔢 Nueva cantidad:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(pady=5)
        self.entry_cantidad = tk.Entry(self.frame, font=FUENTE_NORMAL, width=30)
        self.entry_cantidad.pack()
        self.entry_cantidad.config(state=tk.DISABLED)

        frame_botones = tk.Frame(self.frame, bg=COLOR_FONDO)
        frame_botones.pack(pady=10)
        tk.Button(frame_botones, text="💾 Actualizar", command=self.actualizar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="🗑️ Eliminar", command=self.eliminar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON, width=12).pack(side=tk.LEFT, padx=5)

    def seleccionar_producto(self):
        dlg = SeleccionarProductoDialog(self, self.manager, "Seleccionar producto para editar/eliminar")
        self.wait_window(dlg)
        if dlg.producto_seleccionado:
            self.producto = dlg.producto_seleccionado
            self.lbl_producto.config(text=f"📦 {self.producto['nombre']} - ${self.producto['precio']:.2f} (Stock: {self.producto['cantidad']})",
                                     fg=COLOR_TEXTO)
            self.entry_nombre.config(state=tk.NORMAL)
            self.entry_precio.config(state=tk.NORMAL)
            self.entry_cantidad.config(state=tk.NORMAL)
            self.entry_nombre.delete(0, tk.END)
            self.entry_nombre.insert(0, self.producto["nombre"])
            self.entry_precio.delete(0, tk.END)
            self.entry_precio.insert(0, str(self.producto["precio"]))
            self.entry_cantidad.delete(0, tk.END)
            self.entry_cantidad.insert(0, str(self.producto["cantidad"]))

    def actualizar(self):
        if not self.producto:
            messagebox.showerror("Error", "Seleccione un producto")
            return
        nombre = self.entry_nombre.get().strip()
        precio = self.entry_precio.get().strip()
        cantidad = self.entry_cantidad.get().strip()
        if not nombre or not precio or not cantidad:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return
        try:
            precio = float(precio)
            cantidad = int(cantidad)
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser número y cantidad entero")
            return
        self.manager.actualizar_producto(self.producto["id"], nombre, precio, cantidad)
        messagebox.showinfo("Éxito", "✅ Producto actualizado")
        self.producto = None
        self.lbl_producto.config(text="Ninguno", fg=COLOR_TEXTO_SECUNDARIO)
        self.entry_nombre.config(state=tk.DISABLED)
        self.entry_precio.config(state=tk.DISABLED)
        self.entry_cantidad.config(state=tk.DISABLED)
        self.entry_nombre.delete(0, tk.END)
        self.entry_precio.delete(0, tk.END)
        self.entry_cantidad.delete(0, tk.END)

    def eliminar(self):
        if not self.producto:
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar {self.producto['nombre']}?"):
            self.manager.eliminar_producto(self.producto["id"])
            messagebox.showinfo("Éxito", "🗑️ Producto eliminado")
            self.producto = None
            self.lbl_producto.config(text="Ninguno", fg=COLOR_TEXTO_SECUNDARIO)
            self.entry_nombre.config(state=tk.DISABLED)
            self.entry_precio.config(state=tk.DISABLED)
            self.entry_cantidad.config(state=tk.DISABLED)
            self.entry_nombre.delete(0, tk.END)
            self.entry_precio.delete(0, tk.END)
            self.entry_cantidad.delete(0, tk.END)

# ------------------------------------------------------------
# Ventana de inventario con filtros y PDF (sin cambios)
# ------------------------------------------------------------
class InventarioWindow(VentanaSecundaria):
    def __init__(self, main_app, manager):
        super().__init__(main_app, manager, "📋 Ver Inventario")

        frame_filtros = tk.Frame(self, bg=COLOR_FONDO)
        frame_filtros.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame_filtros, text="🔍 Nombre:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.entry_nombre = tk.Entry(frame_filtros, font=FUENTE_NORMAL)
        self.entry_nombre.grid(row=0, column=1, padx=5, pady=2)

        tk.Label(frame_filtros, text="💰 Precio min:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.entry_precio_min = tk.Entry(frame_filtros, width=10, font=FUENTE_NORMAL)
        self.entry_precio_min.grid(row=0, column=3, padx=5, pady=2)

        tk.Label(frame_filtros, text="💰 Precio max:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.entry_precio_max = tk.Entry(frame_filtros, width=10, font=FUENTE_NORMAL)
        self.entry_precio_max.grid(row=1, column=1, padx=5, pady=2)

        self.var_stock_cero = tk.BooleanVar()
        self.chk_stock_cero = ttk.Checkbutton(frame_filtros, text="📦 Solo stock cero", variable=self.var_stock_cero,
                                              style='My.TCheckbutton')
        self.chk_stock_cero.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('My.TCheckbutton', background=COLOR_FONDO, foreground=COLOR_TEXTO, font=FUENTE_NORMAL)

        tk.Button(frame_filtros, text="🔍 Aplicar Filtros", command=self.cargar_datos,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON).grid(row=2, column=0, columnspan=2, pady=5)
        tk.Button(frame_filtros, text="📄 Generar PDF", command=self.generar_pdf,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON).grid(row=2, column=2, columnspan=2, pady=5)

        estilo_tree = ttk.Style()
        estilo_tree.theme_use("clam")
        estilo_tree.configure("Treeview", background=COLOR_TARJETA, fieldbackground=COLOR_TARJETA,
                        foreground=COLOR_TEXTO, rowheight=30, font=FUENTE_NORMAL)
        estilo_tree.configure("Treeview.Heading", background=COLOR_BOTON, foreground=COLOR_TEXTO, font=FUENTE_NORMAL)

        self.tree = ttk.Treeview(self, columns=("nombre", "precio", "cantidad"), show="headings", height=15)
        self.tree.heading("nombre", text="📛 Nombre")
        self.tree.heading("precio", text="💰 Precio")
        self.tree.heading("cantidad", text="🔢 Cantidad")
        self.tree.column("nombre", width=300)
        self.tree.column("precio", width=150)
        self.tree.column("cantidad", width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.cargar_datos()

    def cargar_datos(self):
        filtros = {}
        nombre = self.entry_nombre.get().strip()
        if nombre:
            filtros["nombre"] = nombre
        try:
            precio_min = float(self.entry_precio_min.get()) if self.entry_precio_min.get().strip() else None
            if precio_min is not None:
                filtros["precio_min"] = precio_min
        except ValueError:
            messagebox.showerror("Error", "Precio mínimo debe ser un número")
            return
        try:
            precio_max = float(self.entry_precio_max.get()) if self.entry_precio_max.get().strip() else None
            if precio_max is not None:
                filtros["precio_max"] = precio_max
        except ValueError:
            messagebox.showerror("Error", "Precio máximo debe ser un número")
            return
        if self.var_stock_cero.get():
            filtros["stock_cero"] = True

        productos = self.manager.obtener_todos_productos(filtros)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in productos:
            self.tree.insert("", tk.END, values=(p["nombre"], f"${p['precio']:.2f}", p["cantidad"]))
        self.productos_actuales = productos

    def generar_pdf(self):
        if not hasattr(self, 'productos_actuales') or not self.productos_actuales:
            messagebox.showinfo("PDF", "No hay productos para generar PDF")
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            pdf.cell(200, 10, txt="Reporte de Inventario", ln=True, align='C')
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Generado: {fecha_actual}", ln=True, align='C')
            pdf.ln(10)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(80, 10, "Nombre", border=1)
            pdf.cell(40, 10, "Precio", border=1)
            pdf.cell(40, 10, "Cantidad", border=1)
            pdf.ln()
            pdf.set_font("Arial", '', 12)
            for p in self.productos_actuales:
                pdf.cell(80, 10, p["nombre"], border=1)
                pdf.cell(40, 10, f"${p['precio']:.2f}", border=1)
                pdf.cell(40, 10, str(p["cantidad"]), border=1)
                pdf.ln()
            nombre_archivo = "inventario.pdf"
            pdf.output(nombre_archivo)
            try:
                if os.name == 'nt':
                    os.startfile(nombre_archivo)
                elif os.name == 'posix':
                    if sys.platform == 'darwin':
                        os.system(f'open "{nombre_archivo}"')
                    else:
                        os.system(f'xdg-open "{nombre_archivo}"')
            except Exception as e:
                messagebox.showwarning("Abrir PDF", f"El PDF se generó pero no se pudo abrir automáticamente.\n{nombre_archivo}")
            messagebox.showinfo("PDF", f"✅ PDF generado y abierto: {os.path.abspath(nombre_archivo)}")
        except Exception as e:
            messagebox.showerror("Error al generar PDF", f"No se pudo generar el PDF.\nAsegúrate de tener instalada la librería fpdf.\nDetalles: {e}")

# ------------------------------------------------------------
# Diálogo para editar/eliminar un movimiento (NUEVO)
# ------------------------------------------------------------
class EditMovimientoDialog(tk.Toplevel):
    def __init__(self, parent, manager, movimiento_id, tipo, callback_actualizar):
        super().__init__(parent)
        self.manager = manager
        self.movimiento_id = movimiento_id
        self.tipo = tipo
        self.callback = callback_actualizar
        self.title(f"✏️ Editar {tipo.capitalize()}")
        self.geometry("600x350")
        self.configure(bg=COLOR_FONDO)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Obtener datos del movimiento
        self.movimiento = self.manager.obtener_movimiento(movimiento_id)
        if not self.movimiento:
            messagebox.showerror("Error", "No se encontró el movimiento")
            self.destroy()
            return

        # Variables
        self.nueva_cantidad = tk.IntVar(value=self.movimiento["cantidad"])
        self.nueva_fecha = tk.StringVar(value=self.movimiento["fecha"])

        # Widgets
        frame = tk.Frame(self, bg=COLOR_FONDO)
        frame.pack(expand=True, padx=20, pady=20)

        # Mostrar producto (solo lectura)
        tk.Label(frame, text="📦 Producto:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=0, column=0, sticky=tk.W, pady=5)
        tk.Label(frame, text=self.movimiento["producto_nombre"], bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=0, column=1, sticky=tk.W, pady=5)

        # Tipo (solo lectura)
        tk.Label(frame, text="📌 Tipo:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=1, column=0, sticky=tk.W, pady=5)
        tk.Label(frame, text=self.movimiento["tipo"].capitalize(), bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=1, column=1, sticky=tk.W, pady=5)

        # Cantidad actual
        tk.Label(frame, text="🔢 Cantidad actual:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=2, column=0, sticky=tk.W, pady=5)
        tk.Label(frame, text=str(self.movimiento["cantidad"]), bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Nueva cantidad
        tk.Label(frame, text="🔢 Nueva cantidad:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=3, column=0, sticky=tk.W, pady=5)
        spin_cantidad = tk.Spinbox(frame, from_=1, to=10000, textvariable=self.nueva_cantidad, font=FUENTE_NORMAL, width=10)
        spin_cantidad.grid(row=3, column=1, sticky=tk.W, pady=5)

        # Fecha
        tk.Label(frame, text="📅 Fecha (YYYY-MM-DD):", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).grid(row=4, column=0, sticky=tk.W, pady=5)
        entry_fecha = tk.Entry(frame, textvariable=self.nueva_fecha, font=FUENTE_NORMAL, width=15)
        entry_fecha.grid(row=4, column=1, sticky=tk.W, pady=5)

        # Botones
        frame_botones = tk.Frame(frame, bg=COLOR_FONDO)
        frame_botones.grid(row=5, column=0, columnspan=2, pady=20)

        tk.Button(frame_botones, text="💾 Guardar cambios", command=self.guardar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_NORMAL, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="🗑️ Eliminar movimiento", command=self.eliminar,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_NORMAL, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="❌ Cancelar", command=self.destroy,
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_NORMAL, width=10).pack(side=tk.LEFT, padx=5)

    def guardar(self):
        nueva_cant = self.nueva_cantidad.get()
        nueva_fecha = self.nueva_fecha.get().strip()

        # Validar fecha
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', nueva_fecha):
            messagebox.showerror("Error", "La fecha debe tener formato YYYY-MM-DD")
            return
        try:
            datetime.strptime(nueva_fecha, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "La fecha no es válida")
            return

        # Validar cantidad positiva
        if nueva_cant <= 0:
            messagebox.showerror("Error", "La cantidad debe ser un entero positivo")
            return

        try:
            self.manager.actualizar_movimiento(self.movimiento_id, nueva_cant, nueva_fecha)
            messagebox.showinfo("Éxito", "✅ Movimiento actualizado correctamente")
            self.callback()  # Refrescar la lista
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def eliminar(self):
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este movimiento?\nEsta acción no se puede deshacer."):
            try:
                self.manager.eliminar_movimiento(self.movimiento_id)
                messagebox.showinfo("Éxito", "🗑️ Movimiento eliminado")
                self.callback()
                self.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

# ------------------------------------------------------------
# Ventana de historial (MODIFICADA: ahora permite editar/eliminar)
# ------------------------------------------------------------
class HistorialWindow(VentanaSecundaria):
    def __init__(self, main_app, manager):
        super().__init__(main_app, manager, "📜 Historial de Movimientos")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_entradas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_entradas, text="📥 Entradas")
        self._crear_pestanna(self.tab_entradas, "entrada")

        self.tab_ventas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ventas, text="📤 Ventas")
        self._crear_pestanna(self.tab_ventas, "venta")

    def _crear_pestanna(self, parent, tipo):
        mes_var = tk.StringVar()

        frame_sel = tk.Frame(parent, bg=COLOR_FONDO)
        frame_sel.pack(fill=tk.X, pady=5)

        tk.Label(frame_sel, text="📅 Seleccionar mes:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=FUENTE_NORMAL).pack(side=tk.LEFT, padx=5)
        cb_mes = ttk.Combobox(frame_sel, textvariable=mes_var, state="readonly", font=FUENTE_NORMAL, width=10)
        cb_mes.pack(side=tk.LEFT, padx=5)
        tk.Button(frame_sel, text="🔍 Ver", command=lambda: self.cargar_movimientos(tipo, mes_var.get(), parent),
                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                  fg=COLOR_TEXTO, font=FUENTE_BOTON).pack(side=tk.LEFT, padx=5)

        # Treeview
        tree = ttk.Treeview(parent, columns=("producto", "fecha", "cantidad"), show="headings", height=12)
        tree.heading("producto", text="📦 Producto")
        tree.heading("fecha", text="📅 Fecha")
        tree.heading("cantidad", text="🔢 Cantidad")
        tree.column("producto", width=250)
        tree.column("fecha", width=120)
        tree.column("cantidad", width=100)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Frame para botones de acción
        frame_acciones = tk.Frame(parent, bg=COLOR_FONDO)
        frame_acciones.pack(fill=tk.X, pady=5)

        btn_editar = tk.Button(frame_acciones, text="✏️ Editar", command=lambda: self.editar_movimiento(tree, tipo),
                               bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                               fg=COLOR_TEXTO, font=FUENTE_NORMAL, width=10)
        btn_editar.pack(side=tk.LEFT, padx=5)

        btn_eliminar = tk.Button(frame_acciones, text="🗑️ Eliminar", command=lambda: self.eliminar_movimiento(tree, tipo),
                                 bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                 fg=COLOR_TEXTO, font=FUENTE_NORMAL, width=10)
        btn_eliminar.pack(side=tk.LEFT, padx=5)

        # Guardar referencias
        parent.cb_mes = cb_mes
        parent.tree = tree
        parent.tipo = tipo

        # Cargar meses disponibles
        meses = self.manager.obtener_meses_con_movimientos(tipo)
        cb_mes['values'] = meses
        if meses:
            cb_mes.current(0)
            self.cargar_movimientos(tipo, meses[0], parent)

    def cargar_movimientos(self, tipo, mes, parent):
        if not mes:
            messagebox.showwarning("Selección", "Debe seleccionar un mes")
            return
        movimientos = self.manager.obtener_movimientos_por_mes(tipo, mes)
        tree = parent.tree
        # Limpiar tree
        for row in tree.get_children():
            tree.delete(row)
        # Insertar con el ID del movimiento como iid
        for mov in movimientos:
            tree.insert("", tk.END, iid=str(mov["id"]), values=(mov["producto"], mov["fecha"], mov["cantidad"]))

    def editar_movimiento(self, tree, tipo):
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor seleccione un movimiento")
            return
        movimiento_id = int(seleccion[0])
        # Abrir diálogo de edición
        dlg = EditMovimientoDialog(self, self.manager, movimiento_id, tipo,
                                   callback_actualizar=lambda: self.actualizar_pestana_actual())
        self.wait_window(dlg)

    def eliminar_movimiento(self, tree, tipo):
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor seleccione un movimiento")
            return
        movimiento_id = int(seleccion[0])
        if messagebox.askyesno("Confirmar", "¿Eliminar este movimiento?"):
            try:
                self.manager.eliminar_movimiento(movimiento_id)
                messagebox.showinfo("Éxito", "Movimiento eliminado")
                self.actualizar_pestana_actual()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def actualizar_pestana_actual(self):
        """Recarga los movimientos de la pestaña actual."""
        pestana_actual = self.notebook.nametowidget(self.notebook.select())
        tipo = pestana_actual.tipo
        mes = pestana_actual.cb_mes.get()
        self.cargar_movimientos(tipo, mes, pestana_actual)

# ------------------------------------------------------------
# Clase principal (dashboard) - SIN CAMBIOS
# ------------------------------------------------------------
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📦 Sistema de Control de Inventario")
        self.state('zoomed')
        self.configure(bg=COLOR_FONDO)
        self.resizable(True, True)

        self.manager = InventoryManager()

        main_frame = tk.Frame(self, bg=COLOR_FONDO)
        main_frame.pack(expand=True, fill=tk.BOTH)

        top_frame = tk.Frame(main_frame, bg=COLOR_FONDO)
        top_frame.pack(expand=True, fill=tk.BOTH)

        titulo = tk.Label(top_frame, text="SISTEMA DE CONTROL DE INVENTARIO",
                          font=FUENTE_TITULO, bg=COLOR_FONDO, fg=COLOR_TEXTO)
        titulo.pack(pady=(50, 5))

        subtitulo = tk.Label(top_frame, text="Gestiona tu inventario de manera eficiente",
                             font=FUENTE_SUBTITULO, bg=COLOR_FONDO, fg=COLOR_TEXTO_SECUNDARIO)
        subtitulo.pack(pady=(0, 40))

        frame_tarjetas = tk.Frame(top_frame, bg=COLOR_FONDO)
        frame_tarjetas.pack(pady=20)

        total_prod, stock_total, valor_total = self.manager.obtener_resumen()

        self.card1 = self._crear_tarjeta(frame_tarjetas, "📦 Productos", str(total_prod), 0)
        self.card2 = self._crear_tarjeta(frame_tarjetas, "📊 Stock Total", f"{stock_total} und", 1)
        self.card3 = self._crear_tarjeta(frame_tarjetas, "💰 Valor Total", f"${valor_total:,.2f}", 2)

        button_frame = tk.Frame(main_frame, bg=COLOR_FONDO)
        button_frame.pack(side=tk.BOTTOM, pady=30)

        for i in range(3):
            button_frame.columnconfigure(i, weight=1)

        btn_add = tk.Button(button_frame, text="➕ Añadir Producto", command=self.abrir_add_producto,
                            bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                            fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_add.grid(row=0, column=0, padx=10, pady=5)

        btn_entrada = tk.Button(button_frame, text="📥 Registrar Entrada", command=self.abrir_entrada,
                                bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_entrada.grid(row=0, column=1, padx=10, pady=5)

        btn_venta = tk.Button(button_frame, text="📤 Registrar Venta", command=self.abrir_venta,
                              bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                              fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_venta.grid(row=0, column=2, padx=10, pady=5)

        button_frame.rowconfigure(1, minsize=30)

        btn_edit = tk.Button(button_frame, text="✏️ Editar / Eliminar", command=self.abrir_edit_delete,
                             bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                             fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_edit.grid(row=2, column=0, padx=10, pady=5)

        btn_inventario = tk.Button(button_frame, text="📋 Ver Inventario", command=self.abrir_inventario,
                                   bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                   fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_inventario.grid(row=2, column=1, padx=10, pady=5)

        btn_historial = tk.Button(button_frame, text="📜 Ver Historial", command=self.abrir_historial,
                                  bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                                  fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_historial.grid(row=2, column=2, padx=10, pady=5)

        button_frame.rowconfigure(3, minsize=30)

        btn_salir = tk.Button(button_frame, text="❌ Salir", command=self.quit,
                              bg=COLOR_BOTON, activebackground=COLOR_BOTON_ACTIVO,
                              fg=COLOR_TEXTO, font=FUENTE_BOTON, width=18, height=2, relief=tk.FLAT)
        btn_salir.grid(row=4, column=1, padx=10, pady=5)

        self.bind("<Escape>", lambda e: self.quit())

    def _crear_tarjeta(self, parent, label, valor, columna):
        card = tk.Frame(parent, bg=COLOR_TARJETA, padx=40, pady=25)
        card.grid(row=0, column=columna, padx=25)

        lbl_label = tk.Label(card, text=label, bg=COLOR_TARJETA, fg=COLOR_TEXTO_SECUNDARIO,
                             font=FUENTE_TARJETA_LABEL)
        lbl_label.pack()

        lbl_valor = tk.Label(card, text=valor, bg=COLOR_TARJETA, fg=COLOR_TEXTO,
                             font=FUENTE_TARJETA_NUM)
        lbl_valor.pack()

        return lbl_valor

    def ocultar(self):
        self.withdraw()

    def mostrar(self):
        total_prod, stock_total, valor_total = self.manager.obtener_resumen()
        self.card1.config(text=str(total_prod))
        self.card2.config(text=f"{stock_total} und")
        self.card3.config(text=f"${valor_total:,.2f}")
        self.deiconify()
        self.state('zoomed')

    def abrir_add_producto(self):
        self.ocultar()
        AddProductWindow(self, self.manager)

    def abrir_entrada(self):
        self.ocultar()
        MovimientoWindow(self, self.manager, "entrada")

    def abrir_venta(self):
        self.ocultar()
        MovimientoWindow(self, self.manager, "venta")

    def abrir_edit_delete(self):
        self.ocultar()
        EditDeleteProductWindow(self, self.manager)

    def abrir_inventario(self):
        self.ocultar()
        InventarioWindow(self, self.manager)

    def abrir_historial(self):
        self.ocultar()
        HistorialWindow(self, self.manager)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()