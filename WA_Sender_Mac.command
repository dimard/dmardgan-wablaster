#!/bin/bash

# Pindah ke direktori tempat script ini berada
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "Memulai WhatsApp Bulk Sender..."
echo "================================="

# Gunakan virtual environment jika tersedia
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Jalankan aplikasi Python UI
python3 app_ui.py

# Jeda jika aplikasi crash agar pengguna bisa melihat pesan error
echo ""
echo "Aplikasi telah ditutup."
read -p "Tekan Enter untuk keluar..."
