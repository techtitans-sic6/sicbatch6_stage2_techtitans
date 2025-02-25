from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)  # Mengizinkan akses dari sumber lain (CORS)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)

# Konfigurasi MongoDB Atlas (Pastikan kredensial benar)
MONGO_URI = "mongodb+srv://techtitans:*techtitans!@cluster-techtitans.t8jps.mongodb.net/?retryWrites=true&w=majority&appName=cluster-techtitans"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # Timeout 5 detik
    db = client["edunudgeai_techtitans"]
    collection = db["sensor_data"]
    client.server_info()  # Cek apakah MongoDB bisa diakses
    logging.info("Koneksi ke MongoDB Atlas berhasil!")
except Exception as e:
    logging.error(f"Gagal terhubung ke MongoDB Atlas: {e}")
    client = None  # Matikan koneksi jika gagal

# Endpoint untuk menyimpan data dari ESP32
@app.route('/save', methods=['POST'])
def save_data():
    if not client:
        return jsonify({"error": "Koneksi ke MongoDB gagal"}), 500

    try:
        data = request.json  # Ambil data dari ESP32
        if not data:
            return jsonify({"error": "Data tidak boleh kosong"}), 400

        collection.insert_one(data)  # Simpan ke MongoDB
        logging.info(f"Data diterima: {data}")
        return jsonify({"message": "Data berhasil disimpan"}), 200
    except Exception as e:
        logging.error(f"Error saat menyimpan data: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint untuk mendapatkan data dari MongoDB
@app.route('/data', methods=['GET'])
def get_data():
    if not client:
        return jsonify({"error": "Koneksi ke MongoDB gagal"}), 500

    try:
        data = list(collection.find({}, {"_id": 0}))  # Ambil semua data tanpa field _id
        return jsonify(data), 200
    except Exception as e:
        logging.error(f"Error saat mengambil data: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
