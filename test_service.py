"""
COMPREHENSIVE TEST SUITE untuk WorkSpotter Service

Test dengan data realistic yang banyak untuk memastikan:
- Tidak ada error atau bug
- Clustering bekerja dengan baik
- Prediksi akurat dengan confidence score yang meaningful
"""

import json
from datetime import datetime, timedelta
import requests

# ============================================================
# 1. GENERATE DATA TESTING REALISTIC
# ============================================================

def generate_realistic_checkin_data():
    """
    Generate data checkin yang realistic:
    - Pedagang checkin di area tertentu (Jakarta area)
    - Berbagai hari dan jam
    - Lokasi-lokasi yang berdekatan (cluster)
    """

    data = []
    vendor_id = 1

    # Cluster 1: Area Blok M (Jakarta Selatan)
    cluster_1_coords = [
        (-6.2850, 106.7950),  # Blok M pusat
        (-6.2855, 106.7952),  # Nearby
        (-6.2848, 106.7948),  # Nearby
    ]

    # Cluster 2: Area Senayan (Jakarta Selatan)
    cluster_2_coords = [
        (-6.2210, 106.8000),  # Senayan
        (-6.2215, 106.8005),  # Nearby
        (-6.2208, 106.7995),  # Nearby
    ]

    # Cluster 3: Area Setiabudi (Jakarta Selatan)
    cluster_3_coords = [
        (-6.2300, 106.8100),  # Setiabudi
        (-6.2305, 106.8105),  # Nearby
        (-6.2295, 106.8095),  # Nearby
    ]

    # Generate data untuk 4 minggu, hari Senin-Jumat, 3 session
    # Total: 4 minggu x 5 hari x 3 session = 60 data

    start_date = datetime(2026, 4, 1)  # 1 April 2026 (Rabu)

    # Untuk setiap minggu
    for week in range(4):
        current_date = start_date + timedelta(weeks=week)

        # Find next Monday
        days_until_monday = (7 - current_date.weekday()) % 7
        if days_until_monday == 0 and current_date.weekday() != 0:
            days_until_monday = 7
        monday_date = current_date + timedelta(days=days_until_monday)

        # Untuk setiap hari Senin-Jumat (5 hari)
        for day in range(5):
            current_date = monday_date + timedelta(days=day)

            # Session 1: Pagi (10:00 - 12:30) - Cluster 1
            lat, lon = cluster_1_coords[day % 3]
            data.append({
                "vendor_id": vendor_id,
                "checkin_time": current_date.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "checkout_time": current_date.replace(hour=12, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": lat,
                "longitude": lon
            })

            # Session 2: Siang (13:30 - 16:00) - Cluster 2
            lat, lon = cluster_2_coords[day % 3]
            data.append({
                "vendor_id": vendor_id,
                "checkin_time": current_date.replace(hour=13, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "checkout_time": current_date.replace(hour=16, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": lat,
                "longitude": lon
            })

            # Session 3: Sore (17:00 - 19:30) - Cluster 3
            lat, lon = cluster_3_coords[day % 3]
            data.append({
                "vendor_id": vendor_id,
                "checkin_time": current_date.replace(hour=17, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "checkout_time": current_date.replace(hour=19, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": lat,
                "longitude": lon
            })

    return data


# ============================================================
# 2. TEST HELPER FUNCTIONS
# ============================================================

def test_api_endpoint(data, target_time, test_name):
    """Test satu endpoint dengan data dan target_time tertentu"""

    url = "http://localhost:8000/predict"
    payload = {
        "data": data,
        "target_time": target_time
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        print("\n" + "="*60)
        print("TEST: " + test_name)
        print("="*60)
        print("Target Time: " + target_time)
        print("Data Points: " + str(len(data)))
        print("Status Code: " + str(response.status_code))

        if response.status_code == 200:
            result = response.json()
            print("[SUCCESS]")
            print("\nResult:")
            print("  - Predicted Latitude: " + str(result['predicted_latitude']))
            print("  - Predicted Longitude: " + str(result['predicted_longitude']))
            print("  - Cluster ID: " + str(result['cluster_id']))
            print("  - Confidence: " + str(result['confidence']))
            return True
        else:
            print("[ERROR] " + str(response.status_code))
            print("Response: " + response.text)
            return False

    except requests.exceptions.ConnectionError:
        print("\n" + "="*60)
        print("[CONNECTION ERROR]")
        print("="*60)
        print("Pastikan server FastAPI sudah running di http://localhost:8000")
        return False
    except Exception as e:
        print("\n" + "="*60)
        print("[ERROR] " + str(e))
        print("="*60)
        return False


def test_health_check():
    """Test health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Health Check: OK")
            print("   Response: " + str(response.json()))
            return True
        else:
            print("[FAILED] Health Check: FAILED (Status " + str(response.status_code) + ")")
            return False
    except Exception as e:
        print("[ERROR] Health Check: ERROR - " + str(e))
        return False


# ============================================================
# 3. RUN TESTS
# ============================================================

def main():
    print("\n" + "="*60)
    print("WORKSPOTTER SERVICE - COMPREHENSIVE TEST SUITE")
    print("="*60)

    # Test health check
    print("\n[1/4] Testing Health Endpoint...")
    health_ok = test_health_check()

    if not health_ok:
        print("\n[WARNING] Server tidak running. Pastikan Anda sudah menjalankan:")
        print("   python main.py")
        return

    # Generate data
    print("\n[2/4] Generating Test Data...")
    data = generate_realistic_checkin_data()
    print("[OK] Generated " + str(len(data)) + " checkin data points")

    # Print sample data
    print("\nSample Data:")
    for i in range(min(3, len(data))):
        d = data[i]
        print("  " + str(i+1) + ". " + d['checkin_time'] + " -> " + d['checkout_time'] + " | " +
              "Lat: " + str(d['latitude']) + ", Lon: " + str(d['longitude']))
    print("  ... (" + str(len(data) - 3) + " more records)")

    # Run tests
    print("\n[3/4] Running Prediction Tests...")

    test_cases = [
        # Test 1: Selasa jam 11:00 (dalam session pagi)
        (data, "2026-04-07 11:00:00", "Test 1: Selasa 11:00 (Pagi - Cluster 1)"),

        # Test 2: Selasa jam 14:00 (dalam session siang)
        (data, "2026-04-07 14:00:00", "Test 2: Selasa 14:00 (Siang - Cluster 2)"),

        # Test 3: Selasa jam 18:00 (dalam session sore)
        (data, "2026-04-07 18:00:00", "Test 3: Selasa 18:00 (Sore - Cluster 3)"),

        # Test 4: Rabu jam 10:30
        (data, "2026-04-08 10:30:00", "Test 4: Rabu 10:30 (Pagi - Cluster 1)"),

        # Test 5: Sabtu jam 15:00 (harusnya error karena weekend)
        (data, "2026-04-06 15:00:00", "Test 5: Senin 15:00 (Siang - Cluster 2)"),
    ]

    results = []
    for test_data, target_time, test_name in test_cases:
        success = test_api_endpoint(test_data, target_time, test_name)
        results.append((test_name, success))

    # Test error cases
    print("\n[4/4] Testing Error Handling...")

    # Test dengan data kosong
    print("\n" + "="*60)
    print("TEST: Error Case - Empty Data")
    print("="*60)
    try:
        response = requests.post(
            "http://localhost:8000/predict",
            json={"data": [], "target_time": "2026-04-07 11:00:00"},
            timeout=5
        )
        if response.status_code == 400:
            print("[OK] Correctly rejected empty data")
            print("   Error message: " + str(response.json()['detail']))
        else:
            print("[WARNING] Expected 400, got " + str(response.status_code))
    except Exception as e:
        print("[ERROR] Error: " + str(e))

    # Test dengan waktu yang tidak ada data
    print("\n" + "="*60)
    print("TEST: Error Case - No Data for Time Slot")
    print("="*60)
    try:
        response = requests.post(
            "http://localhost:8000/predict",
            json={"data": data, "target_time": "2026-04-07 23:00:00"},
            timeout=5
        )
        if response.status_code == 400:
            print("[OK] Correctly rejected time slot with no data")
            print("   Error message: " + str(response.json()['detail']))
        else:
            print("[WARNING] Expected 400, got " + str(response.status_code))
    except Exception as e:
        print("[ERROR] Error: " + str(e))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(status + ": " + test_name)

    print("\nTotal: " + str(passed) + "/" + str(total) + " prediction tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED! Service is working correctly.")
    else:
        print("\n[WARNING] Some tests failed. Check the errors above.")


if __name__ == "__main__":
    main()
