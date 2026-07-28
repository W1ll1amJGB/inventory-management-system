# ============================================
# db_manager.py (con nuevos métodos para movimientos)
# ============================================
from database import Database

class InventoryManager:
    """Clase que gestiona todas las operaciones de inventario."""
    def __init__(self, db_path="inventario.db"):
        self.db = Database(db_path)

    # ---------- Productos ----------
    def agregar_producto(self, nombre, precio, cantidad):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO productos (nombre, precio, cantidad) VALUES (?, ?, ?)",
                (nombre, precio, cantidad)
            )
            conn.commit()
            return cursor.lastrowid

    def obtener_producto(self, producto_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, precio, cantidad FROM productos WHERE id = ?", (producto_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "nombre": row[1], "precio": row[2], "cantidad": row[3]}
            return None

    def obtener_todos_productos(self, filtros=None):
        """
        Filtros: diccionario con claves:
            nombre (str): texto a buscar en nombre (like)
            precio_min (float)
            precio_max (float)
            stock_cero (bool): si es True, solo productos con cantidad = 0
        """
        sql = "SELECT id, nombre, precio, cantidad FROM productos WHERE 1=1"
        params = []
        if filtros:
            if filtros.get("nombre"):
                sql += " AND nombre LIKE ?"
                params.append(f"%{filtros['nombre']}%")
            if filtros.get("precio_min") is not None:
                sql += " AND precio >= ?"
                params.append(filtros["precio_min"])
            if filtros.get("precio_max") is not None:
                sql += " AND precio <= ?"
                params.append(filtros["precio_max"])
            if filtros.get("stock_cero"):
                sql += " AND cantidad = 0"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [{"id": r[0], "nombre": r[1], "precio": r[2], "cantidad": r[3]} for r in rows]

    def actualizar_producto(self, producto_id, nombre=None, precio=None, cantidad=None):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Obtener valores actuales
            cursor.execute("SELECT nombre, precio, cantidad FROM productos WHERE id = ?", (producto_id,))
            actual = cursor.fetchone()
            if not actual:
                return False
            nuevo_nombre = nombre if nombre is not None else actual[0]
            nuevo_precio = precio if precio is not None else actual[1]
            nueva_cantidad = cantidad if cantidad is not None else actual[2]
            cursor.execute(
                "UPDATE productos SET nombre = ?, precio = ?, cantidad = ? WHERE id = ?",
                (nuevo_nombre, nuevo_precio, nueva_cantidad, producto_id)
            )
            conn.commit()
            return True

    def eliminar_producto(self, producto_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ---------- Movimientos ----------
    def registrar_movimiento(self, producto_id, tipo, fecha, cantidad):
        """
        tipo: 'entrada' o 'venta'
        Actualiza el stock del producto y registra el movimiento.
        """
        if tipo not in ('entrada', 'venta'):
            raise ValueError("El tipo debe ser 'entrada' o 'venta'")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Verificar producto y stock suficiente si es venta
            cursor.execute("SELECT cantidad FROM productos WHERE id = ?", (producto_id,))
            stock_actual = cursor.fetchone()
            if not stock_actual:
                return False
            if tipo == 'venta' and stock_actual[0] < cantidad:
                raise ValueError("Stock insuficiente para realizar la venta")
            # Insertar movimiento
            cursor.execute(
                "INSERT INTO movimientos (producto_id, tipo, fecha, cantidad) VALUES (?, ?, ?, ?)",
                (producto_id, tipo, fecha, cantidad)
            )
            # Actualizar stock
            nuevo_stock = stock_actual[0] + cantidad if tipo == 'entrada' else stock_actual[0] - cantidad
            cursor.execute(
                "UPDATE productos SET cantidad = ? WHERE id = ?",
                (nuevo_stock, producto_id)
            )
            conn.commit()
            return True

    # ---------- Nuevos métodos para editar/eliminar movimientos ----------
    def obtener_movimiento(self, movimiento_id):
        """Devuelve los datos de un movimiento específico."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.id, m.producto_id, p.nombre, m.tipo, m.fecha, m.cantidad
                FROM movimientos m
                JOIN productos p ON m.producto_id = p.id
                WHERE m.id = ?
            """, (movimiento_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "producto_id": row[1],
                    "producto_nombre": row[2],
                    "tipo": row[3],
                    "fecha": row[4],
                    "cantidad": row[5]
                }
            return None

    def actualizar_movimiento(self, movimiento_id, nueva_cantidad, nueva_fecha):
        """
        Actualiza la cantidad y/o fecha de un movimiento existente.
        Ajusta el stock del producto correspondiente.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Obtener movimiento actual
            cursor.execute("SELECT producto_id, tipo, cantidad FROM movimientos WHERE id = ?", (movimiento_id,))
            mov = cursor.fetchone()
            if not mov:
                return False
            producto_id, tipo, cantidad_actual = mov

            # Obtener stock actual del producto
            cursor.execute("SELECT cantidad FROM productos WHERE id = ?", (producto_id,))
            stock_actual = cursor.fetchone()[0]

            # Calcular nuevo stock según el tipo
            if tipo == 'venta':
                # stock antes del movimiento = stock_actual + cantidad_actual
                # después de nuevo movimiento = (stock_actual + cantidad_actual) - nueva_cantidad
                nuevo_stock = stock_actual + cantidad_actual - nueva_cantidad
                if nuevo_stock < 0:
                    raise ValueError("Stock insuficiente para realizar la venta con la nueva cantidad")
            else:  # entrada
                nuevo_stock = stock_actual - cantidad_actual + nueva_cantidad

            # Actualizar movimiento
            cursor.execute(
                "UPDATE movimientos SET cantidad = ?, fecha = ? WHERE id = ?",
                (nueva_cantidad, nueva_fecha, movimiento_id)
            )
            # Actualizar stock del producto
            cursor.execute(
                "UPDATE productos SET cantidad = ? WHERE id = ?",
                (nuevo_stock, producto_id)
            )
            conn.commit()
            return True

    def eliminar_movimiento(self, movimiento_id):
        """Elimina un movimiento y revierte su efecto en el stock."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Obtener movimiento
            cursor.execute("SELECT producto_id, tipo, cantidad FROM movimientos WHERE id = ?", (movimiento_id,))
            mov = cursor.fetchone()
            if not mov:
                return False
            producto_id, tipo, cantidad = mov

            # Obtener stock actual
            cursor.execute("SELECT cantidad FROM productos WHERE id = ?", (producto_id,))
            stock_actual = cursor.fetchone()[0]

            # Revertir efecto en stock
            if tipo == 'venta':
                nuevo_stock = stock_actual + cantidad
            else:  # entrada
                nuevo_stock = stock_actual - cantidad
                if nuevo_stock < 0:
                    raise ValueError("No se puede eliminar la entrada porque dejaría stock negativo")

            # Eliminar movimiento
            cursor.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
            # Actualizar stock
            cursor.execute("UPDATE productos SET cantidad = ? WHERE id = ?", (nuevo_stock, producto_id))
            conn.commit()
            return True

    # ---------- Historial ----------
    def obtener_meses_con_movimientos(self, tipo):
        """Devuelve lista de strings 'YYYY-MM' para los meses que tienen movimientos del tipo especificado."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT strftime('%Y-%m', fecha) as mes
                FROM movimientos
                WHERE tipo = ?
                ORDER BY mes DESC
            """, (tipo,))
            return [row[0] for row in cursor.fetchall()]

    def obtener_movimientos_por_mes(self, tipo, mes):
        """
        tipo: 'entrada' o 'venta'
        mes: string 'YYYY-MM'
        Devuelve lista de diccionarios con id, producto, fecha, cantidad.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.id, p.nombre, m.fecha, m.cantidad
                FROM movimientos m
                JOIN productos p ON m.producto_id = p.id
                WHERE m.tipo = ? AND strftime('%Y-%m', m.fecha) = ?
                ORDER BY m.fecha DESC
            """, (tipo, mes))
            rows = cursor.fetchall()
            return [{"id": r[0], "producto": r[1], "fecha": r[2], "cantidad": r[3]} for r in rows]

    # ---------- Resumen para dashboard ----------
    def obtener_resumen(self):
        """Devuelve (total_productos, stock_total, valor_total)"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM productos")
            total_productos = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(cantidad) FROM productos")
            stock_total = cursor.fetchone()[0] or 0
            cursor.execute("SELECT SUM(precio * cantidad) FROM productos")
            valor_total = cursor.fetchone()[0] or 0.0
            return total_productos, stock_total, valor_total