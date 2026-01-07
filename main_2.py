import asyncio
import json
import os
import re
import urllib.parse
import httpx
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Persistence and Config
USER_DATA_DIR = os.path.abspath("./shopee_profile_data")
BASE_URL = "https://shopee.co.id"
HEADLESS = False  # Set to False to login manually first!

# Extraction Functions (copied and refined from main.py)
def parse_info_string(info: str) -> Dict[str, Any]:
    if not info: return {}
    parsed = {}
    score_match = re.search(r'SCORE:([\d.]+)', info)
    if score_match: parsed['score'] = float(score_match.group(1))
    parts = info.split(',')
    for part in parts:
        if ':' in part and '{' not in part:
            k, v = part.split(':', 1)
            parsed[k.strip().lower()] = v.strip()
    return parsed

def extract_shopee_products(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted_products = []
    sections = data.get('data', {}).get('sections', [])
    for section in sections:
        section_data = section.get('data', {})
        top_products = section_data.get('top_product')
        if top_products:
            for item in top_products:
                info_meta = parse_info_string(item.get("info", ""))
                image_ids = item.get("images", [])
                image_urls = [f"https://down-id.img.susercontent.com/file/{img_id}" for img_id in image_ids]
                cat_id = item.get("knodeid") or item.get("key")
                product_url = f"https://shopee.co.id/top_products?catId={urllib.parse.quote(cat_id)}" if cat_id else "#"
                extracted_products.append({
                    "name": item.get("name"),
                    "sold_count": item.get("count"),
                    "label": "Top Product",
                    "product_id": item.get("key"),
                    "score": info_meta.get("score"),
                    "images": image_urls,
                    "primary_image": image_urls[0] if image_urls else None,
                    "type": "Top Product",
                    "url": product_url
                })
    return extracted_products

def extract_suggestions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted = []
    queries = data.get('data', {}).get('queries', [])
    for q in queries:
        text = q.get('text', '')
        img_id = q.get('image') or (q.get('images')[0] if q.get('images') else None)
        primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
        score = None
        tracking = q.get('tracking', '')
        score_match = re.search(r'"rank_score":([\d.]+)', tracking)
        if score_match: score = float(score_match.group(1))
        extracted.append({
            "name": text,
            "sold_count": None,
            "label": "Suggestion",
            "product_id": q.get('item_ids', [None])[0],
            "score": score,
            "images": [primary_image] if primary_image else [],
            "primary_image": primary_image,
            "type": "Suggestion",
            "url": f"https://shopee.co.id/search?keyword={urllib.parse.quote(text)}"
        })
    return extracted

def extract_categories(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    cats = []
    cat_list = data.get('data', {}).get('category_list', [])
    for c in cat_list:
        if c.get('level') == 1:
            cats.append({
                "name": c.get('display_name') or c.get('name'),
                "id": c.get('catid'),
                "image": f"https://down-id.img.susercontent.com/file/{c.get('image')}" if c.get('image') else None,
                "url": f"https://shopee.co.id/{urllib.parse.quote(c.get('display_name', '').replace(' ', '-'))}-cat.{c.get('catid')}"
            })
    return cats

def extract_flash_sales(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted = []
    items = data.get('data', {}).get('items', [])
    for it in items:
        price = (it.get('price') or 0) / 100000
        old_price = (it.get('price_before_discount') or 0) / 100000
        img_id = it.get('image')
        primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
        itemid, shopid = it.get('itemid'), it.get('shopid')
        extracted.append({
            "name": it.get("name"),
            "price": price,
            "old_price": old_price,
            "discount": it.get('discount', ''),
            "sold_count": it.get("historical_sold"),
            "label": "Flash Sale",
            "product_id": f"{shopid}.{itemid}",
            "score": it.get("item_rating", {}).get("rating_star"),
            "images": [primary_image] if primary_image else [],
            "primary_image": primary_image,
            "type": "Flash Sale",
            "url": f"https://shopee.co.id/product-i.{shopid}.{itemid}"
        })
    return extracted

def extract_daily_discover(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted = []
    feeds = data.get('data', {}).get('feeds', [])
    for feed in feeds:
        if feed.get('type') == 'item_card':
            it = feed.get('item_card', {}).get('item', {})
            if not it: continue
            dp = it.get('item_card_display_price', {})
            price = (dp.get('price') or 0) / 100000
            old_price = (dp.get('strikethrough_price') or 0) / 100000
            img_id = it.get('image')
            primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
            itemid, shopid = it.get('itemid'), it.get('shopid')
            extracted.append({
                "name": it.get("name"),
                "price": price,
                "old_price": old_price,
                "discount": dp.get('discount_text', ''),
                "sold_count": it.get("historical_sold") or 0,
                "label": "Daily Discover",
                "product_id": f"{shopid}.{itemid}",
                "score": it.get("item_rating", {}).get("rating_star"),
                "images": [f"https://down-id.img.susercontent.com/file/{img}" for img in it.get('images', [])[:3]],
                "primary_image": primary_image,
                "type": "Daily Discover",
                "url": f"https://shopee.co.id/product-i.{shopid}.{itemid}"
            })
    return extracted

# Visual Generation
def generate_html_report(products, suggestions=[], footer_data={}, categories=[], flash_sales=[], daily_discover=[], output_file="report.html"):
    # (Visual CSS/HTML logic same as main.py but refined)
    def get_cards(items):
        cards_html = ""
        for p in items:
            image_gallery = "".join([f'<img src="{img}" alt="gallery">' for img in p['images'][:3]])
            
            price_html = ""
            if p['type'] in ["Flash Sale", "Daily Discover"]:
                sold_count = p.get('sold_count') or 0
                sold_text = f"⚡ {sold_count:,} terjual" if sold_count > 0 else "✨ Rekomendasi"
                
                old_price_html = ""
                if p.get("old_price") and p["old_price"] > 0:
                    old_price_html = f'<span class="old-price">Rp {p["old_price"]:,.0f}</span>'
                
                discount_html = ""
                if p.get("discount"):
                    discount_html = f'<span class="disc-tag">{p["discount"]}</span>'
                
                price_html = f'''
                <div class="price-box">
                    <span class="curr-price">Rp {p['price']:,.0f}</span>
                    {old_price_html}
                    {discount_html}
                </div>
                '''
            else:
                sold_count = p.get('sold_count') or 0
                sold_text = f"🔥 {sold_count:,} terjual" if sold_count > 0 else "✨ Populer"
            
            score_html = f"<span class='score'>⭐ {p['score']:.2f}</span>" if p.get('score') else ""
            gallery_html = f'<div class="gallery">{image_gallery}</div>' if len(p['images']) > 1 else ''
            
            cards_html += f"""
            <a href="{p['url']}" target="_blank" class="card-link">
                <div class="product-card {p['type'].lower().replace(' ', '-')}">
                    <div class="image-container">
                        <img src="{p['primary_image']}" class="main-img" onerror="this.src='https://placehold.co/400x400?text=No+Image'">
                        <span class="badge {p['type'].lower().replace(' ', '-')}">{p['label']}</span>
                    </div>
                    <div class="product-info">
                        <h3>{p['name']}</h3>
                        {price_html}
                        <div class="stats">
                            <span class="sold">{sold_text}</span>
                            {score_html}
                        </div>
                        {gallery_html}
                        <p class="id-text">ID: {p['product_id']}</p>
                    </div>
                </div>
            </a>"""
        return cards_html

    categories_html = "".join([f'<a href="{c["url"]}" target="_blank" class="category-item"><img src="{c["image"]}"><span>{c["name"]}</span></a>' for c in categories])
    related_links_html = "".join([f'<a href="{link["url"]}" target="_blank" class="trend-tag">#{link["name"]}</a>' for link in footer_data.get('related_links', [])])

    html_template = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Shopee Intel Dynamic</title><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{ --primary: #ee4d2d; --secondary: #2673dd; --flash: #eb4d4b; --discover: #6c5ce7; --bg: #f8f9fa; --card-bg: #fff; --text: #2d3436; }}
        body {{ font-family: 'Outfit', sans-serif; background: var(--bg); margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 50px; }}
        h1 {{ color: var(--primary); font-size: 3rem; margin: 0; }}
        .category-scroll {{ display: flex; overflow-x: auto; gap: 20px; padding: 20px 0; scrollbar-width: none; }}
        .category-item {{ flex: 0 0 auto; display: flex; flex-direction: column; align-items: center; text-decoration: none; color: inherit; }}
        .category-item img {{ width: 70px; height: 70px; background: white; border-radius: 15px; padding: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
        .section-title {{ display: flex; align-items: center; gap: 15px; margin: 40px 0 20px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }}
        .card-link {{ text-decoration: none; color: inherit; height: 100%; }}
        .product-card {{ background: var(--card-bg); border-radius: 18px; overflow: hidden; box-shadow: 0 8px 25px rgba(0,0,0,0.05); transition: 0.3s; border: 1px solid #f0f0f0; }}
        .product-card:hover {{ transform: translateY(-8px); box-shadow: 0 15px 35px rgba(238, 77, 45, 0.1); }}
        .image-container {{ position: relative; height: 280px; }}
        .main-img {{ width: 100%; height: 100%; object-fit: cover; }}
        .badge {{ position: absolute; top: 12px; left: 12px; padding: 4px 12px; border-radius: 20px; color: #fff; font-size: 0.7rem; font-weight: 600; }}
        .badge.top-product {{ background: var(--primary); }}
        .badge.flash-sale {{ background: var(--flash); animation: blink 2s infinite; }}
        .badge.daily-discover {{ background: var(--discover); }}
        .badge.suggestion {{ background: var(--secondary); }}
        @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
        .product-info {{ padding: 20px; }}
        h3 {{ font-size: 1rem; margin: 0 0 10px; height: 2.8rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }}
        .price-box {{ margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
        .curr-price {{ color: var(--primary); font-weight: 600; font-size: 1.2rem; }}
        .old-price {{ color: #999; text-decoration: line-through; font-size: 0.8rem; }}
        .disc-tag {{ background: #fff5f5; color: var(--primary); padding: 2px 5px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
        .stats {{ display: flex; justify-content: space-between; font-size: 0.85rem; color: #666; margin-bottom: 15px; }}
        .gallery {{ display: flex; gap: 5px; }}
        .gallery img {{ width: 45px; height: 45px; border-radius: 6px; object-fit: cover; border: 1px solid #eee; }}
        .id-text {{ font-size: 0.65rem; color: #ccc; margin-top: 10px; }}
        .trends-section {{ background: white; padding: 30px; border-radius: 20px; margin-top: 50px; box-shadow: 0 8px 30px rgba(0,0,0,0.04); }}
        .trend-tag {{ padding: 6px 18px; background: #f1f2f6; color: var(--secondary); border-radius: 30px; text-decoration: none; font-weight: 600; display: inline-block; margin: 5px; transition: 0.2s; }}
        .trend-tag:hover {{ background: var(--secondary); color: white; }}
    </style></head><body><div class="container">
        <header><h1>Shopee Intel Dynamic</h1><p>Real-time Market Intelligence Dashboard</p></header>
        <div class="category-scroll">{categories_html}</div>
        {f'<div class="section-title"><h2 style="color:var(--flash)">⚡ Flash Sale Now</h2></div><div class="grid">{get_cards(flash_sales)}</div>' if flash_sales else ''}
        {f'<div class="section-title" style="margin-top:60px"><h2 style="color:var(--discover)">✨ Daily Discover (For You)</h2></div><div class="grid">{get_cards(daily_discover)}</div>' if daily_discover else ''}
        <div class="section-title" style="margin-top:60px"><h2 style="color:var(--primary)">🔥 Top Products</h2></div><div class="grid">{get_cards(products)}</div>
        {f'<div class="section-title" style="margin-top:60px"><h2 style="color:var(--secondary)">🔍 Market Suggestions</h2></div><div class="grid">{get_cards(suggestions)}</div>' if suggestions else ''}
        {f'<div class="trends-section"><h2>📈 Market Trends & SEO</h2><div class="trends-container">{related_links_html}</div></div>' if related_links_html else ''}
    </div></body></html>
    """
    with open(output_file, 'w', encoding='utf-8') as f: f.write(html_template)
    print(f"\n✅ Dynamic dashboard updated: {output_file}")

# Dynamic Fetching Logic
async def fetch_dynamic_data():
    if not os.path.exists(USER_DATA_DIR): os.makedirs(USER_DATA_DIR)
    
    auth_data = {"headers": {}, "cookies": {}}
    
    async with Stealth().use_async(async_playwright()) as p:
        print(f"🛡️ [Playwright] Launching browser (Headless: {HEADLESS})...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=HEADLESS,
            args=['--disable-blink-features=AutomationControlled'],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="id-ID"
        )
        page = context.pages[0]
        
        print("🌐 [Playwright] Opening Shopee...")
        await page.goto(BASE_URL, wait_until="load", timeout=90000)
        
        print("\n" + "="*50)
        print("🔑 [LOGIN CHECK / MANUAL LOGIN]")
        print("💡 Jika sudah login, klik tombol ENTER di terminal.")
        print("💡 Jika belum login, silakan login di browser dulu, baru klik ENTER.")
        print("="*50)
        
        await asyncio.to_thread(input, "👉 Tekan [ENTER] jika sudah siap tarik data...")
        
        print("🚀 [Browser-Fetch] Executing API calls inside browser context...")
        
        endpoints = {
            "rec": "https://shopee.co.id/api/v4/recommend/recommend?bundle=top_products_homepage&limit=20",
            "cat": "https://shopee.co.id/api/v4/pages/get_category_tree",
            "flash": "https://shopee.co.id/api/v4/flash_sale/flash_sale_get_items?limit=16&need_personalize=true&offset=0&sort_soldout=true&tracker_info_version=1&with_dp_items=true",
            "discover": "https://shopee.co.id/api/v4/homepage/get_daily_discover?bundle=daily_discover_main&item_card=3&limit=60&need_dynamic_translation=false&need_tab=true&offset=0",
            "footer": "https://shopee.co.id/backend/CMS/footer/0/",
            "sug": "https://shopee.co.id/api/v4/search/search_suggestion?bundle=popsearch&limit=10"
        }
        
        results = {}
        for name, url in endpoints.items():
            print(f"  > Fetching {name} via Browser JS...")
            try:
                raw_data = await page.evaluate(f"""
                    fetch("{url}")
                        .then(res => res.json())
                        .catch(err => ({{error: err.message}}))
                """)
                results[name] = raw_data
                with open(f"dynamic_{name}.json", "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, indent=4)
            except Exception as e:
                print(f"  > [Error] {name} failed: {e}")
                results[name] = {}

        await context.close()

    # Data Processing
    print("⚙️ [Processor] Extracting items from browser-fetched results...")
    products = extract_shopee_products(results.get("rec", {}))
    categories = extract_categories(results.get("cat", {}))
    flash_sales = extract_flash_sales(results.get("flash", {}))
    daily_discover = extract_daily_discover(results.get("discover", {}))
    suggestions = extract_suggestions(results.get("sug", {}))
    footer_data = results.get("footer", {})
    
    print(f"📊 Summary: {len(products)} Top, {len(categories)} Categories, {len(flash_sales)} Flash, {len(daily_discover)} Discover, {len(suggestions)} Suggestions.")
    
    # HTML Generation
    generate_html_report(products, suggestions, footer_data, categories, flash_sales, daily_discover, "report_dynamic.html")

if __name__ == "__main__":
    asyncio.run(fetch_dynamic_data())
