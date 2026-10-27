import pymysql
import re

print("Yerel XAMPP ve Bulut TiDB'ye bağlanılıyor...")
local_conn = pymysql.connect(
    host="localhost",
    port=3307,
    user="root",
    password="",
    database="tarif_takip_sistemi",
    charset="utf8mb4"
)

tidb_conn = pymysql.connect(
    host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com",
    port=4000,
    user="3rqakn14zS2CB88.root",
    password="4ix4PFCwHZOrEXji",
    database="tarif_takip_sistemi",
    charset="utf8mb4",
    autocommit=True,
    ssl={"ssl_verify_cert": False}
)

with local_conn.cursor() as loc_cur, tidb_conn.cursor() as tidb_cur:
    tidb_cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    # 1. Tüm tabloların CREATE TABLE komutlarını al ve TiDB'de oluştur
    loc_cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
    tables = [row[0] for row in loc_cur.fetchall()]
    print(f"Toplam {len(tables)} tablo aktarılacak:", tables)

    for tbl in tables:
        loc_cur.execute(f"SHOW CREATE TABLE `{tbl}`;")
        create_sql = loc_cur.fetchone()[1]
        
        # TiDB için standart utf8mb4 uyarlaması
        create_sql = re.sub(r"COLLATE=[a-zA-Z0-9_]+", "COLLATE=utf8mb4_bin", create_sql)
        create_sql = re.sub(r"COLLATE [a-zA-Z0-9_]+", "COLLATE utf8mb4_bin", create_sql)
        create_sql = re.sub(r"DEFAULT CHARSET=[a-zA-Z0-9_]+", "DEFAULT CHARSET=utf8mb4", create_sql)
        create_sql = re.sub(r"CHARACTER SET [a-zA-Z0-9_]+", "CHARACTER SET utf8mb4", create_sql)
        
        tidb_cur.execute(f"DROP TABLE IF EXISTS `{tbl}`;")
        tidb_cur.execute(create_sql)
        print(f"-> Tablo oluşturuldu: {tbl}")

    # 2. Tablo verilerini kopyala
    for tbl in tables:
        loc_cur.execute(f"SELECT * FROM `{tbl}`;")
        rows = loc_cur.fetchall()
        if not rows:
            continue
        
        # Column names
        col_names = [desc[0] for desc in loc_cur.description]
        col_placeholders = ", ".join([f"`{c}`" for c in col_names])
        val_placeholders = ", ".join(["%s"] * len(col_names))
        insert_sql = f"INSERT INTO `{tbl}` ({col_placeholders}) VALUES ({val_placeholders})"
        
        cleaned_rows = []
        for r in rows:
            cleaned_r = list(r)
            for idx, val in enumerate(cleaned_r):
                if str(val) in ["0000-00-00", "0000-00-00 00:00:00"]:
                    cleaned_r[idx] = None
            cleaned_rows.append(tuple(cleaned_r))

        tidb_cur.executemany(insert_sql, cleaned_rows)
        print(f"-> {len(rows)} satır veri aktarıldı: {tbl}")

    tidb_cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    print("TÜM VERİLER BAŞARIYLA AKTARILDI!")

local_conn.close()
tidb_conn.close()
