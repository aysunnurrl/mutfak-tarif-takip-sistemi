from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from database import get_db_connection
from auth import create_access_token, get_current_user, require_role

app = FastAPI(
    title="Mutfak Yönetimi ve Tarif Takip Sistemi API",
    description="Rol Tabanlı Yetkilendirme (RBAC) ile Yönetici, Aşçı ve Depo Sorumlusu API Servisi",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class LoginRequest(BaseModel):
    kadi: str
    sifre: str

class UserCreateRequest(BaseModel):
    kadi: str
    ad: str
    soyad: str
    sifre: str
    email: Optional[str] = None
    telefon: Optional[str] = None
    departmanid: Optional[int] = None
    role: str # 'yonetici', 'asci', 'depo'
    butceYetkisiLimiti: Optional[int] = 50000 # Yönetici için
    depoid: Optional[int] = 1 # Depocu için
    lisanstipi: Optional[str] = "Standart" # Depocu için

class StockMovementRequest(BaseModel):
    malzemeid: int
    miktar: int
    islemTipi: str # 'Giriş', 'Çıkış', 'Fire'
    aciklama: Optional[str] = ""

class PurchaseRequestCreate(BaseModel):
    malzemeid: int
    miktar: str

class PurchaseRequestStatus(BaseModel):
    durum: str # 'Onaylandı', 'Reddedildi'

class TempLogRequest(BaseModel):
    ekipmanid: int
    olculensicaklik: str


# --- AUTH ENDPOINTS ---

@app.post("/api/login")
def login(creds: LoginRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Kullanıcıyı ara
            cursor.execute(
                "SELECT kullaniciid, kadi, ad, soyad, sifre, email, telefon FROM kullanici WHERE kadi = %s",
                (creds.kadi.strip(),)
            )
            user = cursor.fetchone()
            if not user or user["sifre"] != creds.sifre.strip():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Kullanıcı adı veya şifre hatalı!"
                )
            
            uid = user["kullaniciid"]
            
            # Rol tespiti (yonetici, asci, depopersoneli)
            role = None
            role_title = ""
            details = {}
            
            cursor.execute("SELECT * FROM yonetici WHERE kullaniciid = %s", (uid,))
            yonetici_data = cursor.fetchone()
            if yonetici_data:
                role = "yonetici"
                role_title = "Yönetici"
                details = yonetici_data
            else:
                cursor.execute("SELECT * FROM asci WHERE kullaniciid = %s", (uid,))
                asci_data = cursor.fetchone()
                if asci_data:
                    role = "asci"
                    role_title = "Aşçı / Şef"
                    # Uzmanlık ve pozisyon bilgilerini de çek
                    cursor.execute("""
                        SELECT u.uzmanlikadi FROM asciuzmanliklari au
                        JOIN uzmanlikalani u ON au.uzmanlikid = u.uzmanlikid
                        WHERE au.kullaniciid = %s
                    """, (uid,))
                    uzmanliklar = [r["uzmanlikadi"] for r in cursor.fetchall()]
                    details["uzmanliklar"] = uzmanliklar
                else:
                    cursor.execute("SELECT * FROM depopersoneli WHERE kullaniciid = %s", (uid,))
                    depo_data = cursor.fetchone()
                    if depo_data:
                        role = "depo"
                        role_title = "Depo Sorumlusu"
                        details = depo_data
                    else:
                        role = "kullanici"
                        role_title = "Genel Personel"

            token_data = {
                "sub": str(user["kullaniciid"]),
                "kadi": user["kadi"],
                "ad": user["ad"],
                "soyad": user["soyad"],
                "role": role,
                "role_title": role_title
            }
            token = create_access_token(token_data)

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["kullaniciid"],
                    "kadi": user["kadi"],
                    "ad": user["ad"],
                    "soyad": user["soyad"],
                    "email": user["email"],
                    "role": role,
                    "role_title": role_title,
                    "details": details
                }
            }
    finally:
        conn.close()


@app.get("/api/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return current_user


# --- COMMON / RECIPES ENDPOINTS ---

@app.get("/api/tarifler")
def list_recipes(current_user: dict = Depends(get_current_user)):
    """
    Her 3 rol de tarifleri listeleyebilir.
    Yönetici maliyetleri de görebilir.
    Aşçı tarif malzemelerini ve porsiyon detaylarını görür.
    Depocu tarif maliyetlerini göremez.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Tarifler ve bağlı yemek bilgisi
            cursor.execute("""
                SELECT 
                    t.tarifno,
                    t.hazırlamasuresi,
                    t.porsiyonbilgisi,
                    t.aciklama,
                    y.yemekid,
                    y.yemekadı,
                    k.`kategoriadı` AS kategoriadi
                FROM tarif t
                LEFT JOIN yemek y ON t.tarifno = y.tarifno
                LEFT JOIN kategori k ON y.kategoriid = k.kategoriid
                ORDER BY t.tarifno ASC
            """)
            tarifler = cursor.fetchall()
            
            # Her tarifin malzemelerini çek
            for trf in tarifler:
                tno = trf["tarifno"]
                cursor.execute("""
                    SELECT 
                        m.malzemeid,
                        m.`mAdı` AS malzeme_adi,
                        tm.birim,
                        tm.fiyat AS birim_fiyat
                    FROM tarifmalzemeleri trm
                    JOIN malzeme m ON trm.malzemeid = m.malzemeid
                    LEFT JOIN tedarikcimalzeme tm ON m.malzemeid = tm.malzemeid
                    WHERE trm.tarifno = %s
                """, (tno,))
                raw_materials = cursor.fetchall()
                
                # Malzemeleri tekilleştir ve rol bazlı filtrele
                materials = []
                total_cost = 0.0
                seen = set()
                for rm in raw_materials:
                    mid = rm["malzemeid"]
                    if mid not in seen:
                        seen.add(mid)
                        fiyat_num = 0.0
                        if rm["birim_fiyat"]:
                            try:
                                fiyat_num = float(str(rm["birim_fiyat"]).replace(",", ".").replace("₺", "").strip())
                            except ValueError:
                                fiyat_num = 0.0
                        total_cost += fiyat_num
                        
                        mat_item = {
                            "malzemeid": rm["malzemeid"],
                            "malzeme_adi": rm["malzeme_adi"],
                            "birim": rm["birim"] or "Adet"
                        }
                        # KISITLAMA: Depo Sorumlusu maliyetleri göremez!
                        if current_user.get("role") in ["yonetici"]:
                            mat_item["birim_fiyat"] = fiyat_num
                        
                        materials.append(mat_item)
                
                trf["malzemeler"] = materials
                if current_user.get("role") == "yonetici":
                    trf["tahmini_maliyet"] = round(total_cost, 2)
            
            return tarifler
    finally:
        conn.close()


# --- AŞÇI ÖZEL: Porsiyon Simülatörü ve Reçete Ölçekleme ---

@app.get("/api/asci/recete-olcekle/{tarifno}")
def scale_recipe(tarifno: int, carpan: float = 1.0, current_user: dict = Depends(require_role(["asci", "yonetici"]))):
    """
    Aşçı porsiyon simülatörüyle reçete malzemelerini oranlar.
    Aşçı stok seviyelerini doğrudan görmez, ancak yetersizlik uyarısı varsa sistem hesaplar.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT t.tarifno, t.hazırlamasuresi, t.porsiyonbilgisi, y.yemekadı 
                FROM tarif t
                LEFT JOIN yemek y ON t.tarifno = y.tarifno
                WHERE t.tarifno = %s
            """, (tarifno,))
            tarif = cursor.fetchone()
            if not tarif:
                raise HTTPException(status_code=404, detail="Tarif bulunamadı")

            cursor.execute("""
                SELECT 
                    m.malzemeid,
                    m.`mAdı` as malzeme_adi,
                    COALESCE(SUM(CASE WHEN sh.islemTipi = 'Giriş' THEN sh.miktar 
                                      WHEN sh.islemTipi IN ('Çıkış', 'Fire') THEN -sh.miktar 
                                      ELSE 0 END), 0) as mevcut_stok,
                    CAST(m.MinStokSeviyesi AS SIGNED) as min_stok
                FROM tarifmalzemeleri tm
                JOIN malzeme m ON tm.malzemeid = m.malzemeid
                LEFT JOIN stokhareketi sh ON m.malzemeid = sh.malzemeid
                WHERE tm.tarifno = %s
                GROUP BY m.malzemeid
            """, (tarifno,))
            items = cursor.fetchall()

            # Aşçı için oranlanmış malzeme listesi ve stok durum uyarısı
            scaled_materials = []
            for item in items:
                base_qty = 100 # Varsayılan baz gram/adet
                scaled_qty = round(base_qty * carpan, 1)
                
                # Aşçı stok sayısını görmez, sadece 'Yeterli' / 'Kritik Uyarı' durumunu görür
                stok_durumu = "Yeterli"
                if item["mevcut_stok"] <= item["min_stok"]:
                    stok_durumu = "⚠️ Kritik Seviye (Depoya Bildirildi)"
                elif item["mevcut_stok"] < (scaled_qty / 10):
                    stok_durumu = "⚠️ Stok Yetersiz Olabilir"

                mat_info = {
                    "malzemeid": item["malzemeid"],
                    "malzeme_adi": item["malzeme_adi"],
                    "hesaplanan_miktar": f"{scaled_qty} gr/birim",
                    "stok_uyarisi": stok_durumu
                }
                scaled_materials.append(mat_info)

            return {
                "tarif": tarif,
                "carpan": carpan,
                "hesaplanan_porsiyon": f"{carpan}x Katı",
                "malzemeler": scaled_materials
            }
    finally:
        conn.close()


@app.post("/api/asci/sicaklik-kaydi")
def add_temperature_log(data: TempLogRequest, current_user: dict = Depends(require_role(["asci", "yonetici"]))):
    """
    Aşçı ekipmanlar için sıcaklık kontrol kaydı girebilir.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Yeni kayitid üret
            cursor.execute("SELECT COALESCE(MAX(kayitid), 0) + 1 AS next_id FROM sicaklikkontrolkaydi")
            next_id = cursor.fetchone()["next_id"]
            
            cursor.execute("""
                INSERT INTO sicaklikkontrolkaydi (kayitid, tarihSaat, olculensicaklik, ekipmanid, kullaniciid)
                VALUES (%s, NOW(), %s, %s, %s)
            """, (next_id, data.olculensicaklik, data.ekipmanid, current_user["sub"]))
            
            return {"status": "success", "message": f"Sıcaklık kaydı ({data.olculensicaklik}°C) başarıyla eklendi.", "kayitid": next_id}
    finally:
        conn.close()


@app.get("/api/asci/ekipmanlar")
def list_equipments(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.ekipmanid, e.ekipmanadı, m.markaadı, e.periyodikbakimgunu
                FROM ekipman e
                LEFT JOIN marka m ON e.markaid = m.markaid
                ORDER BY e.ekipmanid ASC
            """)
            return cursor.fetchall()
    finally:
        conn.close()


# --- DEPO SORUMLUSU ÖZEL: Stok Hareketleri ve Satınalma Talepleri ---

@app.get("/api/depo/stoklar")
def list_stock(current_user: dict = Depends(require_role(["depo", "yonetici"]))):
    """
    Depo Sorumlusu ve Yönetici güncel malzeme stoklarını görebilir.
    Aşçılar buraya erişemez (RBAC Kısıtlaması)!
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.malzemeid,
                    m.`mAdı` AS malzeme_adi,
                    m.skt,
                    m.MinStokSeviyesi,
                    COALESCE(SUM(CASE WHEN sh.islemTipi = 'Giriş' THEN sh.miktar 
                                      WHEN sh.islemTipi IN ('Çıkış', 'Fire') THEN -sh.miktar 
                                      ELSE 0 END), 0) AS guncel_stok
                FROM malzeme m
                LEFT JOIN stokhareketi sh ON m.malzemeid = sh.malzemeid
                GROUP BY m.malzemeid
                ORDER BY m.malzemeid ASC
            """)
            return cursor.fetchall()
    finally:
        conn.close()


@app.get("/api/depo/stok-hareketleri")
def list_stock_movements(current_user: dict = Depends(require_role(["depo", "yonetici"]))):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    sh.hareketid,
                    sh.miktar,
                    sh.tarihSaat,
                    sh.islemTipi,
                    sh.aciklama,
                    m.`mAdı` AS malzeme_adi,
                    k.ad AS personel_adi,
                    k.soyad AS personel_soyadi
                FROM stokhareketi sh
                JOIN malzeme m ON sh.malzemeid = m.malzemeid
                LEFT JOIN kullanici k ON sh.kullaniciid = k.kullaniciid
                ORDER BY sh.tarihSaat DESC, sh.hareketid DESC
                LIMIT 50
            """)
            return cursor.fetchall()
    finally:
        conn.close()


@app.post("/api/depo/stok-hareketi-ekle")
def add_stock_movement(data: StockMovementRequest, current_user: dict = Depends(require_role(["depo"]))):
    """
    Depo Sorumlusu stok hareketi (Giriş / Çıkış / Fire) ekler.
    Onaylanmış geçmiş hareketleri DEĞİŞTİREMEZ (Kısıtlama). Sadece yeni hareket append edilebilir!
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(hareketid), 0) + 1 AS next_id FROM stokhareketi")
            next_id = cursor.fetchone()["next_id"]

            cursor.execute("""
                INSERT INTO stokhareketi (hareketid, miktar, tarihSaat, islemTipi, aciklama, malzemeid, kullaniciid)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s)
            """, (next_id, data.miktar, data.islemTipi, data.aciklama, data.malzemeid, current_user["sub"]))

            # Eğer işlem 'Fire' ise fire tablosuna da kaydet
            if data.islemTipi == 'Fire':
                cursor.execute("SELECT COALESCE(MAX(fireid), 0) + 1 AS next_fire_id FROM fire")
                next_fire_id = cursor.fetchone()["next_fire_id"]
                cursor.execute("""
                    INSERT INTO fire (fireid, miktar, acıklama, tarih, kullaniciid)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (next_fire_id, str(data.miktar), data.aciklama or "Depo Fire Kaydı", current_user["sub"]))
                cursor.execute("""
                    INSERT INTO firekaydi (malzemeid, fireid) VALUES (%s, %s)
                """, (data.malzemeid, next_fire_id))

            return {"status": "success", "message": "Stok hareketi başarıyla kaydedildi.", "hareketid": next_id}
    finally:
        conn.close()


@app.post("/api/depo/satinalma-talebi")
def create_purchase_request(data: PurchaseRequestCreate, current_user: dict = Depends(require_role(["depo"]))):
    """
    Depo sorumlusu kritik stoklar için satınalma talebi açar.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(talepid), 0) + 1 AS next_id FROM satinalmatalebi")
            next_id = cursor.fetchone()["next_id"]

            cursor.execute("""
                INSERT INTO satinalmatalebi (talepid, kullaniciid, talepTarihi, durum)
                VALUES (%s, %s, NOW(), 'Beklemede')
            """, (next_id, current_user["sub"]))

            cursor.execute("""
                INSERT INTO satinalmatalepdetay (talepid, malzemeid, miktar)
                VALUES (%s, %s, %s)
            """, (next_id, data.malzemeid, data.miktar))

            return {"status": "success", "message": "Satınalma talebi oluşturuldu, yönetici onayına sunuldu.", "talepid": next_id}
    finally:
        conn.close()


@app.get("/api/satinalma-talepleri")
def list_purchase_requests(current_user: dict = Depends(require_role(["depo", "yonetici"]))):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    st.talepid,
                    st.talepTarihi,
                    st.durum,
                    st.onayTarihi,
                    k.ad AS talep_eden_ad,
                    k.soyad AS talep_eden_soyad,
                    m.`mAdı` AS malzeme_adi,
                    std.miktar
                FROM satinalmatalebi st
                LEFT JOIN kullanici k ON st.kullaniciid = k.kullaniciid
                LEFT JOIN satinalmatalepdetay std ON st.talepid = std.talepid
                LEFT JOIN malzeme m ON std.malzemeid = m.malzemeid
                ORDER BY st.talepTarihi DESC
            """)
            return cursor.fetchall()
    finally:
        conn.close()


# --- YÖNETİCİ ÖZEL: Onaylar, Kullanıcı Yönetimi, Maliyet & Raporlar ---

@app.put("/api/yonetici/satinalma-onayla/{talepid}")
def approve_purchase_request(talepid: int, data: PurchaseRequestStatus, current_user: dict = Depends(require_role(["yonetici"]))):
    """
    SADECE YÖNETİCİ satınalma talebini onaylayabilir veya reddedebilir.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE satinalmatalebi 
                SET durum = %s, onayTarihi = NOW() 
                WHERE talepid = %s
            """, (data.durum, talepid))
            return {"status": "success", "message": f"Talep durumu '{data.durum}' olarak güncellendi."}
    finally:
        conn.close()


@app.get("/api/yonetici/kullanicilar")
def list_users(current_user: dict = Depends(require_role(["yonetici"]))):
    """
    SADECE YÖNETİCİ kullanıcı listesini görüntüler, ekler veya siler.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    k.kullaniciid,
                    k.kadi,
                    k.ad,
                    k.soyad,
                    k.email,
                    k.telefon,
                    k.isebaslamatarihi,
                    d.departmanadı,
                    CASE 
                        WHEN y.kullaniciid IS NOT NULL THEN 'Yönetici'
                        WHEN a.kullaniciid IS NOT NULL THEN 'Aşçı'
                        WHEN dp.kullaniciid IS NOT NULL THEN 'Depo Sorumlusu'
                        ELSE 'Genel'
                    END AS rol_adi
                FROM kullanici k
                LEFT JOIN departman d ON k.departmanid = d.deparrtmanid
                LEFT JOIN yonetici y ON k.kullaniciid = y.kullaniciid
                LEFT JOIN asci a ON k.kullaniciid = a.kullaniciid
                LEFT JOIN depopersoneli dp ON k.kullaniciid = dp.kullaniciid
                ORDER BY k.kullaniciid DESC
            """)
            return cursor.fetchall()
    finally:
        conn.close()


@app.post("/api/yonetici/kullanici-ekle")
def create_user(data: UserCreateRequest, current_user: dict = Depends(require_role(["yonetici"]))):
    """
    SADECE YÖNETİCİ sisteme yeni kullanıcı ekler ve rolünü belirler.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Yeni kullaniciid üret
            cursor.execute("SELECT COALESCE(MAX(kullaniciid), 0) + 1 AS next_id FROM kullanici")
            next_id = cursor.fetchone()["next_id"]

            cursor.execute("""
                INSERT INTO kullanici (kullaniciid, kadi, ad, soyad, sifre, email, telefon, isebaslamatarihi, departmanid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (next_id, data.kadi.strip(), data.ad.strip(), data.soyad.strip(), data.sifre.strip(), data.email, data.telefon, data.departmanid))

            # Role tablosuna ekle
            if data.role == "yonetici":
                cursor.execute("INSERT INTO yonetici (kullaniciid, butceYetkisiLimiti, departmanid) VALUES (%s, %s, %s)",
                               (next_id, data.butceYetkisiLimiti, data.departmanid))
            elif data.role == "asci":
                cursor.execute("INSERT INTO asci (kullaniciid) VALUES (%s)", (next_id,))
            elif data.role == "depo":
                cursor.execute("INSERT INTO depopersoneli (kullaniciid, depoid, lisanstipi) VALUES (%s, %s, %s)",
                               (next_id, data.depoid or 1, data.lisanstipi or "Standart"))

            return {"status": "success", "message": f"Kullanıcı başarıyla oluşturuldu.", "kullaniciid": next_id}
    finally:
        conn.close()


@app.delete("/api/yonetici/kullanici-sil/{kullaniciid}")
def delete_user(kullaniciid: int, current_user: dict = Depends(require_role(["yonetici"]))):
    """
    SADECE YÖNETİCİ kullanıcı silebilir.
    """
    if str(kullaniciid) == str(current_user["sub"]):
        raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz!")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM yonetici WHERE kullaniciid = %s", (kullaniciid,))
            cursor.execute("DELETE FROM asci WHERE kullaniciid = %s", (kullaniciid,))
            cursor.execute("DELETE FROM depopersoneli WHERE kullaniciid = %s", (kullaniciid,))
            cursor.execute("DELETE FROM kullanici WHERE kullaniciid = %s", (kullaniciid,))
            return {"status": "success", "message": "Kullanıcı başarıyla silindi."}
    finally:
        conn.close()


@app.get("/api/yonetici/raporlar")
def get_reports(current_user: dict = Depends(require_role(["yonetici"]))):
    """
    Yöneticiye özel özet istatistikler ve SQL sorgu raporları.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Toplam kullanıcı sayısı
            cursor.execute("SELECT COUNT(*) AS total_users FROM kullanici")
            total_users = cursor.fetchone()["total_users"]

            # Toplam tarif
            cursor.execute("SELECT COUNT(*) AS total_recipes FROM tarif")
            total_recipes = cursor.fetchone()["total_recipes"]

            # Bekleyen satınalma talepleri
            cursor.execute("SELECT COUNT(*) AS pending_orders FROM satinalmatalebi WHERE durum = 'Beklemede'")
            pending_orders = cursor.fetchone()["pending_orders"]

            # Toplam fire kaydı
            cursor.execute("SELECT COUNT(*) AS total_waste FROM fire")
            total_waste = cursor.fetchone()["total_waste"]

            # Kritik sıcaklık kayıtları (> 3°C olanlar)
            cursor.execute("""
                SELECT 
                    e.ekipmanadı AS ekipman,
                    s.olculensicaklik AS sicaklik,
                    s.tarihSaat,
                    k.ad AS olcen
                FROM sicaklikkontrolkaydi s
                JOIN ekipman e ON s.ekipmanid = e.ekipmanid
                JOIN kullanici k ON s.kullaniciid = k.kullaniciid
                WHERE CAST(s.olculensicaklik AS SIGNED) > 3
                ORDER BY s.tarihSaat DESC
                LIMIT 5
            """)
            kritik_sicakliklar = cursor.fetchall()

            return {
                "total_users": total_users,
                "total_recipes": total_recipes,
                "pending_orders": pending_orders,
                "total_waste": total_waste,
                "kritik_sicakliklar": kritik_sicakliklar
            }
    finally:
        conn.close()


# Static ve Frontend Dosyaları Servisi
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

