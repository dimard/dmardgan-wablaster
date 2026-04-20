# 💬 WhatsApp Bulk Message Sender (WABlaster)

Aplikasi Desktop yang dibuat menggunakan Python (CustomTkinter) untuk mengirim pesan massal WhatsApp secara otomatis. Dilengkapi dengan dua engine (Node.js & Selenium) yang dapat dipilih sesuai kebutuhan, serta fitur Spintax dan Laporan Pengiriman.

---

## 🌟 Fitur Utama

✅ **Dua Mode Pengiriman**:
   - ⚡ **Mode Cepat (wwebjs Node.js)**: Pengiriman super cepat lewat API background.
   - 🛡️ **Mode Aman (Selenium)**: Otomatisasi melalui browser asli secara visual (human-like delay) untuk meminimalisir kemungkinan banned.
   
✅ **Dukungan Spintax (Pesan Acak Variatif)**:  
   Gunakan format `{Halo|Hai|Selamat pagi}` agar setiap pesan yang terkirim berbeda-beda, sehingga WhatsApp tidak mendeteksi sebagai *spam* atau *bot*.

✅ **Kirim Media & Gambar**:  
   Mendukung pengiriman pesan teks yang dilengkapi gambar ke banyak kontak sekaligus.

✅ **Laporan HTML Interaktif**:  
   Setiap selesai sesi pengiriman (terutama pada Mode Aman), aplikasi akan men-generate Laporan Pengiriman berformat `.html` yang detail dan rapi (berisi status Sukses/Gagal untuk setiap nomor kontak).

✅ **Progress Tracker Interaktif**:  
   Terdapat status *live UI* yang menampilkan jumlah pesan terkirim, serta tombol untuk menghentikan paksa (Cancel) kapan saja.

✅ **Upload File Kontak**:  
   Dapat menerima list kontak dari file `.txt`, `.csv`, atau `.xml`.  
   *(Pastikan setiap nomor berada pada baris baru dan menggunakan kode negara tanpa tanda plus, misalnya: 6281234567890)*.

---

## ⚙️ Persyaratan Sistem (Requirements)

Aplikasi ini membutuhkan dependencies berikut:
1. **Python 3.10+** (untuk menjalankan GUI Desktop).
2. **Node.js** (wajib ada untuk menjalankan server Mode Cepat wwebjs).
3. **Browser Google Chrome** atau **Brave Browser** (untuk Mode Aman menggunakan Selenium).

---

## 🚀 Instalasi & Cara Menjalankan

### 1️⃣ Clone the repository
```bash
git clone https://github.com/dimard/dmardgan-wablaster.git
cd dmardgan-wablaster
```

### 2️⃣ Install Dependencies (Python & Node.js)
```bash
# Install library untuk Python
pip install -r requirements.txt

# Install module untuk backend Node.js (wwebjs & express)
npm install
```

### 3️⃣ Menjalankan Aplikasi

- **Bagi Pengguna Mac OS**:
  Klik 2x pada file `WA_Sender_Mac.command` atau buka terminal lalu jalankan perintah:
  ```bash
  python3 app_ui.py
  ```
  *(Jika baru pertama kali, beri izin execute pada file WA_Sender_Mac.command dengan perintah `chmod +x WA_Sender_Mac.command`)*.

- **Bagi Pengguna Windows**:
  Jalankan file `build.bat` atau jalankan dari command prompt:
  ```bash
  python app_ui.py
  ```

---

## 📝 Contoh Penggunaan Spintax 

Spintax (*Spinal Syntax*) sangat dianjurkan agar akun Anda aman dan tidak terdeteksi mesin spam.

**Contoh Pesan di Kotak Pesan Aplikasi:**
```text
{Halo|Hai|Halo kak}, jangan lewatkan promo {spesial|menarik|terbatas} hari ini ya!
```

**Hasil pesan yang terkirim:**
- Kontak 1 menerima: "Halo, jangan lewatkan promo khusus hari ini ya!"
- Kontak 2 menerima: "Hai, jangan lewatkan promo terbatas hari ini ya!"
- Kontak 3 menerima: "Halo kak, jangan lewatkan promo menarik hari ini ya!"

---

## 🪪 Struktur Folder Penting

- `chrome_whatsapp_profile/`: Menyimpan sesi login WhatsApp Web untuk Mode Aman (agar tidak perlu selalu *scan barcode* saat mode diaktifkan).
- `wwebjs_auth/` & `.wwebjs_cache/`: Menyimpan sesi autentikasi dan cache untuk Mode Cepat (Node.js).
- `media/`: Folder untuk file foto yang ingin dilampirkan.
- `laporan_pengiriman_*.html`: Berkas yang ter-generate otomatis sebagai histori pengiriman.

*(Data sensitif di dalam folder tersebut sudah aman karena telah masuk daftar `gitignore`).*

---

## © Copyright & Kredit

Aplikasi WhatsApp Automation ini dikembangkan oleh:

**Raden Dimard Nugroho**  
🌐 Website : [www.dimardnugroho.web.id](https://www.dimardnugroho.web.id)  
📷 Instagram : [@dimardnugroho](https://instagram.com/dimardnugroho)  

*(Proyek ini adalah bentuk antarmuka visual Python dipadukan script pengiriman handal melalui NodeJs dan Selenium yang terus dilakukan pembaruan).*
