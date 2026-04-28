# 🚀 Quick Start Guide - WorkSpotter Service

Panduan cepat untuk langsung menjalankan service dalam 5 menit!

## Step 1: Install Dependencies (1 menit)

Buka terminal/PowerShell di folder project dan jalankan:

```bash
pip install -r requirements.txt
```

Tunggu sampai selesai (mungkin 2-3 menit).

## Step 2: Jalankan Server (30 detik)

Di terminal yang sama, jalankan:

```bash
python main.py
```

Anda akan lihat output seperti:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Artinya server sudah running! ✅

## Step 3: Buka Interactive Docs (30 detik)

Buka browser dan pergi ke:

```
http://localhost:8000/docs
```

Anda akan lihat Swagger UI dengan semua endpoint.

## Step 4: Test API (2 menit)

### Opsi A: Langsung dari Swagger UI

1. Klik endpoint `POST /predict`
2. Klik tombol "Try it out"
3. Copy-paste JSON dari `example_request.json` ke "Request body"
4. Klik tombol "Execute"
5. Lihat Response di bawah

### Opsi B: Pakai curl (di terminal baru)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

Anda akan dapat response seperti:

```json
{
  "predicted_latitude": -6.200267,
  "predicted_longitude": 106.816722,
  "cluster_id": 0,
  "confidence": 0.75
}
```

## ✅ Selesai!

Service sudah berjalan. Sekarang Anda bisa:

- **Modify code** dan server akan auto-reload (karena `reload=True`)
- **Check health:** http://localhost:8000/health
- **View docs:** http://localhost:8000/docs
- **Baca README.md** untuk penjelasan lengkap

## Troubleshooting

### Error: "Port 8000 already in use"

Artinya ada service lain yang pakai port 8000. Gunakan port lain:

```bash
uvicorn main:app --reload --port 8001
```

Kemudian akses: http://localhost:8001

### Error: "ModuleNotFoundError: No module named 'fastapi'"

Berarti belum install dependencies. Jalankan:

```bash
pip install -r requirements.txt
```

### Error: Timeout atau request sangat lambat

Normal untuk data besar. DBSCAN clustering butuh waktu. Untuk optimization, lihat README.md bagian "Pengembangan Selanjutnya".

## Eksperimen

Coba modifikasi file `example_request.json`:

1. **Ubah target_time** ke waktu berbeda
2. **Ubah koordinat** untuk lokasi berbeda
3. **Ubah epsilon_meter** di main.py untuk precision clustering berbeda

Setiap perubahan akan langsung terlihat saat Anda test API lagi!

---

**Happy experimenting!** 🎉
