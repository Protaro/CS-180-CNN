from flask import Flask, request, jsonify
from flask_cors import CORS
import tf_keras as keras
from PIL import Image
import numpy as np
import tensorflow as tf
import io
import sqlite3
import hashlib

DB_PATH = "feedback.db"
app = Flask(__name__)
CORS(app)  # allows the Chrome extension to call this API

# Load model once at startup
print("Loading model...")
model = keras.models.load_model(
    "Veritas_Model_May03.h5"
)
print("Model ready!")

class Service:
    def __init__(self) -> None:
        self.initialize_db()
        pass
    
    def initialize_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image BLOB,
                image_hash TEXT UNIQUE,
                accurate INTEGER,
                label TEXT,
                confidence REAL
            )
        """)
        conn.commit()
        conn.close()

    def store_to_db(self, image_bytes, image_hash, accurate, label, confidence):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT OR IGNORE INTO feedback (image, image_hash, accurate, label, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (image_bytes, image_hash, int(accurate), label, confidence))

        conn.commit()
        conn.close()
        
    def preprocess_image(self, image_bytes):
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize(IMG_SIZE)
        arr = np.array(img, dtype=np.float32)
        arr = keras.applications.resnet50.preprocess_input(arr)
        arr = np.expand_dims(arr, axis=0)  # shape: (1, 224, 224, 3)
        return arr
    
    
    def hash_image(self, image_bytes):
        return hashlib.sha256(image_bytes).hexdigest()

service = Service()
print("Database is instantiated!")
IMG_SIZE = (224, 224)


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        img_bytes = file.read()
        img_array = service.preprocess_image(img_bytes)
        prediction = model.predict(img_array)[0][0]  # sigmoid output

        label = "FAKE" if prediction > 0.5 else "REAL"
        confidence = float(prediction) if label == "FAKE" else float(1 - prediction)

        return jsonify({
            "label": label,
            "confidence": round(confidence * 100, 2),
            "raw_score": float(prediction)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})

@app.route("/feedback", methods=["POST"])
def feedback():  
    image = request.files.get("image")
    if not image or image.filename == "":
        return jsonify({"error": "Invalid image"}), 400
    
    required_fields = ["accurate", "result", "confidence"]
    if not all(field in request.form for field in required_fields):
        return jsonify({"error": "Incomplete fields"}), 400
    
    try:
        accurate = request.form.get("accurate") == "true"
        label = request.form.get("result")
        conf = float(request.form.get("confidence")[:-1])
        
        img_bytes = image.read()
        img_hash = service.hash_image(img_bytes)
        
        high_conf = conf >= 80
        misclassified = not accurate
        uncertain = 40 <= conf <= 60
        
        if (misclassified and high_conf) or uncertain:
            service.store_to_db(img_bytes, img_hash, accurate, label, conf)
            
        return jsonify({
            "status": 'processed'
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
        

if __name__ == "__main__":
    app.run(debug=True, port=5000)