# WorkSpotter Service - Navigation Guide

Setelah testing lengkap dan semua test PASSED, berikut adalah panduan untuk navigasi project:

---

## 📂 File Organization

### Buat dimulai dari sini
1. **QUICK_START.md** - Baca ini terlebih dahulu untuk setup cepat (5 menit)
2. **README.md** - Dokumentasi lengkap mengenai service dan cara penggunaan

### Pelajari cara kerjanya
3. **ARCHITECTURE.md** - Penjelasan mendalam tentang:
   - Alur data dari input ke output
   - Cara kerja DBSCAN clustering
   - Haversine distance calculation
   - Time-based pattern mapping

### Implementasi
4. **main.py** - Source code production (baca dengan teliti):
   - Pydantic models
   - Helper functions
   - Core algorithm functions
   - FastAPI endpoints
   - Error handling

### Testing & Quality
5. **test_service.py** - Test suite untuk memahami:
   - Cara test API
   - Test cases yang dijalankan
   - Expected behavior

6. **TESTING_REPORT.md** - Hasil lengkap testing:
   - Test configuration
   - Detailed results per test
   - Performance metrics
   - Bug fixes

### Referensi
7. **example_request.json** - Contoh request untuk dipakai
8. **requirements.txt** - Dependencies yang diperlukan
9. **PROJECT_SUMMARY.md** - Ringkasan project completion

---

## 🚀 Quick Start (5 menit)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start server
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Test API (di terminal lain)
python test_service.py

# 4. Atau buka browser
http://localhost:8000/docs
```

---

## 📖 Reading Order

### Untuk Pemula (Belajar dari nol)
1. QUICK_START.md (5 menit)
2. README.md - Bagian "Cara Kerja" (10 menit)
3. ARCHITECTURE.md - Bagian "Arsitektur Keseluruhan" (10 menit)
4. main.py - Baca dengan fokus ke comments (30 menit)
5. test_service.py - Pahami test cases (15 menit)

**Total: ~1 jam untuk pemahaman menyeluruh**

### Untuk yang Sudah Familiar
1. main.py - Review implementation
2. ARCHITECTURE.md - Deep dive ke algoritma
3. TESTING_REPORT.md - Check test coverage

---

## 🎓 Learning Path

### Minggu 1: Fondasi
- [ ] Setup environment (install dependencies)
- [ ] Run QUICK_START.md
- [ ] Baca README.md sections
- [ ] Test API dengan example_request.json

### Minggu 2: Implementasi
- [ ] Baca main.py dengan teliti
- [ ] Pahami setiap fungsi
- [ ] Trace code execution dari request sampai response
- [ ] Understand error handling

### Minggu 3: Testing & Debugging
- [ ] Run test_service.py
- [ ] Pahami test cases
- [ ] Coba modify test cases
- [ ] Understand confidence scoring

### Minggu 4: Advanced
- [ ] Modify clustering parameters
- [ ] Add logging/monitoring
- [ ] Plan untuk improvements
- [ ] Prepare untuk production deployment

---

## 💡 Key Concepts to Understand

### 1. DBSCAN Clustering
Lokasi file: `main.py` - fungsi `clustering_lokasi()`

Apa itu:
- Algoritma clustering yang mengelompokkan point berdasarkan jarak
- Tidak perlu tentukan jumlah cluster di awal
- Bisa detect outlier

Kenapa dipilih:
- Cocok untuk data geografis
- Fleksibel dengan berbagai bentuk cluster
- Tidak perlu parameter yang kompleks

Tugas:
- Grouping semua checkin locations menjadi clusters
- Contoh: 3 checkin di area Blok M → Cluster 0

### 2. Haversine Distance
Lokasi file: `main.py` - fungsi `koordinat_ke_radian()` dan DBSCAN metric

Apa itu:
- Formula untuk menghitung jarak di permukaan bola bumi
- Lebih akurat daripada garis lurus

Kenapa dipilih:
- Koordinat GPS adalah latitude/longitude
- Perlu memperhitungkan lengkung bumi
- Haversine formula paling akurat untuk jarak GPS

Contoh:
- Titik A: (-6.200, 106.816)
- Titik B: (-6.201, 106.817)
- Jarak sebenarnya: ~111 meter (bukan 0.0015 seperti Euclidean)

### 3. Time-Based Pattern Mapping
Lokasi file: `main.py` - fungsi `training_model()`

Apa itu:
- Mapping dari (hari_minggu, jam) ke cluster yang paling sering

Contoh:
- (Senin, 10:00) → Cluster 0 (Blok M) ✓ 5x kemunculan
- (Senin, 14:00) → Cluster 1 (Senayan) ✓ 5x kemunculan
- (Senin, 18:00) → Cluster 2 (Setiabudi) ✓ 5x kemunculan

Gunanya:
- Predict lokasi berdasarkan pola waktu
- Confidence = frekuensi / total data di jam itu

### 4. Confidence Score
Lokasi file: `main.py` - fungsi `prediksi_lokasi()`

Rumus:
```
Confidence = Jumlah kemunculan cluster / Total data di jam itu
```

Contoh:
- Jam 10:00: 5 data semua di Cluster 0 → Confidence = 5/5 = 1.0 (100%)
- Jam 14:00: 3 data di Cluster 1, 2 data di Cluster 0 → Confidence = 3/5 = 0.6 (60%)

Interpretasi:
- 0.8-1.0 = Very confident (yakin sekali)
- 0.6-0.8 = Confident (yakin)
- 0.4-0.6 = Moderate (agak yakin)
- < 0.4 = Low (tidak yakin)

---

## 🔍 Code Navigation

### Understanding the Flow

**Request masuk:**
```
POST /predict
   ↓
Validation (Pydantic)
   ↓
training_model()
   ├─ clustering_lokasi() → DBSCAN
   ├─ expand_data_per_jam() → per-hour expansion
   └─ Create mapping (day, hour) → cluster
   ↓
prediksi_lokasi()
   ├─ Parse target_time
   ├─ Find cluster paling sering
   ├─ Hitung average coordinates
   └─ Calculate confidence
   ↓
Response (PredictResponse)
```

### Finding Things in Code

Mau cari:
- **DBSCAN clustering?** → Lihat fungsi `clustering_lokasi()` di main.py line ~150
- **Haversine distance?** → Lihat parameter `metric='haversine'` di line ~170
- **Time expansion?** → Lihat fungsi `expand_data_per_jam()` di line ~200
- **Prediction logic?** → Lihat fungsi `prediksi_lokasi()` di line ~300
- **Endpoint definition?** → Lihat `@app.post("/predict")` di line ~400

---

## 🧪 Testing Guide

### Run Tests
```bash
python test_service.py
```

### Understand Tests
- Test 1-5: Prediction tests untuk berbagai jam
- Test 6-7: Error handling tests
- Test 8: Health check

### Expected Results
```
[PASS]: Test 1: Selasa 11:00 - Confidence: 1.0
[PASS]: Test 2: Selasa 14:00 - Confidence: 1.0
[PASS]: Test 3: Selasa 18:00 - Confidence: 1.0
[PASS]: Test 4: Rabu 10:30 - Confidence: 1.0
[PASS]: Test 5: Senin 15:00 - Confidence: 1.0
Total: 5/5 prediction tests passed
```

### Modify Tests
```python
# Tambah test case baru di test_service.py
test_cases = [
    # Format: (data, target_time, test_name)
    (data, "2026-04-07 11:00:00", "Test 1: Selasa 11:00"),
    # Tambahkan di sini
    (data, "YOUR_DATE TIME", "Your test name"),
]
```

---

## 🐛 Debugging Tips

### Service tidak responding?
1. Check port 8000 not in use: `netstat -an | grep 8000`
2. Check server log: `cat server.log`
3. Restart server: `pkill -f uvicorn`

### Test failed?
1. Check error message dari server
2. Verify data format di request
3. Check timestamp format (harus "YYYY-MM-DD HH:MM:SS")
4. Ensure server running: `curl http://localhost:8000/health`

### Wrong prediction?
1. Check clustering result (cluster_id correct?)
2. Verify confidence score (should be high if good data)
3. Check test data (realistic locations?)
4. Modify epsilon_meter jika perlu

---

## 📚 Further Learning

### Topik untuk dipelajari lebih lanjut
1. **DBSCAN parameter tuning**
   - Coba different epsilon values
   - See how it affects clustering

2. **Haversine formula derivation**
   - Understand the math behind
   - Learn spherical trigonometry

3. **Time series analysis**
   - Analyze patterns over time
   - Add seasonal adjustments

4. **API optimization**
   - Add caching layer
   - Implement async operations
   - Use database for persistence

### Resources
- scikit-learn docs: https://scikit-learn.org/stable/modules/clustering.html#dbscan
- FastAPI docs: https://fastapi.tiangolo.com/
- Haversine formula: https://en.wikipedia.org/wiki/Haversine_formula

---

## ✅ Checklist untuk Pemahaman Lengkap

- [ ] Sudah run QUICK_START dan berhasil
- [ ] Sudah membaca README.md sampai selesai
- [ ] Sudah membaca ARCHITECTURE.md sampai selesai
- [ ] Sudah membaca main.py dan understand setiap function
- [ ] Sudah run test_service.py dan semua test PASSED
- [ ] Sudah modify test case dan run ulang
- [ ] Sudah coba endpoint via curl atau Swagger UI
- [ ] Sudah understand confidence score
- [ ] Sudah understand DBSCAN clustering
- [ ] Sudah understand Haversine distance
- [ ] Sudah understand time-based pattern mapping
- [ ] Siap untuk production deployment

---

## 🎓 Kesimpulan

Setelah membaca dan memahami semua file di project ini, Anda akan:

1. **Mengerti cara kerja DBSCAN clustering** untuk data geografis
2. **Memahami Haversine distance** untuk GPS coordinates
3. **Bisa membuat REST API** dengan FastAPI
4. **Bisa melakukan data validation** dengan Pydantic
5. **Bisa membuat test suite** untuk API testing
6. **Mengerti confidence scoring** untuk ML predictions
7. **Siap untuk production deployment** dan monitoring

Semua ini adalah skill yang valuable di industri dan akan membantu Anda di karir software engineering!

---

**Happy Learning!** 🎓

Jika ada pertanyaan, baca kembali file yang relevan dengan fokus ke comments dan explanations.
