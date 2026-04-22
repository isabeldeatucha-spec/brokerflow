"""
Record a 90-second demo of the full Sedge flow.
Saves to demo.mp4 in the repo root.

Usage:
    python3.12 record_demo.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8502"
OUTPUT_DIR = Path(__file__).parent


def wait_and_click(page, text: str, timeout: int = 15_000):
    page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
    page.get_by_text(text, exact=False).first.click()


def run_demo(page):
    # ── 1. Dashboard ──────────────────────────────────────────────────────────
    page.goto(BASE_URL)
    page.wait_for_selector("text=Dashboard by Sedge", timeout=30_000)
    time.sleep(1.5)

    # Enable demo mode
    page.get_by_text("Demo mode").first.click()
    page.wait_for_selector("text=Cached results active", timeout=8_000)
    time.sleep(1)

    # ── 2. Type brand in query bar ────────────────────────────────────────────
    query_box = page.get_by_placeholder("Enter any CPG brand name")
    query_box.fill("Chomps")
    time.sleep(0.5)
    page.get_by_role("button", name="▶").first.click()

    # ── 3. Brand Scout loads with cached result ───────────────────────────────
    page.wait_for_selector("text=87", timeout=20_000)  # score
    page.wait_for_selector("text=Broker Brief", timeout=10_000)
    time.sleep(2.5)

    # Scroll down slightly to show the outreach section
    page.evaluate("window.scrollBy(0, 200)")
    time.sleep(1.5)

    # ── 4. Handoff to Admin & Ops ──────────────────────────────────────────────
    page.get_by_role("button", name="📋 Autofill WFM new item form").click()
    page.wait_for_selector("text=Admin & Ops by Sedge", timeout=15_000)
    time.sleep(1.5)

    # Click Autofill form
    page.get_by_role("button", name="▶  Autofill form").click()
    page.wait_for_selector("text=fields autofilled", timeout=30_000)
    time.sleep(2.5)

    # Scroll to show the form
    page.evaluate("window.scrollBy(0, 300)")
    time.sleep(1.5)

    # ── 5. Handoff to Retailer Pitcher ────────────────────────────────────────
    page.get_by_role("button", name="📬 Pitch this to a buyer →").click()
    page.wait_for_selector("text=Draft pitch", timeout=15_000)
    time.sleep(1.5)

    # Click Draft pitch
    page.get_by_role("button", name="Draft pitch").click()
    page.wait_for_selector("text=Outreach email", timeout=15_000)
    time.sleep(3)

    # Click on sell sheet tab
    page.get_by_role("tab", name="1-page sell sheet").click()
    time.sleep(2)

    # ── 6. Final pause on sell sheet ─────────────────────────────────────────
    time.sleep(2)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--window-size=1440,900"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()

        try:
            run_demo(page)
        except Exception as exc:
            print(f"[record_demo] Error during recording: {exc}")
        finally:
            time.sleep(1)
            context.close()
            browser.close()

        # Rename the recorded video to demo.mp4
        videos = list(OUTPUT_DIR.glob("*.webm"))
        if videos:
            latest = max(videos, key=lambda f: f.stat().st_mtime)
            dest = OUTPUT_DIR / "demo.mp4"
            latest.rename(dest)
            print(f"[record_demo] Saved: {dest}")
        else:
            print("[record_demo] No video file found.")


if __name__ == "__main__":
    main()
