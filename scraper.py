#!/usr/bin/env python3
"""
DiziKorea Professional Scraper & Stream Resolver
Categories:
  - Kore Dizileri
  - Cin Dizileri
  - Japon Dizileri
  - Tayland Dizileri
  - Tayvan Dizileri
  - Filipin Dizileri
  - Filmler
Outputs:
  - dizikorea_catalog.json (Structured metadata for Media Studio & Android EmirTV / Cloudstream)
  - dizikorea.m3u (Categorized IPTV playlist with logos and group-titles)
"""

import json
import re
import urllib.request
from typing import Dict, List, Optional

BASE_URL = "https://dizikorea3.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CATEGORIES = [
    {"name": "Filmler", "url": f"{BASE_URL}/filmler", "type": "movie"},
    {"name": "Kore Dizileri", "url": f"{BASE_URL}/kore-dizileri-izle-dq", "type": "series"},
    {"name": "Cin Dizileri", "url": f"{BASE_URL}/cin-dizileri", "type": "series"},
    {"name": "Japon Dizileri", "url": f"{BASE_URL}/japon-dizileri", "type": "series"},
    {"name": "Tayland Dizileri", "url": f"{BASE_URL}/tayland-dizileri", "type": "series"},
    {"name": "Tayvan Dizileri", "url": f"{BASE_URL}/tayvan-dizileri", "type": "series"},
    {"name": "Filipin Dizileri", "url": f"{BASE_URL}/filipin-dizileri", "type": "series"},
    {"name": "Efsane Diziler", "url": f"{BASE_URL}/efsane-diziler", "type": "series"},
]

def fetch_html(url: str, referer: Optional[str] = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"[-] Fetch error ({url}): {e}")
        return ""

def extract_vidmoly_m3u8(embed_url: str) -> Optional[str]:
    """VidMoly embed sayfasindan canli master.m3u8 linkini cozer."""
    html = fetch_html(embed_url, referer=BASE_URL)
    if not html:
        return None
    matches = re.findall(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']|sources:\s*\[{\s*file:\s*["\']([^"\']+)["\']', html)
    for m1, m2 in matches:
        link = m1 or m2
        if link and ".m3u8" in link:
            return link
    raw_m3u8 = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
    return raw_m3u8[0] if raw_m3u8 else None

def parse_cards_from_html(html: str, category_name: str, item_type: str) -> List[Dict]:
    """HTML icerisindeki poster-card blogunu profesyonel regex ile ayiklar."""
    cards = []
    # Standart poster-card yapisi
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
        
    # Efsane diziler gibi legend-card yapisi varsa onu da tara
    if not cards:
        legend_pattern = re.compile(
            r'<a\s+href="([^"]+)"\s+class="home-legend-card"\s+title="([^"]+)".*?'
            r'<img\s+src="([^"]+)".*?'
            r'(?:<span\s+class="home-legend-card-imdb".*?<span>([^<]+)</span>)?',
            re.DOTALL
        )
        for match in legend_pattern.finditer(html):
            href, title, poster, rating = match.groups()
            url = href if href.startswith("http") else BASE_URL + href
            poster = poster if poster.startswith("http") else BASE_URL + poster
            cards.append({
                "title": title.strip(),
                "url": url,
                "poster": poster.strip(),
                "rating": rating.strip() if rating else "N/A",
                "year": "Legend",
                "category": category_name,
                "type": item_type
            })
            
    return cards

def resolve_streams(page_url: str) -> List[Dict]:
    """Detay sayfasindaki tum embed ve oynatici kaynaklarini yakalar."""
    html = fetch_html(page_url)
    if not html:
        return []
    
    streams = []
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    
    for ifr in iframes:
        if "vidmoly" in ifr:
            m3u8 = extract_vidmoly_m3u8(ifr)
            if m3u8:
                streams.append({"source": "VidMoly", "m3u8": m3u8, "embed": ifr})
            else:
                streams.append({"source": "VidMoly", "embed": ifr})
        elif "playerdkorea" in ifr:
            streams.append({"source": "PlayerDKorea", "embed": ifr})
        else:
            streams.append({"source": "EmbedPlayer", "embed": ifr})
            
    return streams

def main():
    print("[*] DiziKorea Professional Harvester Baslatildi...")
    
    all_items = []
    catalog_by_category = {}
    
    for cat in CATEGORIES:
        name = cat["name"]
        url = cat["url"]
        item_type = cat["type"]
        print(f"[*] Kategori taranıyor: {name} -> {url}")
        
        html = fetch_html(url)
        items = parse_cards_from_html(html, name, item_type)
        print(f"  [+] {name}: {len(items)} icerik bulundu.")
        
        catalog_by_category[name] = items
        all_items.extend(items)
        
    print(f"\n[+] Toplam {len(all_items)} icerik toplandi.")
    
    # Ornek ilk 5 film icin anlik stream linklerini onceden cozelim
    print("[*] Populer filmlerin HLS master streamleri cozuluyor...")
    for item in all_items:
        if item["category"] == "Filmler" and len(item.get("streams", [])) == 0:
            print(f"  -> Cozuluyor: {item['title']}")
            item["streams"] = resolve_streams(item["url"])
            if len([x for x in all_items if x.get("streams")]) >= 5:
                break
                
    # 1. JSON Export (Meta Data + Kategoriler)
    master_catalog = {
        "provider": "DiziKorea",
        "base_url": BASE_URL,
        "total_items": len(all_items),
        "categories": list(catalog_by_category.keys()),
        "items": all_items
    }
    
    with open("dizikorea_catalog.json", "w", encoding="utf-8") as f:
        json.dump(master_catalog, f, ensure_ascii=False, indent=2)
    print("[OK] dizikorea_catalog.json hazirlandi.")
    
    # 2. M3U Export (Standart IPTV / TiviMate / Media Studio Player Formati)
    with open("dizikorea.m3u", "w", encoding="utf-8") as f:
        f.write('#EXTM3U name="DiziKorea Premium"\n\n')
        
        for item in all_items:
            streams = item.get("streams", [])
            stream_url = ""
            for s in streams:
                if "m3u8" in s:
                    stream_url = s["m3u8"]
                    break
            if not stream_url and streams:
                stream_url = streams[0].get("embed", "")
            if not stream_url:
                stream_url = item["url"]
                
            f.write(
                f'#EXTINF:-1 tvg-id="{item["title"]}" tvg-name="{item["title"]}" '
                f'tvg-logo="{item["poster"]}" group-title="{item["category"]}",'
                f'{item["title"]} ({item["year"]}) [★{item["rating"]}]\n'
            )
            f.write(f'{stream_url}\n\n')
            
    print("[OK] dizikorea.m3u hazirlandi.")
    print("[*] Islem basariyla tamamlandi!")

if __name__ == "__main__":
    main()
