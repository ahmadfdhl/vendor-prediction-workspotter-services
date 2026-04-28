# WorkSpotter - Microservice Prediksi Lokasi Pedagang

Aplikasi FastAPI untuk memprediksi lokasi pedagang keliling berdasarkan riwayat checkin menggunakan clustering sederhana (DBSCAN).

## 📋 Apa itu WorkSpotter?

WorkSpotter adalah aplikasi yang membantu pedagang keliling untuk ditemukan customer. Sistem ini berbasis **checkin**, bukan tracking realtime:

- Pedagang **checkin** saat tiba di suatu lokasi
- Pedagang **checkout** saat meninggalkan lokasi
- Lokasi valid karena tidak ada overlap atau data missing

## 🎯 Tujuan Service

Service ini memprediksi **kemungkinan lokasi pedagang** pada waktu tertentu berdasarkan pola historis:

**Input:**
- Data checkin (array dengan vendor_id, waktu checkin/checkout, latitude, longitude)
- Target time (waktu yang ingin diprediksi)

**Output:**
- Prediksi latitude & longitude
- Cluster ID (kelompok lokasi)
- Confidence (tingkat keyakinan 0-1)

## 🏗️ Struktur Folder

```
workspotter-service/
├── main.py                    # File utama dengan semua logika
├── requirements.txt           # Dependencies (library yang diperlukan)
├── example_request.json       # Contoh request ke API
├── README.md                  # File ini (dokumentasi)
└── .gitignore                 # File yang diabaikan git
```

## 🚀 Cara Menjalankan

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Jalankan Server

```bash
python main.py
```

Atau dengan Uvicorn langsung:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Buka Browser dan Test

- **Interactive Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health
- **Root Info:** http://localhost:8000/

## 📡 Cara Menggunakan API

### Endpoint: POST /predict

**URL:** `http://localhost:8000/predict`

**Method:** `POST`

**Request Body:**
```json
{
  "data": [
    {
      "vendor_id": 1,
      "checkin_time": "2026-04-20 10:00:00",
      "checkout_time": "2026-04-20 12:00:00",
      "latitude": -6.200000,
      "longitude": 106.816666
    },
    {
      "vendor_id": 1,
      "checkin_time": "2026-04-21 10:15:00",
      "checkout_time": "2026-04-21 11:45:00",
      "latitude": -6.201000,
      "longitude": 106.817000
    },
    {
      "vendor_id": 1,
      "checkin_time": "2026-04-22 09:30:00",
      "checkout_time": "2026-04-22 13:00:00",
      "latitude": -6.199500,
      "longitude": 106.815500
    }
  ],
  "target_time": "2026-04-20 11:00:00"
}
```

**Response:**
```json
{
  "predicted_latitude": -6.200333,
  "predicted_longitude": 106.816555,
  "cluster_id": 0,
  "confidence": 0.87
}
```

## 🧠 Cara Kerja (Logika Algoritma)

### Step 1: Clustering Lokasi (DBSCAN)
- Semua koordinat latitude/longitude di-cluster menggunakan DBSCAN
- Metrik yang digunakan: **Haversine** (jarak berdasarkan bola bumi)
- Radius clustering: ~100 meter
- Setiap titik checkin mendapat cluster_id

```python
# Contoh hasil:
Checkin 1: lat -6.200, lon 106.816 → cluster 0
Checkin 2: lat -6.201, lon 106.817 → cluster 0  (dekat, same cluster)
Checkin 3: lat -6.199, lon 106.815 → cluster 0  (dekat, same cluster)
```

### Step 2: Expand Data Per Jam
- Data interval checkin-checkout dipecah menjadi per jam
- Contoh: checkin 10:00-12:00 menjadi jam 10 dan jam 11

```python
# Contoh:
Checkin jam 10:00-12:00, cluster 0
↓
Jam 10 → cluster 0
Jam 11 → cluster 0
```

### Step 3: Mapping Waktu → Cluster
- Setiap kombinasi (hari_minggu, jam) dipetakan ke cluster yang paling sering muncul
- Dihitung frekuensi kemunculan

```python
# Contoh:
(Senin, jam 10) → cluster 0 muncul 5x, cluster 1 muncul 2x → pilih cluster 0
(Senin, jam 11) → cluster 0 muncul 4x, cluster 1 muncul 1x → pilih cluster 0
```

### Step 4: Prediksi
- Dari target_time, ambil hari dan jam
- Cari cluster yang paling sering di jam itu
- Hitung rata-rata lat/lon dari semua point di cluster tersebut

```python
# Contoh:
Target time: Senin jam 11
→ (Senin, 11) → cluster 0
→ Ambil semua point di cluster 0
→ Rata-rata: lat -6.200333, lon 106.816555
→ Confidence = 4/5 = 0.80 (4 kemunculan dari 5 total data)
```

## 📊 Format Data Input

Setiap item dalam array `data` harus memiliki struktur:

```json
{
  "vendor_id": integer,           // ID vendor/pedagang
  "checkin_time": "YYYY-MM-DD HH:MM:SS",  // Waktu checkin
  "checkout_time": "YYYY-MM-DD HH:MM:SS", // Waktu checkout
  "latitude": float,              // Koordinat lintang (negatif untuk selatan)
  "longitude": float              // Koordinat bujur (positif untuk timur)
}
```

### Contoh Data Jakarta:
- Latitude: -6.200000 (Jakarta Pusat)
- Longitude: 106.816666 (Jakarta Pusat)

## ⚙️ Parameter Tuning

### Clustering Radius

Ubah `epsilon_meter` di fungsi `training_model()`:

```python
# Saat ini: 100 meter
model = training_model(request.data, epsilon_meter=100)

# Ubah ke nilai lain:
model = training_model(request.data, epsilon_meter=50)   # Cluster lebih ketat
model = training_model(request.data, epsilon_meter=200)  # Cluster lebih longgar
```

**Penjelasan:**
- **Kecil (50m):** Cluster hanya untuk lokasi yang sangat dekat
- **Besar (200m):** Cluster untuk lokasi yang lebih jauh

## 🔧 Testing dengan curl

### Test Health Check:
```bash
curl http://localhost:8000/health
```

### Test Predict:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

Atau gunakan file `example_request.json` yang sudah disediakan.

## 📚 Dokumentasi Interaktif

FastAPI menyediakan dokumentasi interaktif otomatis:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Di sini Anda bisa:
- Melihat semua endpoint
- Melihat struktur request/response
- Test API langsung dari browser

## 🎓 Penjelasan Teknis untuk Pemula

### Apa itu DBSCAN?

DBSCAN adalah algoritma clustering yang mengelompokkan titik berdasarkan:
1. **Jarak** (epsilon) - titik dalam radius tertentu dianggap satu cluster
2. **Kepadatan** - cluster terbentuk jika ada cukup banyak titik berdekatan

**Keuntungan:**
- Tidak perlu menentukan jumlah cluster di awal
- Bisa mendeteksi outlier (noise)
- Bagus untuk lokasi geografis

### Apa itu Haversine?

Haversine adalah formula untuk menghitung jarak antara dua titik di permukaan bola bumi.

**Kenapa tidak pakai Euclidean?**
- Euclidean: garis lurus di bidang datar (tidak akurat untuk bumi)
- Haversine: mengikuti lengkung bumi (akurat untuk koordinat GPS)

```python
# Contoh:
Titik A: -6.200, 106.816
Titik B: -6.201, 106.817

Euclidean: ~0.001575 (salah, anggap bumi datar)
Haversine: ~111 meter (benar, mempertimbangkan lengkung bumi)
```

### Confidence Score

Confidence menunjukkan seberapa **yakin** prediksi kami:

```
Confidence = Jumlah kemunculan cluster / Total data di jam itu

Contoh:
- (Senin, 11:00): cluster 0 muncul 4x, cluster 1 muncul 1x
- Confidence = 4 / 5 = 0.80 (80% yakin)

- Jika ada 10 data tapi cluster 0 hanya 3x:
- Confidence = 3 / 10 = 0.30 (30% yakin)
```

## ❓ FAQ

**Q: Bagaimana jika tidak ada data untuk jam tersebut?**
A: API akan return error 400 dengan pesan "Tidak ada data untuk hari X jam Y".

**Q: Bisakah prediksi untuk waktu yang berbeda hari?**
A: Ya! Sistem mempertimbangkan hari dalam seminggu, jadi Senin jam 11 berbeda dengan Rabu jam 11.

**Q: Bagaimana jika semua checkin di lokasi yang sama?**
A: Akan ada 1 cluster, dan prediksi akan selalu ke lokasi itu dengan confidence 1.0.

**Q: Minimum data berapa untuk prediksi akurat?**
A: Semakin banyak data semakin baik. Minimum: 3-5 checkin di jam yang sama, ideali: 10+ per jam.

**Q: Bisa dipakai untuk vendor yang berbeda-beda?**
A: Saat ini per request hanya 1 vendor. Untuk multi-vendor, ubah logika di `training_model()`.

## 📝 Notes untuk Pengembangan Selanjutnya

1. **Database:** Simpan data checkin ke database (PostgreSQL/MySQL) agar bisa historical
2. **Cache:** Simpan hasil clustering agar tidak perlu recompute setiap request
3. **Multi-vendor:** Buat model terpisah untuk setiap vendor
4. **Seasonal:** Pertimbangkan musim/liburan untuk prediksi yang lebih akurat
5. **UI:** Buat dashboard untuk visualisasi lokasi dan prediksi
6. **Notification:** Alert customer jika vendor dekat lokasi mereka

## 📄 License

Ini adalah project pembelajaran untuk siswa SMK RPL.

## 👨‍💻 Author

Student Project - WorkSpotter Service

---

**Happy Learning!** 🎉
