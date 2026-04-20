Note: This is a example of what can be done using automation. Don't Use this to send bulk messages it may lead to account restriction as its against whatsapp rules

# 💬 WhatsApp Automation by CoderzWeb

A modern Python application that automates WhatsApp message sending — including **text, media, and multiple contacts** — powered by **Selenium** and **CustomTkinter**.  
Built with a clean WhatsApp-inspired interface and a one-click setup.  

---

## 🌟 Features

✅ Send **text + image messages** to multiple contacts  
✅ Upload **contacts list (.txt or .xml)** directly  
✅ Stay **logged in automatically** (no QR scan every time)  
✅ Smooth, modern **GUI (CustomTkinter)**  
✅ **Live logs** with progress feedback  
✅ Cross-platform (Windows / Linux / macOS)  

---

## 🖼️ Screenshot

| Light Theme UI |
|----------------|
| ![WhatsApp Automation UI](docs/ui_light.png) |

---

## ⚙️ Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/whatsapp-automation.git
cd whatsapp-automation
2️⃣ Create a virtual environment (recommended)
bash
Copy code
python -m venv venv
source venv/bin/activate    # macOS / Linux
venv\Scripts\activate       # Windows
3️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
(If you don’t have a requirements.txt, create one by running pip freeze > requirements.txt)

▶️ Usage
Run the GUI
bash
Copy code
python app_ui.py
Steps:
Choose your contacts file (contacts.txt or .xml)

Select an image (optional)

Type your message

Click 🚀 Send Messages

✅ The app will automatically open WhatsApp Web and start sending messages one by one.

🧩 Contacts File Format
The app supports .txt or .xml contact lists.
Each phone number must include the country code and be on a new line.

Example — contacts.txt:

Copy code
919876543210
919812345678
919865432198

🪪 Folder Info
Folder / File	Description
chrome_whatsapp_profile/	Stores Chrome login session (auto-created)
media/	Optional folder for storing message images
logs.txt	Logs each message status
.gitignore	Protects local data from being pushed to GitHub

🧹 Note: chrome_whatsapp_profile/ and selenium_whatsapp_session/ are ignored from Git to protect your personal session and privacy.

🧠 Tech Stack
🐍 Python 3.10+

🌐 Selenium

🪟 CustomTkinter

📋 Pyperclip

⚙️ WebDriver Manager

💻 Developer
👨‍💻 Ayub Khan
💼 CoderzWeb — Innovative Web Development & Digital Solutions

🧾 License
This project is licensed under the MIT License — free to use, modify, and distribute.
See LICENSE for details.

⭐ Support
If you find this project useful:

Star ⭐ the repository

Share it with developers or businesses that could benefit

Connect with us on website: CoderzWeb.vercel.app

🧾 License

This project is licensed under the MIT License — free to use, modify, and distribute.
See LICENSE
 for details.
