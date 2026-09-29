#!/usr/bin/env python3
"""
DiziKorea Full Archive Pagination Harvester
Sayfalama mantığını (sayfa 1, 2, 3...) tarayarak tüm arşivi çeker.
"""

import json
import re
import urllib.request
import time
from typing import Dict, List, Optional

BASE_URL = "https://dizikorea3.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Ana Kategori Rotaları ve Sayfalama Yapısı
CATEGORIES = [
    {"name": "Filmler", "base_path": "/filmler", "type": "movie", "max_pages": 50},
    {"name": "Kore Dizileri", "base_path": "/kore-dizileri-izle-dq", "type": "series", "max_pages": 50},
    {"name": "Cin Dizileri", "base_path": "/cin-dizileri", "type": "series", "max_pages": 30},
    {"name": "Japon Dizileri", "base_path": "/japon-dizileri", "type": "series", "max_pages": 30},
    {"name": "Tayland Dizileri", "base_path": "/tayland-dizileri", "type": "series", "max_pages": 30},
    {"name": "Tayvan Dizileri", "base_path": "/tayvan-dizileri", "type": "series", "max_pages": 15},
    {"name": "Filipin Dizileri", "base_path": "/filipin-dizileri", "type": "series", "max_pages": 10},
    {"name": "Efsane Diziler", "base_path": "/efsane-diziler", "type": "series", "max_pages": 5},
]

def fetch_html(url: str, referer: Optional[str] = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        return ""

def parse_cards_from_html(html: str, category_name: str, item_type: str) -> List[Dict]:
    cards = []
    pattern = re.compile(
        r'<a\s+href="([^"]+)"\s+class="poster-card"[^>]*>.*?'
        r'<img\s+[^>]*src="([^"]+)".*?alt="([^"]+)".*?'
        r'(?:<span\s+class="poster-card-rating">.*?<span>([^<]+)</span>)?.*?'
        r'(?:<span\s+class="poster-card-year">([^<]+)</span>)?',
        re.DOTALL
    )
    for match in pattern.finditer(html):
        href, poster, title, rating, year = match.groups()
        url = href if href.startswith("http") else BASE_URL + href
        title = title.strip()
        poster = poster.strip()
        rating = rating.strip() if rating else "N/A"
        year = year.strip() if year else "2026"
        
        cards.append({
            "title": title,
            "url": url,
            "poster": poster,
            "rating": rating,
            "year": year,
            "category": category_name,
            "type": item_type
        })
    return cards

def harvest_category(cat: Dict, page_limit_per_run: int = 5) -> List[Dict]:
    """Kategoriyi sayfalar boyu (sayfa 1, sayfa 2, ...) tarar."""
    name = cat["name"]
    base_path = cat["base_path"]
    item_type = cat["type"]
    max_pages = min(cat.get("max_pages", 10), page_limit_per_run)
    
    collected = []
    seen_urls = set()
    
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{BASE_URL}{base_path}"
        else:
            url = f"{BASE_URL}{base_path}/sayfa/{page}"
            
        html = fetch_html(url)
        if not html:
            break
            
        items = parse_cards_from_html(html, name, item_type)
        if not items:
            break
            
        new_items = 0
        for it in items:
            if it["url"] not in seen_urls:
                seen_urls.add(it["url"])
                collected.append(it)
                new_items += 1
                
        if new_items == 0:
            break
            
        time.sleep(0.2) # Sunucuyu yormamak için nazik gecikme
        
    return collected

def main():
    print("[*] DiziKorea Derin Sayfalama Harvester Baslatildi...")
    all_items = []
    seen_all = set()
    
    # Her kategoriden ilk 5'er sayfayı derinlemesine tarayalım (hızlı ve dolu bir arşiv için)
    for cat in CATEGORIES:
        name = cat["name"]
        print(f"[*] {name} sayfalari taraniyor...")
        items = harvest_category(cat, page_limit_per_run=6)
        print(f"  -> {name}: {len(items)} adet icerik cikarildi.")
        for it in items:
            if it["url"] not in seen_all:
                seen_all.add(it["url"])
                all_items.append(it)
                
    print(f"\n[+] TOPLAM ARSIV: {len(all_items)} adet film ve dizi bulundu!")
    
    # 1. JSON
    master_catalog = {
        "provider": "DiziKorea",
        "base_url": BASE_URL,
        "total_items": len(all_items),
        "items": all_items
    }
    with open("dizikorea_catalog.json", "w", encoding="utf-8") as f:
        json.dump(master_catalog, f, ensure_ascii=False, indent=2)
        
    # 2. M3U
    with open("dizikorea.m3u", "w", encoding="utf-8") as f:
        f.write('#EXTM3U name="DiziKorea Full Archive"\n\n')
        for item in all_items:
            f.write(
                f'#EXTINF:-1 tvg-id="{item["title"]}" tvg-name="{item["title"]}" '
                f'tvg-logo="{item["poster"]}" group-title="{item["category"]}",'
                f'{item["title"]} ({item["year"]}) [★{item["rating"]}]\n'
            )
            f.write(f'{item["url"]}\n\n')
            
    print("[OK] Dosyalar basariyla olusturuldu.")

if __name__ == "__main__":
    main()
