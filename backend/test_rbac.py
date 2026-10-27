import urllib.request
import json

def test_login(kadi, sifre):
    data = json.dumps({"kadi": kadi, "sifre": sifre}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8000/api/login", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"Login Başarılı: {kadi} -> Rol: {res['user']['role']} ({res['user']['role_title']})")
        return res["access_token"]

# 1. Test Admin Login
admin_token = test_login("ahmet.yilmaz", "Ynt123.")

# 2. Test Asci Login
asci_token = test_login("kerem.usta", "Mutfak101!")

# 3. Test Depo Login
depo_token = test_login("mehmet.oz", "Depo123.")

# 4. Test Porsiyon Simülatörü (Aşçı)
req = urllib.request.Request("http://127.0.0.1:8000/api/asci/recete-olcekle/10?carpan=3", headers={"Authorization": f"Bearer {asci_token}"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Aşçı Porsiyon Simülasyonu (3x):", data["tarif"]["yemekadı"], "| Malzeme Sayısı:", len(data["malzemeler"]))

# 5. Test Depo Stok Listesi (Depocu)
req = urllib.request.Request("http://127.0.0.1:8000/api/depo/stoklar", headers={"Authorization": f"Bearer {depo_token}"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Depo Sorumlusu Stok Kalemleri Sayısı:", len(data))

# 6. Test RBAC Kısıtlaması (Aşçı depo stoklarına erişemez!)
try:
    req_forbidden = urllib.request.Request("http://127.0.0.1:8000/api/depo/stoklar", headers={"Authorization": f"Bearer {asci_token}"})
    urllib.request.urlopen(req_forbidden)
    print("HATA: Aşçı yetkisiz alana erişti!")
except urllib.error.HTTPError as e:
    print(f"RBAC Koruması Başarılı: Aşçı stokları okuyamadı (HTTP {e.code} - {e.reason})")
