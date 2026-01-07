import json
import re
import urllib.parse
from typing import List, Dict, Any

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Reads and parses a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {}

def parse_info_string(info: str) -> Dict[str, Any]:
    """Parses the comma-separated info string into a dictionary."""
    if not info:
        return {}
    
    parsed = {}
    score_match = re.search(r'SCORE:([\d.]+)', info)
    if score_match:
        parsed['score'] = float(score_match.group(1))
    
    parts = info.split(',')
    for part in parts:
        if ':' in part and '{' not in part:
            k, v = part.split(':', 1)
            parsed[k.strip().lower()] = v.strip()
            
    return parsed

def extract_shopee_products(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts essential product information from the Shopee API response."""
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
                encoded_cat_id = urllib.parse.quote(cat_id) if cat_id else ""
                product_url = f"https://shopee.co.id/top_products?catId={encoded_cat_id}"
                
                product = {
                    "name": item.get("name"),
                    "sold_count": item.get("count"),
                    "label": "Top Product",
                    "product_id": item.get("key"),
                    "score": info_meta.get("score"),
                    "images": image_urls,
                    "primary_image": image_urls[0] if image_urls else None,
                    "type": "Top Product",
                    "url": product_url
                }
                extracted_products.append(product)
    return extracted_products

def extract_suggestions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts products from the search suggestions API."""
    extracted = []
    queries = data.get('data', {}).get('queries', [])
    for q in queries:
        text = q.get('text', '')
        img_id = q.get('image') or (q.get('images')[0] if q.get('images') else None)
        primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
        
        encoded_keyword = urllib.parse.quote(text)
        search_url = f"https://shopee.co.id/search?keyword={encoded_keyword}"
        
        score = None
        tracking = q.get('tracking', '')
        score_match = re.search(r'"rank_score":([\d.]+)', tracking)
        if score_match:
            score = float(score_match.group(1))

        item = {
            "name": text,
            "sold_count": None,
            "label": "Suggestion",
            "product_id": q.get('item_ids', [None])[0],
            "score": score,
            "images": [primary_image] if primary_image else [],
            "primary_image": primary_image,
            "type": "Suggestion",
            "url": search_url
        }
        extracted.append(item)
    return extracted

def extract_categories(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts top-level categories."""
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
    """Extracts flash sale items."""
    extracted = []
    items = data.get('data', {}).get('items', [])
    for it in items:
        # Price is multiplied by 10^5 in API
        raw_price = it.get('price') or 0
        raw_old_price = it.get('price_before_discount') or 0
        
        price = raw_price / 100000
        old_price = raw_old_price / 100000
        discount = it.get('discount', '')
        
        img_id = it.get('image')
        primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
        
        itemid = it.get('itemid')
        shopid = it.get('shopid')
        product_url = f"https://shopee.co.id/product-i.{shopid}.{itemid}"
        
        item = {
            "name": it.get("name"),
            "price": price,
            "old_price": old_price,
            "discount": discount,
            "sold_count": it.get("historical_sold"),
            "label": "Flash Sale",
            "product_id": f"{shopid}.{itemid}",
            "score": it.get("item_rating", {}).get("rating_star"),
            "images": [primary_image] if primary_image else [],
            "primary_image": primary_image,
            "type": "Flash Sale",
            "url": product_url
        }
        extracted.append(item)
    return extracted

def extract_daily_discover(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts items from Daily Discover."""
    extracted = []
    feeds = data.get('data', {}).get('feeds', [])
    for feed in feeds:
        if feed.get('type') == 'item_card':
            it = feed.get('item_card', {}).get('item', {})
            if not it: continue
            
            display_price = it.get('item_card_display_price', {})
            raw_price = display_price.get('price') or 0
            raw_old_price = display_price.get('strikethrough_price') or 0
            
            price = raw_price / 100000
            old_price = raw_old_price / 100000
            discount = display_price.get('discount_text', '')
            
            img_id = it.get('image')
            primary_image = f"https://down-id.img.susercontent.com/file/{img_id}" if img_id else None
            
            itemid = it.get('itemid')
            shopid = it.get('shopid')
            product_url = f"https://shopee.co.id/product-i.{shopid}.{itemid}"
            
            item = {
                "name": it.get("name"),
                "price": price,
                "old_price": old_price,
                "discount": discount,
                "sold_count": it.get("historical_sold") or 0,
                "label": "Daily Discover",
                "product_id": f"{shopid}.{itemid}",
                "score": it.get("item_rating", {}).get("rating_star"),
                "images": [f"https://down-id.img.susercontent.com/file/{img}" for img in it.get('images', [])[:3]],
                "primary_image": primary_image,
                "type": "Daily Discover",
                "url": product_url
            }
            extracted.append(item)
    return extracted

def generate_html_report(products: List[Dict[str, Any]], suggestions: List[Dict[str, Any]] = None, footer_data: Dict[str, Any] = None, categories: List[Dict[str, Any]] = None, flash_sales: List[Dict[str, Any]] = None, daily_discover: List[Dict[str, Any]] = None, output_file: str = "report.html"):
    """Generates a premium HTML dashboard."""
    
    def get_cards(items):
        cards_html = ""
        for p in items:
            image_gallery = "".join([f'<img src="{img}" alt="gallery">' for img in p['images'][:3]])
            
            # Custom info for different types
            if p['type'] in ["Flash Sale", "Daily Discover"]:
                sold_count = p.get('sold_count') or 0
                sold_text = f"⚡ {sold_count:,} terjual" if sold_count > 0 else "✨ Rekomendasi"
                price_html = f"""
                <div class="price-box">
                    <span class="curr-price">Rp {p['price']:,.0f}</span>
                    {f'<span class="old-price">Rp {p["old_price"]:,.0f}</span>' if p.get('old_price') and p['old_price'] > 0 else ''}
                    {f'<span class="disc-tag">{p["discount"]}</span>' if p.get('discount') else ''}
                </div>
                """
            else:
                sold_text = f"🔥 {p['sold_count']:,} terjual" if p.get('sold_count') else "✨ Populer"
                price_html = ""
                
            badge_text = p['label']
            
            cards_html += f"""
            <a href="{p['url']}" target="_blank" class="card-link">
                <div class="product-card {p['type'].lower().replace(' ', '-')}">
                    <div class="image-container">
                        <img src="{p['primary_image']}" alt="{p['name']}" class="main-img" onerror="this.src='https://placehold.co/400x400?text=No+Image'">
                        <span class="badge {p['type'].lower().replace(' ', '-')}">{badge_text}</span>
                    </div>
                    <div class="product-info">
                        <h3>{p['name']}</h3>
                        {price_html}
                        <div class="stats">
                            <span class="sold">{sold_text}</span>
                            {f'<span class="score">⭐ {p["score"]:.2f}</span>' if p["score"] else ''}
                        </div>
                        {'<div class="gallery">' + image_gallery + '</div>' if len(p['images']) > 1 else ''}
                        <p class="id-text">Target: {p['product_id']}</p>
                    </div>
                </div>
            </a>
            """
        return cards_html

    # Process Categories
    categories_html = ""
    if categories:
        for cat in categories:
            categories_html += f"""
            <a href="{cat['url']}" target="_blank" class="category-item">
                <img src="{cat['image']}" alt="{cat['name']}">
                <span>{cat['name']}</span>
            </a>
            """

    # Process Related Links from Footer
    related_links_html = ""
    if footer_data and footer_data.get('related_links'):
        for link in footer_data['related_links']:
            related_links_html += f'<a href="{link["url"]}" target="_blank" class="trend-tag">#{link["name"]}</a>'

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Shopee Intel Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #ee4d2d;
                --secondary: #2673dd;
                --flash: #eb4d4b;
                --discover: #6c5ce7;
                --accent: #2ecc71;
                --bg: #f8f9fa;
                --card-bg: #ffffff;
                --text: #2d3436;
            }}
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 40px 20px;
            }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            header {{ text-align: center; margin-bottom: 60px; }}
            h1 {{ font-size: 3rem; color: var(--primary); margin: 0; letter-spacing: -1px; }}
            .subtitle {{ opacity: 0.7; font-size: 1.1rem; }}
            
            /* Category Navigation */
            .category-scroll {{
                display: flex;
                overflow-x: auto;
                gap: 20px;
                padding: 20px 0;
                margin-bottom: 50px;
                scrollbar-width: none;
                mask-image: linear-gradient(to right, black 85%, transparent);
            }}
            .category-scroll::-webkit-scrollbar {{ display: none; }}
            .category-item {{
                flex: 0 0 auto;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-decoration: none;
                color: inherit;
                transition: transform 0.2s;
            }}
            .category-item:hover {{ transform: translateY(-5px); }}
            .category-item img {{
                width: 80px;
                height: 80px;
                background: white;
                border-radius: 20px;
                padding: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.03);
                object-fit: contain;
                margin-bottom: 10px;
            }}
            .category-item span {{ font-size: 0.85rem; font-weight: 600; text-align: center; width: 100px; }}

            .section-title {{
                display: flex;
                align-items: center;
                gap: 15px;
                margin: 40px 0 25px;
                padding-bottom: 10px;
                border-bottom: 2px solid #eee;
            }}
            .section-title h2 {{ margin: 0; font-size: 1.8rem; }}
            
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 30px;
            }}
            
            .card-link {{
                text-decoration: none;
                color: inherit;
                display: block;
            }}
            
            .product-card {{
                background: var(--card-bg);
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.05);
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                border: 1px solid rgba(0,0,0,0.05);
                height: 100%;
            }}
            .product-card:hover {{
                transform: translateY(-10px);
                box-shadow: 0 20px 40px rgba(238, 77, 45, 0.12);
            }}
            .flash-sale:hover {{ box-shadow: 0 20px 40px rgba(235, 77, 75, 0.2); }}
            .daily-discover:hover {{ box-shadow: 0 20px 40px rgba(108, 92, 231, 0.15); }}
            
            .image-container {{ position: relative; height: 300px; background: #f0f0f0; }}
            .main-img {{ width: 100%; height: 100%; object-fit: cover; }}
            
            .badge {{
                position: absolute; top: 15px; left: 15px;
                padding: 6px 15px; border-radius: 30px;
                color: white; font-size: 0.75rem; font-weight: 600;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            }}
            .badge.top-product {{ background: var(--primary); }}
            .badge.suggestion {{ background: var(--secondary); }}
            .badge.flash-sale {{ background: var(--flash); animation: pulse 2s infinite; }}
            .badge.daily-discover {{ background: var(--discover); }}
            
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.8; }}
                100% {{ opacity: 1; }}
            }}
            
            .product-info {{ padding: 25px; }}
            h3 {{
                margin: 0 0 15px; font-size: 1.1rem; line-height: 1.4;
                height: 3.1rem; overflow: hidden; display: -webkit-box;
                -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            }}
            
            .price-box {{ margin-bottom: 15px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
            .curr-price {{ color: var(--primary); font-weight: 600; font-size: 1.3rem; }}
            .flash-sale .curr-price {{ color: var(--flash); }}
            .old-price {{ color: #95a5a6; text-decoration: line-through; font-size: 0.9rem; }}
            .disc-tag {{ background: #fff5f5; color: var(--primary); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
            .flash-sale .disc-tag {{ color: var(--flash); }}

            .stats {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            .sold {{ font-weight: 600; color: #636e72; font-size: 0.9rem; }}
            .score {{ color: #ffa502; font-weight: 600; background: #fffaf0; padding: 2px 10px; border-radius: 6px; font-size: 0.9rem; }}
            
            .gallery {{ display: flex; gap: 8px; }}
            .gallery img {{ width: 50px; height: 50px; border-radius: 8px; object-fit: cover; border: 1px solid #eee; }}
            
            .trends-section {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                margin-top: 80px;
                margin-bottom: 40px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.05);
            }}
            .trends-container {{ display: flex; flex-wrap: wrap; gap: 12px; }}
            .trend-tag {{ padding: 8px 20px; background: #f1f2f6; color: var(--secondary); border-radius: 50px; text-decoration: none; font-weight: 600; transition: all 0.2s; }}
            .trend-tag:hover {{ background: var(--secondary); color: white; transform: scale(1.05); }}
            
            @media (max-width: 768px) {{
                h1 {{ font-size: 2rem; }}
                .grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Shopee Intel Dashboard</h1>
                <p class="subtitle">Complete Intelligence Center: All Shopee Channels Decoded</p>
            </header>

            {f'''
            <div class="category-scroll">
                {categories_html}
            </div>
            ''' if categories_html else ''}

            {f'''
            <div class="section-title">
                <h2 style="color: var(--flash)">⚡ Flash Sale Now</h2>
            </div>
            <div class="grid">
                {get_cards(flash_sales)}
            </div>
            ''' if flash_sales else ''}

            {f'''
            <div class="section-title" style="margin-top: 80px;">
                <h2 style="color: var(--discover)">✨ Daily Discover (For You)</h2>
            </div>
            <div class="grid">
                {get_cards(daily_discover)}
            </div>
            ''' if daily_discover else ''}

            <div class="section-title" style="margin-top: 80px;">
                <h2 style="color: var(--primary)">🔥 Top Products</h2>
            </div>
            <div class="grid">
                {get_cards(products)}
            </div>

            {f'''
            <div class="section-title" style="margin-top: 80px;">
                <h2 style="color: var(--secondary)">🔍 Market Suggestions</h2>
            </div>
            <div class="grid">
                {get_cards(suggestions)}
            </div>
            ''' if suggestions else ''}

            {f'''
            <div class="trends-section">
                <div class="section-title" style="margin-top: 0; border: none;">
                    <h2 style="color: var(--accent)">📈 Market Trends & SEO Keywords</h2>
                </div>
                <div class="trends-container">
                    {related_links_html}
                </div>
            </div>
            ''' if related_links_html else ''}
        </div>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"\n✨ Premium dashboard updated: {output_file}")

if __name__ == "__main__":
    # Load Recommendation Data
    rec_data = load_json_data("response_shopee.json")
    products = extract_shopee_products(rec_data)
    
    # Load Suggestion Data
    sug_data = load_json_data("search_suggestion_shopee.json")
    suggestions = extract_suggestions(sug_data) if sug_data else []
    
    # Load Footer Data
    footer_data = load_json_data("response_footer.json")
    
    # Load Category Data
    cat_data = load_json_data("response_category.json")
    categories = extract_categories(cat_data)
    
    # Load Flash Sale Data
    flash_data = load_json_data("response_flash_sale.json")
    flash_sales = extract_flash_sales(flash_data) if flash_data else []
    
    # Load Daily Discover Data
    discover_data = load_json_data("response_daily_discover.json")
    daily_discover = extract_daily_discover(discover_data) if discover_data else []
    
    print(f"Loaded {len(products)} Top Products, {len(suggestions)} Suggestions, {len(categories)} Categories, {len(flash_sales)} Flash Sales, {len(daily_discover)} Discover Items.")
    
    # Generate the combined visual report
    generate_html_report(products, suggestions, footer_data, categories, flash_sales, daily_discover)
