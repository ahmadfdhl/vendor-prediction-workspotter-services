# 🏗️ Architecture & Data Flow - WorkSpotter Service

Dokumentasi arsitektur dan alur data service.

## Arsitektur Keseluruhan

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Laravel/Mobile)                   │
│                                                               │
│  Kirim JSON dengan:                                          │
│  - Array data checkin (vendor_id, waktu, lat, lon)           │
│  - Target time (waktu yang ingin diprediksi)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                    HTTP POST
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   FASTAPI SERVICE                            │
│                  (main.py - port 8000)                       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Endpoint POST /predict                              │   │
│  │  - Validasi input (Pydantic)                         │   │
│  │  - Jalankan training_model()                         │   │
│  │  - Jalankan prediksi_lokasi()                        │   │
│  │  - Return response (lat, lon, cluster_id, conf)     │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PROCESSING (Dalam Memory)                           │   │
│  │                                                       │   │
│  │  Step 1: Clustering DBSCAN + Haversine              │   │
│  │  Step 2: Expand data per jam                        │   │
│  │  Step 3: Mapping (hari, jam) → cluster              │   │
│  │  Step 4: Prediksi lokasi                            │   │
│  │                                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Library yang digunakan:                                    │
│  - scikit-learn (DBSCAN)                                    │
│  - numpy (numerical computing)                              │
│  - fastapi (web framework)                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ JSON Response
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Response)                         │
│                                                               │
│  {                                                           │
│    "predicted_latitude": -6.200267,                         │
│    "predicted_longitude": 106.816722,                       │
│    "cluster_id": 0,                                         │
│    "confidence": 0.75                                       │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Prediksi

```
INPUT: Array Checkin
┌────────────────────────────────────────────────┐
│ vendor_id: 1                                   │
│ checkin_time: 2026-04-20 10:00:00             │
│ checkout_time: 2026-04-20 12:00:00            │
│ latitude: -6.200000                            │
│ longitude: 106.816666                          │
├────────────────────────────────────────────────┤
│ vendor_id: 1                                   │
│ checkin_time: 2026-04-20 15:00:00             │
│ checkout_time: 2026-04-20 17:30:00            │
│ latitude: -6.208000                            │
│ longitude: 106.820000                          │
├────────────────────────────────────────────────┤
│ ... (lebih banyak data checkin)               │
└────────────────────────────────────────────────┘
           │
           ▼
STEP 1: CLUSTERING DENGAN DBSCAN
┌────────────────────────────────────────────────┐
│ Konversi koordinat ke radian                  │
│ Gunakan DBSCAN dengan:                        │
│  - epsilon: 100m (converted to radian)        │
│  - metric: haversine (bola bumi)              │
│  - min_samples: 1                             │
│                                                 │
│ Hasil:                                         │
│ Point 1 (-6.200, 106.816) → Cluster 0       │
│ Point 2 (-6.201, 106.817) → Cluster 0       │
│ Point 3 (-6.208, 106.820) → Cluster 1       │
│ Point 4 (-6.209, 106.819) → Cluster 1       │
│ ... (semua point dapat cluster_id)           │
└────────────────────────────────────────────────┘
           │
           ▼
STEP 2: EXPAND DATA PER JAM
┌────────────────────────────────────────────────┐
│ Checkin: 10:00 - 12:00 (Senin)                │
│ Cluster: 0                                    │
│         │                                      │
│         ├─ Jam 10 → Cluster 0                │
│         └─ Jam 11 → Cluster 0                │
│                                                │
│ Checkin: 15:00 - 17:30 (Senin)               │
│ Cluster: 1                                    │
│         │                                      │
│         ├─ Jam 15 → Cluster 1                │
│         ├─ Jam 16 → Cluster 1                │
│         └─ Jam 17 → Cluster 1                │
│                                                │
│ ... (semua interval di-expand)                │
└────────────────────────────────────────────────┘
           │
           ▼
STEP 3: MAPPING (HARI, JAM) → CLUSTER
┌────────────────────────────────────────────────┐
│ Key (hari_minggu, jam) → Frekuensi Cluster   │
│                                                │
│ (0, 10):  {0: 5, 1: 0}   ─► Cluster 0 (5x)   │
│ (0, 11):  {0: 4, 1: 1}   ─► Cluster 0 (4x)   │
│ (0, 15):  {0: 0, 1: 3}   ─► Cluster 1 (3x)   │
│ (0, 16):  {0: 1, 1: 5}   ─► Cluster 1 (5x)   │
│ (0, 17):  {0: 0, 1: 3}   ─► Cluster 1 (3x)   │
│ (1, 10):  {0: 4, 1: 0}   ─► Cluster 0 (4x)   │
│ ... (semua kombinasi hari+jam)                │
└────────────────────────────────────────────────┘
           │
           ▼
INPUT: target_time: 2026-04-20 11:00:00
           │
           ▼
STEP 4: PREDIKSI
┌────────────────────────────────────────────────┐
│ 1. Parse target_time                          │
│    - Day of week: 0 (Senin)                   │
│    - Hour: 11                                  │
│                                                │
│ 2. Cari di mapping:                           │
│    Key (0, 11) → {0: 4, 1: 1}               │
│                                                │
│ 3. Ambil cluster dengan frekuensi tertinggi:  │
│    Cluster 0 (4 kemunculan)                   │
│                                                │
│ 4. Hitung rata-rata koordinat Cluster 0:      │
│    Points: [(-6.200, 106.816),               │
│              (-6.201, 106.817),               │
│              (-6.199, 106.815)]              │
│    Rata-rata: (-6.200, 106.816)              │
│                                                │
│ 5. Hitung confidence:                         │
│    4 kemunculan / 5 total = 0.80             │
└────────────────────────────────────────────────┘
           │
           ▼
OUTPUT: Response
┌────────────────────────────────────────────────┐
│ {                                              │
│   "predicted_latitude": -6.200267,            │
│   "predicted_longitude": 106.816722,          │
│   "cluster_id": 0,                            │
│   "confidence": 0.80                          │
│ }                                              │
└────────────────────────────────────────────────┘
```

## Struktur Folder & File

```
workspotter-service/
│
├── main.py
│   ├── Pydantic Models
│   │   ├── CheckinData (input checkin)
│   │   ├── PredictRequest (input request)
│   │   └── PredictResponse (output response)
│   │
│   ├── Helper Functions
│   │   └── koordinat_ke_radian()
│   │
│   ├── Core Functions
│   │   ├── clustering_lokasi() → DBSCAN + Haversine
│   │   ├── expand_data_per_jam() → interval to hourly
│   │   ├── training_model() → build model
│   │   └── prediksi_lokasi() → predict location
│   │
│   └── FastAPI Endpoints
│       ├── POST /predict
│       ├── GET /health
│       └── GET /
│
├── requirements.txt (library dependencies)
├── README.md (dokumentasi lengkap)
├── QUICK_START.md (panduan cepat)
├── ARCHITECTURE.md (file ini)
├── example_request.json (contoh request)
└── .gitignore (file git ignore)
```

## Fungsi-Fungsi Utama

### 1. `koordinat_ke_radian(latitude, longitude)`
```
Input:  latitude=-6.200, longitude=106.816
        ↓
        Konversi degree ke radian menggunakan math.radians()
        ↓
Output: latitude_radian=-0.108, longitude_radian=1.863
```

### 2. `clustering_lokasi(latitudes, longitudes, epsilon_meter, min_samples)`
```
Input:  List latitude, List longitude, radius=100m
        ↓
        - Konversi ke radian
        - Jalankan DBSCAN dengan Haversine metric
        ↓
Output: {
          'labels': [0, 0, 1, 1, ...],  // cluster id per point
          'n_clusters': 2,               // jumlah cluster
          'original_coords': [(-6.200, 106.816), ...]
        }
```

### 3. `training_model(checkin_list, epsilon_meter)`
```
Input:  List CheckinData
        ↓
        - Step 1: Extract latitude & longitude
        - Step 2: Clustering DBSCAN
        - Step 3: Expand per jam
        - Step 4: Mapping (hari, jam) → cluster
        ↓
Output: {
          'clustering_result': {...},
          'jam_cluster_mapping': {(0, 10): [0, 0, 1], ...},
          'jam_cluster_counts': {(0, 10): {0: 2, 1: 1}, ...}
        }
```

### 4. `prediksi_lokasi(target_time, model, checkin_list)`
```
Input:  target_time="2026-04-20 11:00:00", model dari training
        ↓
        - Parse hari & jam dari target_time
        - Cari cluster paling sering
        - Hitung rata-rata koordinat
        - Hitung confidence
        ↓
Output: PredictResponse {
          predicted_latitude: -6.200267,
          predicted_longitude: 106.816722,
          cluster_id: 0,
          confidence: 0.80
        }
```

## Konsep Penting

### DBSCAN (Density-Based Spatial Clustering)

**Cara kerja:**
1. Untuk setiap point, cari berapa banyak point lain dalam radius epsilon
2. Jika minimal min_samples point ditemukan, bentuk cluster
3. Point yang tidak termasuk dalam cluster apapun disebut "noise" (label -1)

**Keuntungan DBSCAN:**
- ✅ Tidak perlu tentukan jumlah cluster di awal
- ✅ Bisa deteksi outlier/noise
- ✅ Bagus untuk cluster berbentuk arbitrary
- ✅ Cocok untuk data geografis/lokasi

**Disadvantage:**
- ❌ Sensitif terhadap parameter epsilon
- ❌ Lambat untuk dataset besar (O(n²))

### Haversine Distance

**Formula:**
```
a = sin²(Δφ/2) + cos(φ1) × cos(φ2) × sin²(Δλ/2)
c = 2 × atan2(√a, √(1−a))
d = R × c

Dimana:
φ = latitude (radian)
λ = longitude (radian)
R = radius bumi (6371 km)
d = jarak (km)
```

**Kenapa Haversine?**
- Menghitung jarak di permukaan bola (lebih akurat)
- Euclidean hanya untuk bidang datar

### Confidence Score

```
Confidence = (Frekuensi cluster yang diprediksi) / (Total data di jam itu)

Contoh:
- Ada 5 data di (Senin, 11:00)
- Cluster 0 muncul 4x, Cluster 1 muncul 1x
- Confidence = 4/5 = 0.80 (80%)

Interpretasi:
- 0.80-1.00 = Very confident
- 0.60-0.80 = Confident
- 0.40-0.60 = Moderately confident
- < 0.40  = Low confidence
```

## Complexity Analysis

### Time Complexity
- **Clustering:** O(n²) untuk DBSCAN (n = jumlah data)
- **Expand data:** O(n × h) untuk n data dan max h jam
- **Prediksi:** O(n) untuk hitung rata-rata

**Total:** O(n²) karena DBSCAN dominates

### Space Complexity
- **Labels:** O(n)
- **Mapping:** O(7 × 24) = O(168) untuk seminggu × 24 jam
- **Total:** O(n)

## Testing Checklist

```
□ Install requirements.txt
□ Jalankan python main.py
□ Test /health endpoint
□ Test /predict dengan example_request.json
□ Ubah target_time dan test lagi
□ Ubah epsilon_meter dan lihat perbedaannya
□ Test dengan data minimal (2-3 checkin)
□ Test dengan error case (tidak ada data di jam X)
```

---

**Last Updated:** 2026-04-28
