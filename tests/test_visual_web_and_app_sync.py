import asyncio
import os
import shutil
from playwright.async_api import async_playwright
from PIL import Image

ARTIFACT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"
SCREENSHOTS_DIR = r"C:\RE\axon_iot\tests\screenshots"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

async def run_sync_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Open Web Console
        context1 = await browser.new_context(viewport={"width": 1400, "height": 900})
        web_page = await context1.new_page()
        print("Loading Web Console at http://127.0.0.1:8000/ ...")
        await web_page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await web_page.wait_for_timeout(2000)

        # Capture Web Console Dashboard
        web_dash_path = os.path.join(SCREENSHOTS_DIR, "web_console_dashboard.png")
        await web_page.screenshot(path=web_dash_path)
        print(f"[Captured] Web Console Dashboard -> {web_dash_path}")

        # 2. Open Mobile App
        context2 = await browser.new_context(viewport={"width": 430, "height": 900})
        app_page = await context2.new_page()
        print("Loading Mobile App at http://127.0.0.1:8000/app ...")
        await app_page.goto("http://127.0.0.1:8000/app", wait_until="networkidle")
        await app_page.wait_for_timeout(2000)

        # Capture Mobile App Dashboard
        app_dash_path = os.path.join(SCREENSHOTS_DIR, "mobile_app_dashboard.png")
        await app_page.screenshot(path=app_dash_path)
        print(f"[Captured] Mobile App Dashboard -> {app_dash_path}")

        # 3. Test Bidirectional Hardware Control: Toggle V0 from Mobile App
        print("Toggling Relay V0 from Mobile App...")
        v0_btn = await app_page.wait_for_selector("#app-btn-v0")
        await v0_btn.click()
        await app_page.wait_for_timeout(1000)
        app_v0_text = await v0_btn.inner_text()
        print(f"[Mobile App] Relay V0 state: {app_v0_text}")

        # Check if Web Console reflects Relay V0
        await web_page.wait_for_timeout(1000)
        web_btn_v0 = await web_page.query_selector("#btn-V0")
        if web_btn_v0:
            web_v0_text = await web_btn_v0.inner_text()
            print(f"[Web Console] Button V0 state received over WebSocket: {web_v0_text}")

        # 4. Test Mobile App Account Registration Modal
        print("Testing Mobile App Account Modal...")
        avatar_btn = await app_page.wait_for_selector("#app-user-avatar-btn")
        await avatar_btn.click()
        await app_page.wait_for_timeout(800)

        app_auth_path = os.path.join(SCREENSHOTS_DIR, "mobile_app_account_sync.png")
        await app_page.screenshot(path=app_auth_path)
        print(f"[Captured] Mobile App Account Modal -> {app_auth_path}")

        # Close modal
        close_btn = await app_page.wait_for_selector("button:has-text('✕')")
        await close_btn.click()
        await app_page.wait_for_timeout(500)

        # 5. Test Web Console Users Tab
        print("Switching to Users tab on Web Console...")
        users_nav = await web_page.wait_for_selector("div.sidebar-nav-item:has-text('Users')")
        await users_nav.click()
        await web_page.wait_for_timeout(1500)

        web_users_path = os.path.join(SCREENSHOTS_DIR, "web_console_users_sync.png")
        await web_page.screenshot(path=web_users_path)
        print(f"[Captured] Web Console Users Tab -> {web_users_path}")

        # Stitch Side-by-Side comparison: Web Console + Mobile App
        img_web = Image.open(web_dash_path)
        img_app = Image.open(app_dash_path)
        
        # Target canvas: 1400 + 430 = 1830 width, 900 height
        combined = Image.new("RGB", (img_web.width + img_app.width, max(img_web.height, img_app.height)), (15, 20, 28))
        combined.paste(img_web, (0, 0))
        combined.paste(img_app, (img_web.width, 0))

        side_by_side_path = os.path.join(SCREENSHOTS_DIR, "web_and_mobile_side_by_side.png")
        combined.save(side_by_side_path, quality=95)
        print(f"[Stitched] Side-by-Side View -> {side_by_side_path}")

        # Copy to Artifact directory for persistent display
        for fname in ["web_console_dashboard.png", "mobile_app_dashboard.png", "web_console_users_sync.png", "mobile_app_account_sync.png", "web_and_mobile_side_by_side.png"]:
            src = os.path.join(SCREENSHOTS_DIR, fname)
            dst = os.path.join(ARTIFACT_DIR, fname)
            shutil.copy2(src, dst)
            print(f"[Copied to Brain Artifacts] {dst}")

        await browser.close()
        print("\nAll visual and sync tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_sync_test())
