from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import math
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN

app = FastAPI(
    title="WorkSpotter Service (Improved)",
    description="Microservice untuk prediksi lokasi pedagang keliling - versi improved",
    version="2.0.0"
)

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
    """Model untuk response dari endpoint /predict - IMPROVED VERSION"""
    predicted_latitude: float = Field(..., description="Latitude hasil prediksi")
    predicted_longitude: float = Field(..., description="Longitude hasil prediksi")
    cluster_id: int = Field(..., description="ID cluster lokasi yang diprediksi")
    confidence: float = Field(..., description="Nilai keyakinan prediksi (0-1)")

    # NEW: Fallback information
    fallback: bool = Field(..., description="Apakah menggunakan fallback (jam/hari berubah)")
    used_hour: int = Field(..., description="Jam yang sebenarnya dipakai untuk prediksi")
    notes: Optional[str] = Field(None, description="Catatan tambahan tentang prediksi")


def koordinat_ke_radian(latitude: float, longitude: float) -> Tuple[float, float]:
    lat_radian = math.radians(latitude)
    lon_radian = math.radians(longitude)
    return lat_radian, lon_radian

def clustering_lokasi(
    latitudes: List[float],
    longitudes: List[float],
    epsilon_meter: float = 100,
    min_samples: int = 1
) -> Dict[str, any]:

    # Konversi jarak dari meter ke radian
    RADIUS_BUMI = 6371000  # meter
    epsilon_radian = epsilon_meter / RADIUS_BUMI

    # Konversi semua koordinat ke radian
    coords_radian = []
    for lat, lon in zip(latitudes, longitudes):
        lat_rad, lon_rad = koordinat_ke_radian(lat, lon)
        coords_radian.append([lat_rad, lon_rad])

    coords_radian = np.array(coords_radian)

    # Jalankan DBSCAN
    dbscan = DBSCAN(
        eps=epsilon_radian,
        min_samples=min_samples,
        metric='haversine'
    )

    labels = dbscan.fit_predict(coords_radian)

    # Hitung jumlah cluster (exclude label -1 untuk noise)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    return {
        'labels': labels,
        'n_clusters': n_clusters,
        'original_coords': list(zip(latitudes, longitudes))
    }


def get_nearest_hour(
    day_of_week: int,
    hour: int,
    jam_cluster_counts: Dict[Tuple[int, int], Dict[int, int]],
    search_range: int = 3
) -> Optional[Tuple[int, int]]:
    key = (day_of_week, hour)
    if key in jam_cluster_counts:
        return key

    # Cari dalam range
    for offset in range(1, search_range + 1):
        # Cek jam setelah (hour + offset)
        if hour + offset < 24:
            key = (day_of_week, hour + offset)
            if key in jam_cluster_counts:
                return key

        # Cek jam sebelum (hour - offset)
        if hour - offset >= 0:
            key = (day_of_week, hour - offset)
            if key in jam_cluster_counts:
                return key
            
    # Cari jam yang sama di hari lain (prioritas: jam terdekat dulu)
    for offset in range(0, search_range + 1):
        # Cek semua hari untuk jam + offset
        if hour + offset < 24:
            for day in range(7):  # 0-6 untuk semua hari
                key = (day, hour + offset)
                if key in jam_cluster_counts:
                    return key

        # Cek semua hari untuk jam - offset
        if hour - offset >= 0:
            for day in range(7):
                key = (day, hour - offset)
                if key in jam_cluster_counts:
                    return key

    # Jika benar-benar tidak ada data apapun
    return None


def get_time_window_data(
    day_of_week: int,
    hour: int,
    jam_cluster_counts: Dict[Tuple[int, int], Dict[int, int]],
    window_size: int = 1
) -> Dict[int, int]:

    combined_freqs = defaultdict(int)

    # Loop setiap jam dalam window
    for offset in range(-window_size, window_size + 1):
        current_hour = hour + offset

        # Skip jika di luar range (0-23)
        if current_hour < 0 or current_hour >= 24:
            continue

        key = (day_of_week, current_hour)

        # Jika ada data untuk jam ini
        if key in jam_cluster_counts:
            cluster_freqs = jam_cluster_counts[key]

            # Tambahkan frekuensi dari setiap cluster
            for cluster_id, freq in cluster_freqs.items():
                # IMPORTANT: Abaikan cluster -1 (noise/outlier)
                if cluster_id != -1:
                    combined_freqs[cluster_id] += freq

    return dict(combined_freqs)


def apply_laplace_smoothing(
    predicted_cluster_freq: int,
    total_data: int,
    n_clusters: int,
    smoothing_factor: float = 1.0
) -> float:
    # Jika n_clusters = 0, return 0
    if n_clusters == 0:
        return 0.0

    confidence = (predicted_cluster_freq + smoothing_factor) / (total_data + smoothing_factor * n_clusters)

    # Ensure dalam range 0-1
    return min(1.0, max(0.0, confidence))


# ============================================================
# 6. TRAINING MODEL
# ============================================================

def training_model(checkin_list: List[CheckinData], epsilon_meter: float = 100) -> Dict[str, any]:
    latitudes = [c.latitude for c in checkin_list]
    longitudes = [c.longitude for c in checkin_list]

    clustering_result = clustering_lokasi(
        latitudes=latitudes,
        longitudes=longitudes,
        epsilon_meter=epsilon_meter,
        min_samples=1
    )

    labels = clustering_result['labels']
    
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

    jam_cluster_counts = {}

    for key, cluster_list in jam_cluster_mapping.items():
        freq_dict = defaultdict(int)

        for cluster_id in cluster_list:
            freq_dict[cluster_id] += 1

        jam_cluster_counts[key] = dict(freq_dict)

    return {
        'clustering_result': clustering_result,
        'jam_cluster_mapping': dict(jam_cluster_mapping),
        'jam_cluster_counts': jam_cluster_counts
    }


def prediksi_lokasi(
    target_time: str,
    model: Dict[str, any],
    checkin_list: List[CheckinData],
    window_size: int = 1,
    smoothing_factor: float = 1.0
) -> PredictResponse:
    
    # Parse target_time
    target_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
    day_of_week = target_dt.weekday()
    hour = target_dt.hour

    jam_cluster_counts = model['jam_cluster_counts']
    clustering_result = model['clustering_result']
    labels = clustering_result['labels']
    original_coords = clustering_result['original_coords']
    n_clusters = clustering_result['n_clusters']

    # ========== STEP 1: Coba ambil data dari time window ==========
    cluster_freqs = get_time_window_data(
        day_of_week=day_of_week,
        hour=hour,
        jam_cluster_counts=jam_cluster_counts,
        window_size=window_size
    )

    used_hour = hour
    fallback_used = False
    if not cluster_freqs:
        # Cari jam terdekat yang ada data
        nearest_key = get_nearest_hour(day_of_week, hour, jam_cluster_counts)

        if nearest_key is None:
            raise HTTPException(
                status_code=400,
                detail=f"Tidak ada data untuk prediksi (hari {day_of_week}, jam {hour:02d})"
            )

        # Gunakan data dari jam terdekat
        fallback_day, fallback_hour = nearest_key
        cluster_freqs = get_time_window_data(
            day_of_week=fallback_day,
            hour=fallback_hour,
            jam_cluster_counts=jam_cluster_counts,
            window_size=window_size
        )

        used_hour = fallback_hour
        fallback_used = True

    if cluster_freqs:
        # Jika ada cluster -1 dan ada cluster lain, abaikan -1
        if -1 in cluster_freqs and len(cluster_freqs) > 1:
            del cluster_freqs[-1]
    if not cluster_freqs:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada cluster yang valid untuk prediksi"
        )

    most_common_cluster = max(cluster_freqs.items(), key=lambda x: x[1])
    predicted_cluster_id = most_common_cluster[0]
    cluster_frequency = most_common_cluster[1]

    cluster_lats = []
    cluster_lons = []

    for idx, cluster_id in enumerate(labels):
        if int(cluster_id) == predicted_cluster_id:
            lat, lon = original_coords[idx]
            cluster_lats.append(lat)
            cluster_lons.append(lon)

    if not cluster_lats:
        raise HTTPException(
            status_code=500,
            detail="Error: Tidak dapat menemukan koordinat untuk cluster yang diprediksi"
        )

    avg_lat = sum(cluster_lats) / len(cluster_lats)
    avg_lon = sum(cluster_lons) / len(cluster_lons)

    total_data = sum(cluster_freqs.values())

    confidence = apply_laplace_smoothing(
        predicted_cluster_freq=cluster_frequency,
        total_data=total_data,
        n_clusters=n_clusters,
        smoothing_factor=smoothing_factor
    )

    notes = None
    if fallback_used:
        notes = f"Menggunakan fallback: jam {used_hour:02d} (permintaan jam {hour:02d})"

    return PredictResponse(
        predicted_latitude=round(avg_lat, 6),
        predicted_longitude=round(avg_lon, 6),
        cluster_id=predicted_cluster_id,
        confidence=round(confidence, 2),
        fallback=fallback_used,
        used_hour=used_hour,
        notes=notes
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    if not request.data:
        raise HTTPException(status_code=400, detail="Data checkin tidak boleh kosong")

    try:
        # Training model
        model = training_model(request.data, epsilon_meter=100)

        # Prediksi dengan improved logic
        result = prediksi_lokasi(
            target_time=request.target_time,
            model=model,
            checkin_list=request.data,
            window_size=1,  # Time window: jam-1 sampai jam+1
            smoothing_factor=1.0  # Laplace smoothing factor
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Format data tidak valid: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error prediksi: {str(e)}")



@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "WorkSpotter Prediction Service (Improved)",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    return {
        "nama": "WorkSpotter Service (Improved)",
        "deskripsi": "Microservice untuk prediksi lokasi pedagang keliling - versi improved dengan fallback & smoothing",
        "version": "2.0.0",
        "endpoints": {
            "health": "GET /health",
            "predict": "POST /predict",
            "docs": "GET /docs"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )
