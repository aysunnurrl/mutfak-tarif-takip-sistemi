-- Mutfak Tarif Takip ve Yönetim Sistemi
-- Zengin Örnek Reçete ve Malzeme Eşleştirme Seed Scripti

USE `tarif_takip_sistemi`;

-- 1. Eksik olabilecek temel mutfak malzemeleri (Varsa atlar)
INSERT IGNORE INTO `malzeme` (`malzemeid`, `mAdı`, `skt`, `tedariktarihi`, `MinStokSeviyesi`) VALUES
(9, 'Kuru Soğan', '2026-12-31', NOW(), '20'),
(10, 'Sarımsak', '2026-12-31', NOW(), '10'),
(11, 'Karabiber / Tuz', '2027-01-01', NOW(), '5'),
(12, 'Kuzu Eti', '2026-11-15', NOW(), '15'),
(13, 'Makarna', '2027-06-01', NOW(), '30'),
(14, 'Pastırma', '2026-12-01', NOW(), '10'),
(15, 'Kaşar Peyniri', '2026-11-30', NOW(), '15');

-- 2. Tariflerin malzemelerini eksiksiz zenginleştir
INSERT IGNORE INTO `tarifmalzemeleri` (`tarifno`, `malzemeid`) VALUES
-- Izgara Köfte (10): Kıyma (1), Zeytinyağı (6), Kuru Soğan (9), Baharat (11)
(10, 1),
(10, 9),
(10, 11),

-- Fırın Sütlaç (20): Süt (2), Pirinç (3), Un/Nişasta (7), Şeker (8)
(20, 3),

-- Süzme Mercimek Çorbası (30): Mercimek (4), Kuru Soğan (9), Zeytinyağı (6), Baharat (11)
(30, 6),
(30, 9),
(30, 11),

-- Çoban Salata (40): Domates (5), Zeytinyağı (6), Kuru Soğan (9)
(40, 6),
(40, 9),

-- Linguine Frutti (50): Makarna (13), Zeytinyağı (6), Sarımsak (10), Domates (5)
(50, 10),
(50, 13),

-- Tandır (60): Kuzu Eti (12), Zeytinyağı (6), Sarımsak (10), Baharat (11)
(60, 10),
(60, 11),
(60, 12),

-- Sufle (70): Süt (2), Un (7), Şeker (8)
(70, 7),
(70, 8),

-- Paçanga Böreği (80): Pastırma (14), Kaşar (15), Domates (5), Un (7)
(80, 5),
(80, 14),
(80, 15);

-- 3. Yemek eşleşmelerini tam kontrol et
UPDATE `yemek` SET `tarifno` = 30 WHERE `yemekid` = 3 AND (`tarifno` IS NULL OR `tarifno` = 0);
UPDATE `yemek` SET `yemekadı` = 'Geleneksel Paçanga Böreği' WHERE `yemekid` = 8;
