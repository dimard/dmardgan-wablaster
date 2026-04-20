/**
 * wa_server.js — WhatsApp Bulk Sender backend
 * Uses whatsapp-web.js for fast, direct WhatsApp Web API access.
 * Exposes a simple REST API consumed by the Python GUI.
 *
 * Endpoints:
 *   GET  /status        → { ready, state }
 *   GET  /qr            → { qr: "data:image/png;base64,..." }
 *   GET  /logs?since=N  → [ { time, msg }, ... ]
 *   POST /send          → { contacts, message, imagePath?, delay? }
 *   POST /restart       → re-initialize the WA client
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express  = require('express');
const qrcode   = require('qrcode');
const cors     = require('cors');
const fs       = require('fs');
const path     = require('path');
const { execSync } = require('child_process');

// ─── Express App ────────────────────────────────────────────────────────────

const app = express();
app.use(cors());
app.use(express.json());

// ─── State ───────────────────────────────────────────────────────────────────

let client        = null;
let currentQR     = null;   // base64 PNG data URL
let isReady       = false;
let clientState   = 'INITIALIZING';
let isSending     = false;
let stopRequested = false;
let logs          = [];     // ring buffer, max 1000 entries
let logIndex      = 0;      // monotonic counter
let sentProgress  = 0;      // pesan berhasil terkirim
let totalProgress = 0;      // total pesan dalam sesi ini


// ─── Helpers ─────────────────────────────────────────────────────────────────

function addLog(msg) {
    const entry = { index: logIndex++, time: new Date().toISOString(), msg };
    logs.push(entry);
    if (logs.length > 1000) logs.shift();
    console.log(msg);
}

function formatNumber(number) {
    return number.replace(/\D/g, '') + '@c.us';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function processSpintax(text) {
    if (!text) return text;
    let str = text;
    let matches;
    // Evaluates innermost brackets first for recursive spintax: {Hello|{Hi|Hey}}
    while ((matches = /\{([^{}]+)\}/.exec(str)) !== null) {
        const options = matches[1].split('|');
        const randomOption = options[Math.floor(Math.random() * options.length)];
        str = str.replace(matches[0], randomOption);
    }
    return str;
}

/**
 * Remove stale Chromium profile lock files and kill any orphaned Chromium
 * process that is still holding the wwebjs_auth session directory.
 * Must be called BEFORE client.initialize().
 */
function cleanupSessionLocks() {
    const sessionDir = path.join(__dirname, 'wwebjs_auth', 'session');
    const lockNames  = ['SingletonLock', 'SingletonSocket', 'SingletonCookie'];

    for (const name of lockNames) {
        const p = path.join(sessionDir, name);
        if (fs.existsSync(p)) {
            try {
                fs.unlinkSync(p);
                console.log(`🧹 Removed stale lock: ${name}`);
            } catch (e) {
                console.warn(`⚠️  Could not remove ${name}: ${e.message}`);
            }
        }
    }

    // Kill any Chromium/Chrome processes holding the session data dir
    try {
        // macOS / Linux
        execSync(
            `pkill -f 'wwebjs_auth' 2>/dev/null || true`,
            { stdio: 'ignore' }
        );
    } catch (_) { /* ignore */ }
}

// ─── WA Client Factory ───────────────────────────────────────────────────────

function initClient() {
    cleanupSessionLocks();   // ← clear stale locks before every init
    addLog('🔧 Menginisialisasi WhatsApp client...');

    client = new Client({
        authStrategy: new LocalAuth({
            dataPath: path.join(__dirname, 'wwebjs_auth')
        }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
            ]
        }
    });

    client.on('qr', async (qr) => {
        try {
            currentQR   = await qrcode.toDataURL(qr);
            clientState = 'QR_READY';
            addLog('📲 QR code siap — silakan scan dari aplikasi.');
        } catch (e) {
            addLog(`⚠️ Gagal generate QR: ${e.message}`);
        }
    });

    client.on('loading_screen', (percent, message) => {
        clientState = 'LOADING';
        addLog(`⏳ Loading: ${percent}% — ${message}`);
    });

    client.on('authenticated', () => {
        clientState = 'AUTHENTICATED';
        currentQR   = null;
        addLog('🔐 Autentikasi berhasil.');
    });

    client.on('auth_failure', (msg) => {
        clientState = 'AUTH_FAILURE';
        isReady     = false;
        addLog(`❌ Autentikasi gagal: ${msg}`);
    });

    client.on('ready', () => {
        isReady     = true;
        currentQR   = null;
        clientState = 'READY';
        addLog('✅ WhatsApp siap! Bisa mulai kirim pesan.');
    });

    client.on('disconnected', (reason) => {
        isReady     = false;
        clientState = 'DISCONNECTED';
        addLog(`⚠️ WhatsApp terputus: ${reason}`);
    });

    client.initialize().catch(e => {
        addLog(`❌ Client init error: ${e.message}`);
        clientState = 'ERROR';
    });
}

// ─── API Routes ───────────────────────────────────────────────────────────────

/** Health / status */
app.get('/status', (req, res) => {
    res.json({ ready: isReady, state: clientState, sending: isSending });
});

/** QR code image (base64 PNG) */
app.get('/qr', (req, res) => {
    res.json({ qr: currentQR });
});

/**
 * Fetch logs since a given index.
 * Client sends ?since=N; server returns entries with index >= N.
 */
app.get('/logs', (req, res) => {
    const since = parseInt(req.query.since ?? '0', 10);
    const slice = logs.filter(e => e.index >= since);
    res.json(slice);
});

/** Bulk send — supports random delay & batch mode */
app.post('/send', async (req, res) => {
    if (!isReady)  return res.status(503).json({ error: 'WhatsApp belum siap. Scan QR terlebih dahulu.' });
    if (isSending) return res.status(409).json({ error: 'Masih mengirim pesan sebelumnya.' });

    const {
        contacts,
        message,
        imagePath,
        minDelay   = 1,    // seconds
        maxDelay   = 3,    // seconds (random between min–max)
        batchSize  = 0,    // 0 = no batching
        batchPause = 5,    // minutes to pause between batches
    } = req.body;

    if (!contacts || contacts.length === 0)
        return res.status(400).json({ error: 'Daftar kontak kosong.' });

    // Respond immediately; sending runs in background
    res.json({ ok: true, total: contacts.length });

    isSending     = true;
    stopRequested = false;
    sentProgress  = 0;
    totalProgress = contacts.length;
    let sendResults = [];

    const useBatch   = batchSize > 0;
    const totalBatch = useBatch ? Math.ceil(contacts.length / batchSize) : 1;

    addLog(`\n🚀 Memulai pengiriman ke ${contacts.length} kontak...`);
    if (useBatch)
        addLog(`📦 Batch mode: ${batchSize} pesan/batch, jeda ${batchPause} menit antar batch`);
    addLog(`⏱️  Jeda acak: ${minDelay}–${maxDelay} detik per pesan\n`);

    let batchNum  = 1;
    let sentCount = 0;

    for (let i = 0; i < contacts.length; i++) {
        // Check stop flag
        if (stopRequested) {
            addLog(`\n⛔ Pengiriman dihentikan pada pesan ke-${i + 1}.`);
            break;
        }

        const number = contacts[i];
        const chatId = formatNumber(number);

        try {
            addLog(`📤 [${i + 1}/${contacts.length}] → ${number}`);
            
            const finalMessage = processSpintax(message);

            if (imagePath && fs.existsSync(imagePath)) {
                const media = MessageMedia.fromFilePath(imagePath);
                await client.sendMessage(chatId, media, { caption: finalMessage });
                addLog('   ✅ Gambar + pesan terkirim!');
            } else {
                await client.sendMessage(chatId, finalMessage);
                addLog('   ✅ Pesan terkirim!');
            }
            sendResults.push({ number, status: 'Berhasil', detail: '-' });
            sentCount++;
            sentProgress++;
        } catch (e) {
            addLog(`   ❌ Gagal: ${e.message}`);
            sendResults.push({ number, status: 'Gagal', detail: e.message || 'Error tidak diketahui' });
        }

        const isLastContact = i === contacts.length - 1;

        // Batch pause: after every batchSize messages (except last contact)
        if (useBatch && !isLastContact && (i + 1) % batchSize === 0) {
            batchNum++;
            const pauseMs = batchPause * 60 * 1000;
            addLog(`\n☕ Batch ${batchNum - 1}/${totalBatch} selesai — istirahat ${batchPause} menit...`);

            // Count down every 30 s so user can see progress
            let remaining = batchPause * 60;
            while (remaining > 0 && !stopRequested) {
                const mins = Math.floor(remaining / 60);
                const secs = remaining % 60;
                addLog(`   ⏳ Lanjut dalam ${mins}m ${secs}s...`);
                await sleep(Math.min(30000, remaining * 1000));
                remaining -= 30;
            }

            if (stopRequested) break;
            addLog(`🚀 Melanjutkan batch ${batchNum}/${totalBatch}...\n`);
            continue;
        }

        // Random delay between messages (skip after last)
        if (!isLastContact) {
            const delayMs = (minDelay + Math.random() * (maxDelay - minDelay)) * 1000;
            await sleep(delayMs);
        }
    }

    addLog(`\n🎉 Selesai! Terkirim: ${sentCount}/${contacts.length} pesan.`);
    
    try {
        const timestamp = new Date().toISOString().replace(/T/, '_').replace(/[:.]/g, '-').slice(0, 19);
        const fileName = `laporan_pengiriman_${timestamp}.html`;
        const htmlFile = path.join(__dirname, fileName);
        
        let successCount = sendResults.filter(r => r.status === 'Berhasil').length;
        let failCount = sendResults.filter(r => r.status === 'Gagal').length;

        let tableRows = '';
        for (const r of sendResults) {
            const isGagal = r.status === 'Gagal';
            const rowStyle = isGagal ? 'background-color: #fff0f0; color: #c62828;' : 'background-color: #ffffff; color: #333;';
            const icon = isGagal ? '❌' : '✅';
            tableRows += `
                <tr style="${rowStyle}">
                    <td style="padding: 12px; border-bottom: 1px solid #ddd;">${r.number}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #ddd; font-weight: bold;">${icon} ${r.status}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #ddd;">${r.detail || '-'}</td>
                </tr>
            `;
        }
        
        const htmlContent = `
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Pengiriman WhatsApp</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { color: #128C7E; margin-top: 0; margin-bottom: 20px; }
        .summary { display: flex; gap: 20px; margin-bottom: 20px; }
        .card { padding: 15px 20px; border-radius: 8px; font-weight: bold; font-size: 16px; min-width: 120px; }
        .card.success { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;}
        .card.fail { background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2;}
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th { background-color: #f8f9fa; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; color: #555;}
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 Laporan Hasil Pengiriman</h2>
        <div class="summary">
            <div class="card success">✅ Berhasil: ${successCount}</div>
            <div class="card fail">❌ Gagal: ${failCount}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Nomor Tujuan</th>
                    <th>Status</th>
                    <th>Detail / Keterangan</th>
                </tr>
            </thead>
            <tbody>
                ${tableRows}
            </tbody>
        </table>
    </div>
</body>
</html>`;
        
        fs.writeFileSync(htmlFile, htmlContent, 'utf-8');
        addLog(`📄 Laporan disimpan (HTML) di: ${fileName}`);
        
        // Coba buka file laporan secara otomatis
        try {
            const { exec } = require('child_process');
            if (process.platform === 'darwin') {
                exec(`open "${htmlFile}"`);
            } else if (process.platform === 'win32') {
                exec(`start "" "${htmlFile}"`);
            } else {
                exec(`xdg-open "${htmlFile}"`);
            }
        } catch (e) {
            // abaikan
        }
    } catch (err) {
        addLog(`⚠️ Gagal menyimpan laporan HTML: ${err.message}`);
    }

    isSending     = false;
    stopRequested = false;
    totalProgress = 0;   // reset setelah selesai
    sentProgress  = 0;
});

/** Progress pengiriman realtime */
app.get('/progress', (req, res) => {
    res.json({ sent: sentProgress, total: totalProgress, sending: isSending });
});

/** Stop a running send session */
app.post('/stop-send', (req, res) => {
    if (!isSending) return res.json({ ok: false, msg: 'Tidak ada pengiriman aktif.' });
    stopRequested = true;
    addLog('⛔ Permintaan stop diterima — menunggu pesan saat ini selesai...');
    res.json({ ok: true });
});


/** Force restart the WA client */
app.post('/restart', async (req, res) => {
    addLog('🔄 Merestart WhatsApp client...');
    isReady     = false;
    currentQR   = null;
    clientState = 'INITIALIZING';

    try { await client.destroy(); } catch { /* ignore */ }

    // Give the browser a moment to exit before cleaning locks
    setTimeout(() => initClient(), 2000);
    res.json({ ok: true });
});

/** Logout: clear session data so next start shows fresh QR */
app.post('/logout', async (req, res) => {
    addLog('🚪 Logout dari WhatsApp & menghapus sesi...');
    isReady     = false;
    currentQR   = null;
    clientState = 'DISCONNECTED';

    // 1. Logout from WhatsApp gracefully
    try { await client.logout(); } catch { /* ignore */ }
    // 2. Destroy Chromium
    try { await client.destroy(); } catch { /* ignore */ }

    // 3. Delete session directory so next start shows fresh QR
    const sessionDir = path.join(__dirname, 'wwebjs_auth');
    try {
        fs.rmSync(sessionDir, { recursive: true, force: true });
        addLog('🗑️  Data sesi dihapus. Server akan berhenti.');
    } catch (e) {
        addLog(`⚠️  Gagal hapus sesi: ${e.message}`);
    }

    // Respond then exit cleanly
    res.json({ ok: true });
    setTimeout(() => process.exit(0), 600);
});

// ─── Boot ─────────────────────────────────────────────────────────────────────

const PORT = 3000;
app.listen(PORT, '127.0.0.1', () => {
    console.log(`🌐 WA Server berjalan di http://127.0.0.1:${PORT}`);
    initClient();
});
