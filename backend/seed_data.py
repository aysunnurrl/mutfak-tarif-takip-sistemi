import pymysql

conn = pymysql.connect(
    host="localhost",
    port=3307,
    user="root",
    password="",
    database="tarif_takip_sistemi",
    charset="utf8mb4",
    autocommit=True
)

with conn.cursor() as cur:
    # 1. Yeni malzemeler
    malzemeler = [
        (9, "Kuru Soğan", "2026-12-31", "20"),
        (10, "Sarımsak", "2026-12-31", "10"),
        (11, "Karabiber / Tuz", "2027-01-01", "5"),
        (12, "Kuzu Eti", "2026-11-15", "15"),
        (13, "Makarna", "2027-06-01", "30"),
        (14, "Pastırma", "2026-12-01", "10"),
        (15, "Kaşar Peyniri", "2026-11-30", "15")
    ]
    for mid, ad, skt, min_stok in malzemeler:
        cur.execute("""
            INSERT INTO `malzeme` (`malzemeid`, `mAdı`, `skt`, `tedariktarihi`, `MinStokSeviyesi`)
            VALUES (%s, %s, %s, NOW(), %s)
            ON DUPLICATE KEY UPDATE `mAdı` = VALUES(`mAdı`)
        """, (mid, ad, skt, min_stok))

    # 2. Malzeme - Tarif ilişkileri
    tarif_malzemeleri = [
        (10, 1), (10, 9), (10, 11), # Köfte: Kıyma, Soğan, Tuz/Baharat
        (20, 3), # Sütlaç: Pirinç
        (30, 4), (30, 6), (30, 9), (30, 11), # Mercimek: Mercimek, Zeytinyağ, Soğan, Baharat
        (40, 5), (40, 6), (40, 9), # Salata: Domates, Zeytinyağ, Soğan
        (50, 10), (50, 13), # Makarna: Sarımsak, Makarna
        (60, 10), (60, 11), (60, 12), # Tandır: Sarımsak, Baharat, Kuzu Eti
        (70, 7), (70, 8), # Sufle: Un, Şeker
        (80, 5), (80, 14), (80, 15) # Börek: Domates, Pastırma, Kaşar
    ]
    for tno, mid in tarif_malzemeleri:
        cur.execute("""
            INSERT IGNORE INTO `tarifmalzemeleri` (`tarifno`, `malzemeid`)
            VALUES (%s, %s)
        """, (tno, mid))

    # 3. Yemek eksikliklerini bağla
    cur.execute("UPDATE `yemek` SET `tarifno` = 30 WHERE `yemekid` = 3")
    cur.execute("UPDATE `yemek` SET `yemekadı` = 'Geleneksel Paçanga Böreği' WHERE `yemekid` = 8")

print("Seed verileri başarıyla veritabanına işlendi!")
conn.close()
