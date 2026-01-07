import httpx
import json
import asyncio

async def fetch_shopee_direct():
    print("🚀 [Direct] Loading intercepted tokens from shopee_prep.json...")
    
    try:
        with open("shopee_prep.json", "r", encoding="utf-8") as f:
            prep = json.load(f)
    except FileNotFoundError:
        print("❌ Prep file not found. Run cek_shopee.py first!")
        return

    url = prep["url"]
    headers = prep["headers"]
    cookies = prep["cookies"]

    print(f"📡 [Direct] Sending request to: {url[:60]}...")
    
    # We use HTTP/2 because Shopee likes it
    async with httpx.AsyncClient(http2=True, cookies=cookies) as client:
        try:
            response = await client.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # Try to extract count
                sections = data.get('data', {}).get('sections', [])
                product_count = 0
                for section in sections:
                    prods = section.get('data', {}).get('top_product', [])
                    product_count += len(prods)
                
                print(f"✅ [Sukses] Berhasil mengambil {product_count} produk secara langsung!")
                
                # Save fresh data
                with open("response_shopee.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print("📁 Data terbaru disimpan di: response_shopee.json")
                
            else:
                print(f"❌ [Error] Status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ [Exception] {e}")

if __name__ == "__main__":
    asyncio.run(fetch_shopee_direct())
