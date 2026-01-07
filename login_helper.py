import asyncio
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_DATA_DIR = os.path.abspath("./shopee_profile_data")

async def open_manual_browser():
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)
        
    async with Stealth().use_async(async_playwright()) as p:
        print(f"🌐 [Manual Mode] Membuka browser...")
        print(f"📂 Lokasi Profile: {USER_DATA_DIR}")
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="id-ID",
            viewport={"width": 1366, "height": 768}
        )
        
        page = context.pages[0]
        print("🚀 Membuka Shopee... Silakan login/selesaikan captcha sampai benar-benar masuk.")
        await page.goto("https://shopee.co.id/", wait_until="load")
        
        print("\n" + "="*50)
        print("🔓 BROWSER BERJALAN DALAM MODE MANUAL")
        print("💡 Silakan selesaikan Login/Captcha di jendela browser.")
        print("💡 Browser TIDAK AKAN ditutup otomatis.")
        print("💡 Jika sudah selesai dan mau tutup, tekan [CTRL+C] di terminal ini.")
        print("="*50)
        
        try:
            # Tetap hidup sampai user mematikan lewat terminal (Ctrl+C)
            while True:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\n👋 Menutup browser...")
        finally:
            await context.close()

if __name__ == "__main__":
    try:
        asyncio.run(open_manual_browser())
    except KeyboardInterrupt:
        pass
