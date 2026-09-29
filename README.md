# Emir - DiziKorea Otomatik Akış Havuzu

Bu depo, **dizikorea3.com** üzerindeki güncel Kore & Asya dizilerini ve filmlerini otomatik olarak tarar, video kaynaklarını (VidMoly vb.) çözer ve oynatıcıların anlayacağı standart formatlarda yayınlar.

## 📡 Doğrudan Yayın Bağlantıları (Raw Links)

Aşağıdaki linkleri hem **Media Studio (Masaüstü)** uygulamanızda hem de **Android (TiviMate / IPTV / Cloudstream uyumlu oynatıcılar)** üzerinde doğrudan kullanabilirsiniz:

* **M3U Oynatma Listesi:**
  ```text
  https://raw.githubusercontent.com/kodlama155-ctrl/emir/main/dizikorea.m3u
  ```

* **JSON Katalog (Film & Dizi Meta Verileri + Stream Kaynakları):**
  ```text
  https://raw.githubusercontent.com/kodlama155-ctrl/emir/main/dizikorea_catalog.json
  ```

## ⚙️ Nasıl Çalışır?
1. **GitHub Actions (`.github/workflows/update.yml`):**
   * Her 6 saatte bir otomatik olarak tetiklenir (veya GitHub "Actions" sekmesinden tek tıkla elle başlatılabilir).
2. **Scraper (`scraper.py`):**
   * `dizikorea3.com` sitesindeki en yeni film ve dizileri çeker.
   * VidMoly embed oynatıcılarından doğrudan canlı `.m3u8` master akış linklerini ayıklar.
3. **Commit & Push:**
   * Güncel linkleri `dizikorea.m3u` ve `dizikorea_catalog.json` dosyalarına yazar ve depoya kaydeder.
