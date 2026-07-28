# ============================================
# database.py
# ============================================
import sqlite3

class Database:
    """Maneja la conexión y creación de la base de datos."""
    def __init__(self, db_path="inventario.db"):
        self.db_path = db_path
        self._create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Crea las tablas si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    precio REAL NOT NULL,
                    cantidad INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,  -- 'entrada' o 'venta'
                    fecha TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    FOREIGN KEY (producto_id) REFERENCES productos (id) ON DELETE CASCADE
                )
            """)
            conn.commit()