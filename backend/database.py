import os
import pymysql
from pymysql.cursors import DictCursor

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3307"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "tarif_takip_sistemi")

def get_db_connection():
    connect_kwargs = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": True
    }
    # TiDB Cloud ve bulut bağlantıları güvenli SSL gerektirir
    if DB_HOST not in ["localhost", "127.0.0.1"]:
        connect_kwargs["ssl_verify_cert"] = False
        connect_kwargs["ssl"] = {"ssl_verify_cert": False}

    return pymysql.connect(**connect_kwargs)

