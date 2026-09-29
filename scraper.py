#!/usr/bin/env python3
"""
DiziKorea Scraper & Stream Resolver
Site: https://dizikorea3.com/
Üretilenler:
  - dizikorea_catalog.json (PC Media Studio & Cloudstream için tam katalog)
  - dizikorea.m3u (Canlı oynatıcılar için M3U8 listesi)
"""

import json
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

BASE_URL = "https://dizikorea3.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_html(url: str, referer: Optional[str] = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"[-] Hata ({url}): {e}")
        return ""

def extract_vidmoly_m3u8(embed_url: str) -> Optional[str]:
    """VidMoly embed sayfasından direkt master.m3u8 linkini ayıklar."""
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

def get_latest_movies() -> List[Dict]:
    """Son eklenen filmleri çeker."""
    html = fetch_html(f"{BASE_URL}/filmler")
    if not html:
        return []
    
    movies = []
    cards = re.findall(
        r'<a\s+href="([^"]+/film/[^"]+)"\s+class="poster-card"[^>]*>.*?<img\s+src="([^"]+)".*?alt="([^"]+)".*?<span\s+class="poster-card-rating">.*?<span>([^<]+)</span>.*?<span\s+class="poster-card-year">([^<]+)</span>',
        html,
        re.DOTALL
    )
    
    for url, poster, title, rating, year in cards[:15]:
        movies.append({
            "title": title.strip(),
            "url": url if url.startswith("http") else BASE_URL + url,
            "poster": poster.strip(),
            "rating": rating.strip(),
            "year": year.strip(),
            "type": "movie"
        })
    return movies

def get_latest_series() -> List[Dict]:
    """Son eklenen / popüler dizileri çeker."""
    html = fetch_html(f"{BASE_URL}/kore-dizileri-izle-dq")
    if not html:
        return []
    
    series_list = []
    cards = re.findall(
        r'<a\s+href="([^"]+/dizi/[^"]+)"\s+class="poster-card"[^>]*>.*?<img\s+src="([^"]+)".*?alt="([^"]+)".*?<span\s+class="poster-card-rating">.*?<span>([^<]+)</span>.*?<span\s+class="poster-card-year">([^<]+)</span>',
        html,
        re.DOTALL
    )
    
    for url, poster, title, rating, year in cards[:15]:
        series_list.append({
            "title": title.strip(),
            "url": url if url.startswith("http") else BASE_URL + url,
            "poster": poster.strip(),
            "rating": rating.strip(),
            "year": year.strip(),
            "type": "series"
        })
    return series_list

def resolve_item_streams(page_url: str) -> List[Dict]:
    """Film veya dizi bölüm sayfasındaki iframe ve m3u8 kaynaklarını çözer."""
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
            streams.append({"source": "Player", "embed": ifr})
            
    return streams

def run():
    print("[*] DiziKorea taramasi baslatiliyor...")
    movies = get_latest_movies()
    print(f"[+] {len(movies)} film bulundu.")
    
    series = get_latest_series()
    print(f"[+] {len(series)} dizi bulundu.")
    
    print("[*] Ilk filmlerin yayin linkleri cozuluyor...")
    for m in movies[:3]:
        print(f"  -> Cozuluyor: {m['title']}")
        m["streams"] = resolve_item_streams(m["url"])
    
    catalog = {
        "provider": "DiziKorea",
        "base_url": BASE_URL,
        "total_movies": len(movies),
        "total_series": len(series),
        "movies": movies,
        "series": series
    }
    
    # 1. JSON Ciktisi (Cloudstream & PC App icin)
    with open("dizikorea_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print("[OK] dizikorea_catalog.json olusturuldu.")
    
    # 2. M3U Oynatma Listesi Ciktisi
    with open("dizikorea.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for m in movies:
            streams = m.get("streams", [])
            stream_url = ""
            for s in streams:
                if "m3u8" in s:
                    stream_url = s["m3u8"]
                    break
            if not stream_url and streams:
                stream_url = streams[0].get("embed", "")
            if not stream_url:
                stream_url = m["url"]
                
            f.write(f'#EXTINF:-1 tvg-logo="{m["poster"]}" group-title="Filmler",{m["title"]} ({m["year"]})\n')
            f.write(f'{stream_url}\n')
            
    print("[OK] dizikorea.m3u olusturuldu.")

if __name__ == "__main__":
    run()
