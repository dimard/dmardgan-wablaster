import os
import re
import sys
import time
import random
from datetime import datetime
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# macOS uses Command key for paste, Windows/Linux uses Control
PASTE_KEY = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

# ---------- PERSISTENT DRIVER SINGLETON ----------
# Chrome is launched ONCE via launch_chrome(), then reused for every send.
# We use remote-debugging-port so Selenium attaches to the same window.

_driver = None
DEBUG_PORT = 9222


def process_spintax(text):
    """Process spintax syntax: {option1|option2|option3} → picks one randomly.
    Supports nested spintax like {Hello|{Hi|Hey}} by evaluating innermost first."""
    if not text:
        return text
    result = text
    # Keep replacing innermost {…} groups until none remain
    while True:
        match = re.search(r'\{([^{}]+)\}', result)
        if not match:
            break
        options = match.group(1).split('|')
        chosen = random.choice(options)
        result = result[:match.start()] + chosen + result[match.end():]
    return result


def _cleanup_profile_lock(profile_path):
    """Remove stale SingletonLock so Chrome can reuse the profile after a crash/detach."""
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        p = os.path.join(profile_path, name)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def launch_chrome():
    """
    Launch a NEW managed Chrome window with remote-debugging enabled.
    Called once by the UI button. Returns (driver, is_new).
    """
    global _driver

    # Already alive — just return it
    if _driver is not None:
        try:
            _ = _driver.window_handles
            return _driver, False
        except Exception:
            _driver = None

    profile_path = os.path.join(os.getcwd(), "chrome_whatsapp_profile")
    os.makedirs(profile_path, exist_ok=True)
    _cleanup_profile_lock(profile_path)

    options = Options()
    options.add_argument(f"--remote-debugging-port={DEBUG_PORT}")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")

    service = Service(ChromeDriverManager().install())
    _driver = webdriver.Chrome(service=service, options=options)
    
    # Auto-navigate to WhatsApp Web
    try:
        _driver.get("https://web.whatsapp.com")
    except Exception:
        pass
        
    return _driver, True


def get_driver():
    """
    Return the existing driver. If Chrome was closed, reconnect via remote-debug.
    Raises RuntimeError if Chrome has never been launched.
    """
    global _driver

    # Happy path: driver still alive
    if _driver is not None:
        try:
            _ = _driver.window_handles
            return _driver, False
        except Exception:
            _driver = None

    # Try to attach to an already-running Chrome on the debug port
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=options)
        _ = _driver.window_handles  # confirm connection
        return _driver, False
    except Exception:
        _driver = None

    raise RuntimeError(
        "Chrome belum dibuka. Klik tombol '🌐 Buka Chrome' terlebih dahulu."
    )


def quit_driver():
    """Cleanly quit the Chrome driver (called when the app exits)."""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


# ---------- LOGGING ----------
def log_result(status, number, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs.txt", "a", encoding="utf-8") as log:
        log.write(f"[{timestamp}] {status} - {number} {details}\n")


# ---------- MAIN FUNCTION ----------
def send_whatsapp_messages(contacts, message, image_path=None, delay=2, log_callback=None, progress_callback=None, stop_event=None):
    """
    Send WhatsApp messages with optional image attachment and caption.
    Optimized for instant caption → send click.
    Returns: list of dicts [{"number": ..., "status": ..., "detail": ...}]
    """
    
    send_results = []


    def log(text):
        print(text)
        if log_callback:
            log_callback(text + "\n")

    def human_type(element, text):
        """Simulate human typing for the first few characters, then paste the rest to save time."""
        if not text:
            return True
            
        # Ketik 5 karakter pertama agar indikator "sedang mengetik..." muncul di WA
        type_len = min(5, len(text))
        typing_chars = text[:type_len]
        remaining_text = text[type_len:]
        
        for char in typing_chars:
            if stop_event and stop_event.is_set(): return False
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.06))
            
        # Paste sisanya langsung secara instan
        if remaining_text:
            pyperclip.copy(remaining_text)
            element.send_keys(PASTE_KEY, "v")
            
        # Jeda sangat kecil agar paste ter-render di Chrome
        time.sleep(0.3)
        return True

    # ---------- CHROME SETUP ----------
    log("🧩 Checking Chrome instance...")

    try:
        driver, is_new = get_driver()
    except RuntimeError as e:
        log(f"⚠️ {e}")
        return
    except Exception as e:
        log(f"❌ Gagal terhubung ke Chrome: {e}")
        return

    # ---------- OPEN WHATSAPP (only if new window) ----------
    if is_new:
        log("🔗 Opening WhatsApp Web...")
        driver.get("https://web.whatsapp.com")

        try:
            # If QR is visible
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@aria-label='Scan me!']"))
            )
            log("📲 QR code detected — please scan it once.")
            WebDriverWait(driver, 300).until_not(
                EC.presence_of_element_located((By.XPATH, "//canvas[@aria-label='Scan me!']"))
            )
            log("✅ QR scanned successfully!")
        except Exception:
            log("✅ WhatsApp Web already logged in (session restored).")
    else:
        log("♻️ Reusing existing Chrome window — tidak perlu login ulang.")

    # ---------- IMAGE SENDER ----------
    def send_image_with_caption(img_path, caption):
        """Attach an image and send instantly with caption."""
        try:
            log("📎 Attaching image...")

            # 1️⃣ Click the attach button
            attach_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@aria-label='Attach' or @title='Attach']")
                )
            )
            driver.execute_script("arguments[0].click();", attach_btn)
            time.sleep(0.7)

            # 2️⃣ Select and upload image
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@accept='image/*,video/mp4,video/3gpp,video/quicktime']",
                    )
                )
            )
            file_input.send_keys(img_path)
            log("🖼️ Image selected, waiting for preview...")
            time.sleep(2.0)

            # 3️⃣ Wait for preview or send button to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@aria-label='Send' or @role='button']")
                )
            )

            # 4️⃣ Type caption (fast paste)
            caption_added = False
            caption_selectors = [
                "//div[@contenteditable='true'][@data-tab='10']",
                "//div[@role='textbox'][@contenteditable='true']",
                "//div[contains(@aria-label,'Type a message')]",
            ]
            for sel in caption_selectors:
                try:
                    caption_box = driver.find_element(By.XPATH, sel)
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", caption_box
                    )
                    caption_box.click()
                    pyperclip.copy(caption)
                    caption_box.send_keys(PASTE_KEY, "v")
                    caption_added = True
                    log("✅ Caption added successfully.")
                    break
                except Exception:
                    continue

            if not caption_added:
                log("⚠️ Could not add caption, sending image only.")

            # 5️⃣ Instantly find and click send button (no extra wait)
            send_btn_selectors = [
                "//span[@data-icon='send']/ancestor::button",
                "//button[@aria-label='Send' or @title='Send']",
                "//div[@aria-label='Send']",
            ]

            send_btn = None
            # ⚡ Try finding immediately
            for sel in send_btn_selectors:
                try:
                    send_btn = driver.find_element(By.XPATH, sel)
                    if send_btn.is_enabled():
                        break
                except Exception:
                    continue

            # fallback: short wait if not found instantly
            if not send_btn:
                send_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@aria-label='Send' or @title='Send']")
                    )
                )

            # 🚀 Hit send immediately (no delay)
            driver.execute_script("arguments[0].click();", send_btn)
            log("✅ Image (and caption) sent instantly.")
            return True

        except Exception as e:
            log(f"⚠️ Image send failed: {e}")
            return False

    # ---------- HELPER: open a chat WITHOUT reloading the page ----------
    def open_chat_fast(number):
        """
        Navigate to a chat using WhatsApp's in-app New Chat search.
        No page reload → significantly faster than driver.get(send?phone=...).
        Returns the message input box, or None on failure.
        """
        try:
            # 1. Click the "New chat" pencil/compose icon
            new_chat_selectors = [
                "//span[@data-icon='new-chat-outline']",
                "//span[@data-icon='compose']",
                "//div[@aria-label='New chat']",
                "//button[@aria-label='New chat']",
            ]
            new_chat_btn = None
            for sel in new_chat_selectors:
                try:
                    new_chat_btn = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    break
                except Exception:
                    continue

            if new_chat_btn:
                driver.execute_script("arguments[0].click();", new_chat_btn)
                time.sleep(0.25)

            # 2. Type number in search box
            search_input = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
                )
            )
            search_input.click()
            time.sleep(0.3)
            # Clear any previous text — use PASTE_KEY (Command on macOS, Ctrl on Windows)
            search_input.send_keys(PASTE_KEY, "a")
            time.sleep(0.1)
            pyperclip.copy(number)
            search_input.send_keys(PASTE_KEY, "v")
            time.sleep(0.3)

            # 3. Wait for search results to load
            time.sleep(1.5)

            # Try multiple selectors to find the contact result
            contact_result = None
            contact_selectors = [
                f"//span[@title='{number}']",
                f"//span[contains(@title,'{number}')]",
                # Match list items in search results
                "//div[@id='pane-side']//div[@role='listitem'][1]",
                "//div[@id='pane-side']//div[contains(@class,'matched-text')]",
            ]
            for sel in contact_selectors:
                try:
                    contact_result = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    if contact_result:
                        break
                except Exception:
                    continue

            if not contact_result:
                return None

            driver.execute_script("arguments[0].click();", contact_result)
            time.sleep(0.5)

            # 4. Get message input box — try multiple selectors
            input_box = None
            input_selectors = [
                '//div[@contenteditable="true"][@data-tab="10"]',
                '//div[@contenteditable="true"][@title="Type a message"]',
                '//div[@contenteditable="true"][contains(@aria-label,"Type a message")]',
                '//div[@contenteditable="true"][@role="textbox"][@data-tab="10"]',
                '//footer//div[@contenteditable="true"]',
            ]
            for sel in input_selectors:
                try:
                    input_box = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    if input_box:
                        break
                except Exception:
                    continue
            return input_box

        except Exception as e:
            log(f"⚠️ Fast navigation failed ({e}), using fallback...")
            return None

    def open_chat_url(number):
        """Fallback: URL navigation (slower, causes page reload)."""
        # Clean number: remove spaces, dashes; ensure starts with country code
        clean_num = number.replace(' ', '').replace('-', '').replace('+', '')
        # If starts with 0, assume Indonesian (+62)
        if clean_num.startswith('0'):
            clean_num = '62' + clean_num[1:]
        driver.get(f"https://web.whatsapp.com/send?phone={clean_num}&text=")
        
        # Wait for page to load and try to find the invalid number popup
        time.sleep(3)
        
        # Check if "Phone number shared via url is invalid" popup appeared
        try:
            invalid_popup = driver.find_element(
                By.XPATH, "//div[contains(text(),'Phone number shared via url is invalid') or contains(text(),'invalid')]")
            if invalid_popup:
                log(f"⚠️ Nomor {number} tidak valid di WhatsApp.")
                # Click OK to dismiss
                try:
                    ok_btn = driver.find_element(By.XPATH, "//div[@role='button']")
                    ok_btn.click()
                except Exception:
                    pass
                return None
        except NoSuchElementException:
            pass  # No popup = number is valid
        
        input_box = None
        input_selectors = [
            '//div[@contenteditable="true"][@data-tab="10"]',
            '//div[@contenteditable="true"][@title="Type a message"]',
            '//div[@contenteditable="true"][contains(@aria-label,"Type a message")]',
            '//footer//div[@contenteditable="true"]',
        ]
        for _ in range(40):
            for sel in input_selectors:
                try:
                    input_box = driver.find_element(By.XPATH, sel)
                    if input_box:
                        return input_box
                except NoSuchElementException:
                    pass
            time.sleep(0.5)
        return input_box

    # ---------- MAIN LOOP ----------
    for idx, number in enumerate(contacts, start=1):
        if stop_event and stop_event.is_set():
            log("\n⛔ Pengiriman dihentikan oleh pengguna.")
            break
            
        try:
            log(f"\n📤 [{idx}/{len(contacts)}] → {number}")

            # ⚡ Try fast in-app navigation first (no page reload)
            input_box = open_chat_fast(number)

            # Fallback to URL if in-app nav failed
            if not input_box:
                log("🔄 Switching to URL fallback...")
                input_box = open_chat_url(number)

            if not input_box:
                log(f"⚠️ Chat box not found for {number}. Skipping.")
                log_result("❌ FAILED", number, "(Chat box not found)")
                send_results.append({"number": number, "status": "Gagal", "detail": "Chat box not found"})
            else:
                # ✨ Process spintax for EACH contact (unique message per recipient)
                final_message = process_spintax(message)
                if final_message != message:
                    log(f"🎲 Spintax → \"{final_message[:60]}{'...' if len(final_message) > 60 else ''}\"")

                # --- Send Image + Caption or plain text ---
                if image_path and os.path.exists(image_path):
                    success = send_image_with_caption(image_path, final_message)
                    if not success:
                        log("⚠️ Image failed, sending text only.")
                        input_box.click()
                        if not human_type(input_box, final_message): break
                        
                        try:
                            send_btn = WebDriverWait(driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']/ancestor::button | //button[@aria-label='Send' or @title='Send'] | //button[span[@data-icon='send']]"))
                            )
                            driver.execute_script("arguments[0].click();", send_btn)
                        except Exception:
                            input_box.send_keys(Keys.ENTER)
                            
                        log("✅ Text sent as fallback.")
                        log_result("✅ TEXT ONLY SENT", number)
                        send_results.append({"number": number, "status": "Berhasil", "detail": "Text fallback"})
                    else:
                        log_result("✅ IMAGE+TEXT SENT", number)
                        send_results.append({"number": number, "status": "Berhasil", "detail": "Image + Text"})
                else:
                    input_box.click()
                    if not human_type(input_box, final_message): break
                    
                    try:
                        send_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']/ancestor::button | //button[@aria-label='Send' or @title='Send'] | //button[span[@data-icon='send']]"))
                        )
                        driver.execute_script("arguments[0].click();", send_btn)
                    except Exception:
                        input_box.send_keys(Keys.ENTER)
                        
                    log("✅ Pesan terkirim!")
                    log_result("✅ TEXT SENT", number)
                    send_results.append({"number": number, "status": "Berhasil", "detail": "-"})

            if progress_callback:
                progress_callback(idx, len(contacts))

            # Brief pause to avoid WhatsApp rate-limits
            if idx < len(contacts):
                time.sleep(delay)

        except WebDriverException as e:
            log(f"⚠️ Gagal kirim ke {number}: {e}")
            log_result("❌ FAILED", number, str(e))
            send_results.append({"number": number, "status": "Gagal", "detail": str(e)})

    log("\n🎉 Proses Selesai!")
    log("📝 Chrome tetap terbuka — tutup manual jika sudah selesai.")
    
    return send_results


# ---------- TEST RUN ----------
if __name__ == "__main__":
    test_contacts = ["91XXXXXXXXXX"]  # Replace with your test number
    test_message = "🚀 Instant caption test (send button speed optimized)"
    test_image = os.path.join(os.getcwd(), "media", "test.jpg")  # adjust if needed

    send_whatsapp_messages(test_contacts, test_message, image_path=test_image, delay=1.5)
