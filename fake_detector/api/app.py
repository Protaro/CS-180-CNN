from flask import Flask, request, jsonify
from flask_cors import CORS
import tf_keras as keras
from PIL import Image
import numpy as np
import tensorflow as tf
import io

app = Flask(__name__)
CORS(app)  # allows the Chrome extension to call this API

# Load model once at startup
print("Loading model...")
model = keras.models.load_model(
    "Veritas_Model_May03.h5"
)
print("Model ready!")

IMG_SIZE = (224, 224)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img, dtype=np.float32)
    arr = keras.applications.resnet50.preprocess_input(arr)
    arr = np.expand_dims(arr, axis=0)  # shape: (1, 224, 224, 3)
    return arr

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        img_bytes = file.read()
        img_array = preprocess_image(img_bytes)
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)