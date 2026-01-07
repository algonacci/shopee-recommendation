import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Persistence directory
USER_DATA_DIR = os.path.abspath("./shopee_profile_data")

async def get_shopee_tokens_persistent():
    print(f"📂 [Persistence] Menggunakan profil di: {USER_DATA_DIR}")
    
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    harvested_data = {
        "url": None,
        "headers": {},
        "cookies": {}
    }

    # Hide automation flags
    launch_args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-infobars',
        '--disable-dev-shm-usage',
    ]

    # Use Stealth v2.0.0 wrapper
    async with Stealth().use_async(async_playwright()) as p:
        print("🌐 [Persistence] Launching persistent context...")
        
        # We use headless=True by default for the script to run in background, 
        # but the user can change it to False if they need to login manually.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True, 
            args=launch_args,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            bypass_csp=True
        )
        
        page = context.pages[0]
        
        # Stealth is already applied by the wrapper to all pages, 
        # but just in case, we can verify with a small script
        is_webdriver = await page.evaluate("navigator.webdriver")
        print(f"🛡️  Stealth Check (navigator.webdriver): {is_webdriver}")

        request_captured = asyncio.Event()

        async def handle_response(response):
            # Target API Recommend
            if "api/v4/recommend/recommend" in response.url:
                print(f"🎯 [Target] API Recommend detected!")
                
                # Check for the specific bundle
                if "bundle=top_products_homepage" in response.url or not harvested_data["url"]:
                    harvested_data["url"] = response.url
                    harvested_data["headers"] = response.request.headers
                    
                    cookies = await context.cookies()
                    harvested_data["cookies"] = {c['name']: c['value'] for c in cookies}
                    
                    try:
                        resp_json = await response.json()
                        with open("response_shopee.json", "w", encoding="utf-8") as f:
                            json.dump(resp_json, f, indent=4)
                        print("📁 Data produk disimpan di: response_shopee.json")
                    except:
                        pass
                    
                    request_captured.set()

        page.on("response", handle_response)

        print("🌐 [Navigasi] Membuka Shopee...")
        try:
            await page.goto("https://shopee.co.id/", wait_until="load", timeout=90000)
            
            # Check for login redirect
            if "login" in page.url:
                print("\n⚠️  [DETEKSI] Redirect ke Login!")
                print("💡 Karena script ini jalan di mode Headless, login manual tidak bisa dilakukan.")
                print("💡 Silakan ganti 'headless=True' jadi 'headless=False' di cek_shopee.py lalu jalankan lagi.")
                
            # Wait for content
            await asyncio.sleep(5)
            
            print("📜 [Action] Scrolling pancingan...")
            for i in range(15):
                if request_captured.is_set():
                    print("✨ Data captured!")
                    break
                    
                scroll_val = 600 + (i * 200)
                await page.evaluate(f"window.scrollBy(0, {scroll_val})")
                print(f"  > Scrolled {scroll_val}px")
                await asyncio.sleep(2)
            
            if not request_captured.is_set():
                # Take a final screenshot to see what happened
                await page.screenshot(path="debug_persistent.png")
                print("📸 Screenshot saved to debug_persistent.png")

        except Exception as e:
            print(f"❌ Error: {e}")
        
        await context.close()

    # Save tokens for HTTPX
    if harvested_data["url"]:
        # Prepare headers for HTTPX
        headers = dict(harvested_data["headers"])
        headers['x-requested-with'] = 'XMLHttpRequest'
        headers['accept'] = 'application/json'
        
        prep_data = {
            "url": harvested_data["url"],
            "headers": headers,
            "cookies": harvested_data["cookies"]
        }
        with open("shopee_prep.json", "w", encoding="utf-8") as f:
            json.dump(prep_data, f, indent=4)
        print("✅ [Sukses] Token & Prep Data disimpan di: shopee_prep.json")
    else:
        print("⚠️ Gagal mendapatkan token recommend.")

if __name__ == "__main__":
    asyncio.run(get_shopee_tokens_persistent())
