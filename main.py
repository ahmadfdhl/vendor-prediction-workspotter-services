# ============================================================
# WORKSPOTTER - Microservice Prediksi Lokasi Pedagang
# ============================================================
# Aplikasi FastAPI untuk memprediksi lokasi pedagang berdasarkan
# riwayat checkin menggunakan clustering sederhana (DBSCAN)
# ============================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Tuple
import math
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN

# ============================================================
# 1. SETUP FASTAPI
# ============================================================
app = FastAPI(
    title="WorkSpotter Service",
    description="Microservice untuk prediksi lokasi pedagang keliling",
    version="1.0.0"
)

# ============================================================
# 2. PYDANTIC MODELS (untuk validasi data input/output)
# ============================================================

class CheckinData(BaseModel):
    """Model untuk satu data checkin dari vendor"""
    vendor_id: int = Field(..., description="ID vendor/pedagang")
    checkin_time: str = Field(..., description="Waktu checkin (format: YYYY-MM-DD HH:MM:SS)")
    checkout_time: str = Field(..., description="Waktu checkout (format: YYYY-MM-DD HH:MM:SS)")
    latitude: float = Field(..., description="Latitude lokasi")
    longitude: float = Field(..., description="Longitude lokasi")


class PredictRequest(BaseModel):
    """Model untuk request ke endpoint /predict"""
    data: List[CheckinData] = Field(..., description="Array data checkin dari vendor")
    target_time: str = Field(..., description="Waktu target untuk prediksi (format: YYYY-MM-DD HH:MM:SS)")


class PredictResponse(BaseModel):
    """Model untuk response dari endpoint /predict"""
    predicted_latitude: float = Field(..., description="Latitude hasil prediksi")
    predicted_longitude: float = Field(..., description="Longitude hasil prediksi")
    cluster_id: int = Field(..., description="ID cluster lokasi yang diprediksi")
    confidence: float = Field(..., description="Nilai keyakinan prediksi (0-1)")


# ============================================================
# 3. FUNGSI HELPER - KONVERSI KOORDINAT KE RADIAN
# ============================================================

def koordinat_ke_radian(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Mengkonversi koordinat degree ke radian.

    Alasan: DBSCAN dengan metrik Haversine memerlukan input dalam radian
    untuk menghitung jarak bumi yang akurat.

    Args:
        latitude: Koordinat lintang (degree)
        longitude: Koordinat bujur (degree)

    Returns:
        Tuple berisi (latitude_radian, longitude_radian)
    """
    lat_radian = math.radians(latitude)
    lon_radian = math.radians(longitude)
    return lat_radian, lon_radian


# ============================================================
# 4. FUNGSI CLUSTERING - DBSCAN DENGAN HAVERSINE
# ============================================================

def clustering_lokasi(
    latitudes: List[float],
    longitudes: List[float],
    epsilon_meter: float = 100,
    min_samples: int = 1
) -> Dict[str, any]:
    """
    Melakukan clustering pada lokasi-lokasi menggunakan DBSCAN
    dengan metrik Haversine (jarak berdasarkan bola bumi).

    Penjelasan DBSCAN:
    - epsilon: radius jarak maksimal dalam radian
    - min_samples: jumlah minimum point dalam cluster
    - Haversine: metrik untuk menghitung jarak di permukaan bumi

    Args:
        latitudes: List latitude dari semua checkin
        longitudes: List longitude dari semua checkin
        epsilon_meter: radius dalam meter (akan dikonversi ke radian)
        min_samples: minimum samples dalam satu cluster

    Returns:
        Dict berisi:
        - 'labels': array cluster_id untuk setiap point
        - 'n_clusters': jumlah cluster yang terbentuk
        - 'original_coords': list (lat, lon) original
    """

    # Konversi jarak dari meter ke radian
    # Formula: radian = jarak_meter / radius_bumi_meter
    RADIUS_BUMI = 6371000  # meter
    epsilon_radian = epsilon_meter / RADIUS_BUMI

    # Konversi semua koordinat ke radian
    coords_radian = []
    for lat, lon in zip(latitudes, longitudes):
        lat_rad, lon_rad = koordinat_ke_radian(lat, lon)
        coords_radian.append([lat_rad, lon_rad])

    # Ubah ke numpy array
    coords_radian = np.array(coords_radian)

    # Jalankan DBSCAN dengan metrik Haversine
    dbscan = DBSCAN(
        eps=epsilon_radian,
        min_samples=min_samples,
        metric='haversine'  # Metrik jarak untuk bola bumi
    )

    # Fit dan prediksi
    labels = dbscan.fit_predict(coords_radian)

    # Hitung jumlah cluster (label -1 adalah noise/outlier)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    return {
        'labels': labels,
        'n_clusters': n_clusters,
        'original_coords': list(zip(latitudes, longitudes))
    }


# ============================================================
# 5. FUNGSI EXPAND DATA - DARI INTERVAL KE PER JAM
# ============================================================

def expand_data_per_jam(checkin_list: List[CheckinData]) -> Dict[str, List[int]]:
    """
    Mengubah data checkin (dengan interval waktu) menjadi data per jam.

    Contoh:
    - Checkin jam 10:00 - 12:00 di cluster 0
    - Akan menjadi: jam 10 → cluster 0, jam 11 → cluster 0

    Args:
        checkin_list: List objek CheckinData dengan waktu interval

    Returns:
        Dict dengan key (day_of_week, hour) dan value list cluster_id
        Contoh: {(0, 10): [0, 0, 1], (0, 11): [0, 1]}
    """

    # Mapping waktu ke cluster_id sudah dilakukan sebelumnya
    # Di sini kita hanya prepare struktur
    jam_cluster_mapping = defaultdict(list)

    for checkin in checkin_list:
        # Parse waktu checkin dan checkout
        checkin_dt = datetime.strptime(checkin.checkin_time, "%Y-%m-%d %H:%M:%S")
        checkout_dt = datetime.strptime(checkin.checkout_time, "%Y-%m-%d %H:%M:%S")

        # Ambil hari dalam seminggu (0=Senin, 6=Minggu)
        day_of_week = checkin_dt.weekday()

        # Loop setiap jam dari checkin sampai checkout
        current_hour = checkin_dt.hour
        end_hour = checkout_dt.hour

        # Jika checkout di jam yang sama, tetap masukkan
        if current_hour > end_hour:
            end_hour = current_hour

        for jam in range(current_hour, end_hour):
            # Key adalah (hari, jam)
            key = (day_of_week, jam)
            # Value adalah list cluster_id (akan diisi kemudian)
            # Di sini kita hanya tandai bahwa jam ini ada data
            jam_cluster_mapping[key]

    return jam_cluster_mapping


# ============================================================
# 6. FUNGSI TRAINING - MEMBANGUN MODEL DARI DATA CHECKIN
# ============================================================

def training_model(checkin_list: List[CheckinData], epsilon_meter: float = 100) -> Dict[str, any]:
    """
    Melatih model untuk prediksi lokasi.

    Langkah-langkah:
    1. Extract semua latitude dan longitude
    2. Lakukan clustering DBSCAN
    3. Expand data dari interval ke per jam
    4. Buat mapping (day_of_week, hour) → cluster_id paling sering

    Args:
        checkin_list: List objek CheckinData
        epsilon_meter: radius clustering dalam meter

    Returns:
        Dict berisi:
        - 'clustering_result': hasil clustering
        - 'jam_cluster_mapping': mapping waktu ke cluster
        - 'jam_cluster_counts': jumlah kemunculan setiap cluster per jam
    """

    # ========== STEP 1: Extract koordinat ==========
    latitudes = [c.latitude for c in checkin_list]
    longitudes = [c.longitude for c in checkin_list]

    # ========== STEP 2: Clustering DBSCAN ==========
    clustering_result = clustering_lokasi(
        latitudes=latitudes,
        longitudes=longitudes,
        epsilon_meter=epsilon_meter,
        min_samples=1
    )

    labels = clustering_result['labels']

    # ========== STEP 3: Buat mapping jam → list cluster_id ==========
    jam_cluster_mapping = defaultdict(list)

    for idx, checkin in enumerate(checkin_list):
        cluster_id = int(labels[idx])  # cluster_id dari DBSCAN

        # Parse waktu
        checkin_dt = datetime.strptime(checkin.checkin_time, "%Y-%m-%d %H:%M:%S")
        checkout_dt = datetime.strptime(checkin.checkout_time, "%Y-%m-%d %H:%M:%S")

        # Hari dalam seminggu
        day_of_week = checkin_dt.weekday()

        # Loop setiap jam
        current_hour = checkin_dt.hour
        end_hour = checkout_dt.hour

        if current_hour > end_hour:
            end_hour = current_hour

        # Tambahkan cluster_id ke setiap jam
        for jam in range(current_hour, end_hour):
            key = (day_of_week, jam)
            jam_cluster_mapping[key].append(cluster_id)

    # ========== STEP 4: Hitung frekuensi cluster per jam ==========
    jam_cluster_counts = {}

    for key, cluster_list in jam_cluster_mapping.items():
        # Hitung frekuensi setiap cluster di jam tersebut
        freq_dict = defaultdict(int)

        for cluster_id in cluster_list:
            freq_dict[cluster_id] += 1

        # Simpan frekuensi
        jam_cluster_counts[key] = dict(freq_dict)

    return {
        'clustering_result': clustering_result,
        'jam_cluster_mapping': dict(jam_cluster_mapping),
        'jam_cluster_counts': jam_cluster_counts
    }


# ============================================================
# 7. FUNGSI PREDIKSI
# ============================================================

def prediksi_lokasi(
    target_time: str,
    model: Dict[str, any],
    checkin_list: List[CheckinData]
) -> PredictResponse:
    """
    Memprediksi lokasi vendor pada waktu tertentu.

    Logika:
    1. Ekstrak hari dan jam dari target_time
    2. Cari cluster yang paling sering muncul di waktu tersebut
    3. Hitung rata-rata latitude & longitude dari cluster
    4. Hitung confidence = frekuensi cluster / total data di jam itu

    Args:
        target_time: Waktu target prediksi (format: YYYY-MM-DD HH:MM:SS)
        model: Hasil dari training_model()
        checkin_list: List data checkin original (untuk ambil koordinat cluster)

    Returns:
        PredictResponse dengan latitude, longitude, cluster_id, dan confidence

    Raises:
        HTTPException: Jika tidak ada data untuk jam tersebut
    """

    # Parse target_time
    target_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
    day_of_week = target_dt.weekday()
    hour = target_dt.hour

    key = (day_of_week, hour)

    # ========== STEP 1: Cek apakah ada data untuk jam ini ==========
    jam_cluster_counts = model['jam_cluster_counts']

    if key not in jam_cluster_counts:
        raise HTTPException(
            status_code=400,
            detail=f"Tidak ada data untuk hari {day_of_week} jam {hour:02d}"
        )

    cluster_freqs = jam_cluster_counts[key]

    # ========== STEP 2: Cari cluster dengan frekuensi tertinggi ==========
    most_common_cluster = max(cluster_freqs.items(), key=lambda x: x[1])
    predicted_cluster_id = most_common_cluster[0]
    cluster_frequency = most_common_cluster[1]

    # ========== STEP 3: Hitung rata-rata koordinat dari cluster ==========
    clustering_result = model['clustering_result']
    labels = clustering_result['labels']
    original_coords = clustering_result['original_coords']

    # Kumpulkan semua koordinat yang termasuk cluster yang diprediksi
    cluster_lats = []
    cluster_lons = []

    for idx, cluster_id in enumerate(labels):
        if int(cluster_id) == predicted_cluster_id:
            lat, lon = original_coords[idx]
            cluster_lats.append(lat)
            cluster_lons.append(lon)

    # Hitung rata-rata
    avg_lat = sum(cluster_lats) / len(cluster_lats)
    avg_lon = sum(cluster_lons) / len(cluster_lons)

    # ========== STEP 4: Hitung confidence ==========
    total_data_in_hour = sum(cluster_freqs.values())
    confidence = cluster_frequency / total_data_in_hour

    return PredictResponse(
        predicted_latitude=round(avg_lat, 6),
        predicted_longitude=round(avg_lon, 6),
        cluster_id=predicted_cluster_id,
        confidence=round(confidence, 2)
    )


# ============================================================
# 8. ENDPOINT - POST /predict
# ============================================================

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Endpoint untuk memprediksi lokasi vendor pada waktu tertentu.

    Cara kerja:
    1. Terima data checkin dan target_time
    2. Lakukan training (clustering + mapping jam → cluster)
    3. Prediksi lokasi berdasarkan hari & jam target_time
    4. Kembalikan latitude, longitude, cluster_id, dan confidence

    Request body:
    {
        "data": [
            {
                "vendor_id": 1,
                "checkin_time": "2026-04-20 10:00:00",
                "checkout_time": "2026-04-20 12:00:00",
                "latitude": -6.200000,
                "longitude": 106.816666
            }
        ],
        "target_time": "2026-04-20 11:00:00"
    }

    Response:
    {
        "predicted_latitude": -6.20001,
        "predicted_longitude": 106.81665,
        "cluster_id": 0,
        "confidence": 0.82
    }
    """

    # Validasi input
    if not request.data:
        raise HTTPException(status_code=400, detail="Data checkin tidak boleh kosong")

    try:
        # Training model
        model = training_model(request.data, epsilon_meter=100)

        # Prediksi
        result = prediksi_lokasi(request.target_time, model, request.data)

        return result

    except HTTPException:
        # Re-raise HTTPException tanpa di-wrap
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Format data tidak valid: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error prediksi: {str(e)}")


# ============================================================
# 9. ENDPOINT HEALTH CHECK (opsional)
# ============================================================

@app.get("/health")
async def health_check():
    """Endpoint untuk cek apakah service aktif"""
    return {
        "status": "healthy",
        "service": "WorkSpotter Prediction Service",
        "version": "1.0.0"
    }


# ============================================================
# 10. ROOT ENDPOINT (opsional)
# ============================================================

@app.get("/")
async def root():
    """Root endpoint dengan informasi API"""
    return {
        "nama": "WorkSpotter Service",
        "deskripsi": "Microservice untuk prediksi lokasi pedagang keliling",
        "endpoints": {
            "health": "GET /health",
            "predict": "POST /predict",
            "docs": "GET /docs"
        }
    }


# ============================================================
# 11. JALANKAN SERVER (jika file dijalankan langsung)
# ============================================================

if __name__ == "__main__":
    import uvicorn

    # Jalankan server di localhost:8000
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload saat kode berubah (development)
    )
