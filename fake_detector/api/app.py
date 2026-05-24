from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import numpy as np
import io
import sqlite3
import hashlib
import torch
import torch.nn.functional as F
from transformers import ViTImageProcessor, ViTForImageClassification

DB_PATH = "feedback.db"
MODEL_PATH = "Veritas_ViT_Gen2" 

app = Flask(__name__)
CORS(app)  

print("Loading model...")
processor = ViTImageProcessor.from_pretrained(MODEL_PATH)
model = ViTForImageClassification.from_pretrained(MODEL_PATH)
model.eval()
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
                user_id TEXT,
                image BLOB,
                image_hash TEXT UNIQUE,
                accurate INTEGER,
                label TEXT,
                confidence REAL
            )
        """)
        conn.commit()
        conn.close()

    def store_to_db(self, image_bytes, image_hash, accurate, label, confidence, user_id):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT OR IGNORE INTO feedback (image, image_hash, accurate, label, confidence, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (image_bytes, image_hash, int(accurate), label, confidence, user_id))

        conn.commit()
        conn.close()
        
    def hash_image(self, image_bytes):
        return hashlib.sha256(image_bytes).hexdigest()
    
    def get_user_error_rate(self, user_id):
        if not user_id:
            return "unknown_user"

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("SELECT accurate FROM feedback WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        conn.close()

        total_feedbacks = len(rows)

        if total_feedbacks < 5:
            return "learning"

        mistakes = sum(1 for row in rows if row[0] == 0)
        error_rate = mistakes / total_feedbacks

        if error_rate >= 0.40:
            return "frequent_false_alarms"
        
        return "normal"

service = Service()
print("Database is instantiated!")

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    user_id = request.form.get("user_id", None)
    
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        inputs = processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            
            probs = F.softmax(logits, dim=-1)[0]
            
            prediction = probs[1].item() 

        user_context = service.get_user_error_rate(user_id)

        if user_context == "frequent_false_alarms" and 0.50 < prediction < 0.65:
            label = "REAL"
            confidence = float(1 - prediction)
            adjusted_flag = True
        else:
            label = "FAKE" if prediction > 0.5 else "REAL"
            confidence = float(prediction) if label == "FAKE" else float(1 - prediction)
            adjusted_flag = False

        return jsonify({
            "label": label,
            "confidence": round(confidence * 100, 2),
            "context_adjusted": adjusted_flag,
            "raw_score": float(prediction)
        })

    except Exception as e:
        print(f"\nCRASH IN PREDICT: {str(e)}\n")
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
        user_id = request.form.get("user_id")
        
        img_bytes = image.read()
        img_hash = service.hash_image(img_bytes)
        
        high_conf = conf >= 80
        misclassified = not accurate
        uncertain = 40 <= conf <= 60
        
        if (misclassified and high_conf) or uncertain:
            service.store_to_db(img_bytes, img_hash, accurate, label, conf, user_id)
            
        return jsonify({
            "status": 'processed'
        }), 200
        
    except Exception as e:
        print(f"\nCRASH IN FEDBACK: {str(e)}\n")
        return jsonify({
            "error": str(e)
        }), 500
        
if __name__ == "__main__":
    app.run(debug=True, port=5000)