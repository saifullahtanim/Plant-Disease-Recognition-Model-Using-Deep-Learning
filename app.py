from __future__ import annotations

from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, abort
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from functools import lru_cache
from pathlib import Path
import sqlite3
import threading
from datetime import datetime, timezone
import json
import time
import uuid

import numpy as np
import tensorflow as tf

app = Flask(__name__)
app.config.setdefault("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)  # 8MB

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploadimages"
MODEL_PATH = BASE_DIR / "models" / "plant_disease_recog_model_pwp.keras"
PLANT_DISEASE_PATH = BASE_DIR / "plant_disease.json"
DB_PATH = BASE_DIR / "analysis.sqlite3"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
label = ['Apple___Apple_scab',
 'Apple___Black_rot',
 'Apple___Cedar_apple_rust',
 'Apple___healthy',
 'Background_without_leaves',
 'Blueberry___healthy',
 'Cherry___Powdery_mildew',
 'Cherry___healthy',
 'Corn___Cercospora_leaf_spot Gray_leaf_spot',
 'Corn___Common_rust',
 'Corn___Northern_Leaf_Blight',
 'Corn___healthy',
 'Grape___Black_rot',
 'Grape___Esca_(Black_Measles)',
 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
 'Grape___healthy',
 'Orange___Haunglongbing_(Citrus_greening)',
 'Peach___Bacterial_spot',
 'Peach___healthy',
 'Pepper,_bell___Bacterial_spot',
 'Pepper,_bell___healthy',
 'Potato___Early_blight',
 'Potato___Late_blight',
 'Potato___healthy',
 'Raspberry___healthy',
 'Soybean___healthy',
 'Squash___Powdery_mildew',
 'Strawberry___Leaf_scorch',
 'Strawberry___healthy',
 'Tomato___Bacterial_spot',
 'Tomato___Early_blight',
 'Tomato___Late_blight',
 'Tomato___Leaf_Mold',
 'Tomato___Septoria_leaf_spot',
 'Tomato___Spider_mites Two-spotted_spider_mite',
 'Tomato___Target_Spot',
 'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
 'Tomato___Tomato_mosaic_virus',
 'Tomato___healthy']

with open(PLANT_DISEASE_PATH, 'r', encoding='utf-8') as file:
    plant_disease = json.load(file)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                prediction_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                top_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# print(plant_disease[4])

@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.route('/',methods = ['GET'])
def home():
    init_db()
    return render_template('home.html', cache_bust=int(time.time()))


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_e):
    init_db()
    return (
        render_template(
            "home.html",
            cache_bust=int(time.time()),
            error="File is too large. Please upload an image under 8MB.",
        ),
        413,
    )


@lru_cache(maxsize=1)
def get_model() -> tf.keras.Model:
    print("Loading model...")
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Model loaded successfully!")
    return model

def extract_features_from_bytes(image_bytes: bytes) -> tf.Tensor:
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, [160, 160])
    image = tf.cast(image, tf.float32)
    image = tf.expand_dims(image, axis=0)
    return image

def model_predict(image_bytes: bytes, k: int = 3):
    img = extract_features_from_bytes(image_bytes)
    raw = get_model().predict(img, verbose=0)
    scores = raw[0]
    probs = tf.nn.softmax(scores).numpy() if scores.ndim == 1 else tf.nn.softmax(scores[0]).numpy()

    k = max(1, min(int(k), len(probs)))
    top_idx = np.argsort(probs)[-k:][::-1]

    top_predictions = []
    for idx in top_idx:
        idx_int = int(idx)
        entry = plant_disease[idx_int]
        top_predictions.append(
            {
                "idx": idx_int,
                "name": entry.get("name", ""),
                "cause": entry.get("cause", ""),
                "cure": entry.get("cure", ""),
                "confidence": float(probs[idx_int]),
            }
        )

    primary = top_predictions[0]
    return primary, top_predictions


def record_analysis(*, image_filename: str, primary: dict, top_predictions: list[dict]) -> tuple[int, str]:
    created_at = datetime.now(timezone.utc).isoformat()
    top_compact = [
        {"name": p.get("name", ""), "confidence": float(p.get("confidence", 0.0))}
        for p in top_predictions
    ]
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses (created_at, image_filename, prediction_name, confidence, top_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at,
                image_filename,
                primary.get("name", ""),
                float(primary.get("confidence", 0.0)),
                json.dumps(top_compact, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid), created_at

@app.route('/upload/',methods = ['POST','GET'])
def uploadimage():
    if request.method == "POST":
        init_db()
        image = request.files.get('img')
        if not image:
            return redirect('/')

        safe_name = secure_filename(image.filename or "upload.jpg")
        file_id = uuid.uuid4().hex
        saved_name = f"temp_{file_id}_{safe_name}"

        content_type = (image.mimetype or "").lower()
        if content_type and content_type not in {"image/jpeg", "image/png"}:
            return (
                render_template(
                    "home.html",
                    cache_bust=int(time.time()),
                    error="Unsupported file type. Please upload a JPG or PNG image.",
                ),
                400,
            )

        image_bytes = image.read() or b""
        if len(image_bytes) < 20:
            return (
                render_template(
                    "home.html",
                    cache_bust=int(time.time()),
                    error="The uploaded file looks empty or invalid. Please try another image.",
                ),
                400,
            )

        try:
            primary, top_predictions = model_predict(image_bytes, k=3)
        except Exception:
            return (
                render_template(
                    "home.html",
                    cache_bust=int(time.time()),
                    error="We couldn't read that image. Please upload a clear JPG/PNG leaf photo.",
                ),
                400,
            )

        # Save only after we know it's a valid image.
        saved_path = UPLOAD_DIR / saved_name
        try:
            saved_path.write_bytes(image_bytes)
        except Exception:
            return (
                render_template(
                    "home.html",
                    cache_bust=int(time.time()),
                    error="Upload succeeded but saving failed. Please try again.",
                ),
                500,
            )

        analysis_id, created_at = record_analysis(
            image_filename=saved_name,
            primary=primary,
            top_predictions=top_predictions,
        )
        return render_template(
            'home.html',
            result=True,
            imagepath=f"/uploadimages/{saved_name}",
            prediction=primary,
            top_predictions=top_predictions,
            analysis_id=analysis_id,
            created_at=created_at,
            cache_bust=int(time.time()),
        )
    
    else:
        return redirect('/')


@app.get('/api/history')
def api_history_list():
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, image_filename, prediction_name, confidence
            FROM analyses
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    items = [
        {
            "id": int(r["id"]),
            "created_at": r["created_at"],
            "image_url": f"/uploadimages/{r['image_filename']}",
            "prediction_name": r["prediction_name"],
            "confidence": float(r["confidence"]),
        }
        for r in rows
    ]
    return jsonify(items)


@app.delete('/api/history/<int:analysis_id>')
def api_history_delete(analysis_id: int):
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_filename FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        if not row:
            abort(404)
        image_filename = row["image_filename"]
        conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        conn.commit()

    # Best-effort delete associated image file.
    try:
        (UPLOAD_DIR / image_filename).unlink(missing_ok=True)
    except Exception:
        pass

    return jsonify({"ok": True})


@app.get('/report/<int:analysis_id>')
def report(analysis_id: int):
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, image_filename, prediction_name, confidence, top_json
            FROM analyses
            WHERE id = ?
            """,
            (analysis_id,),
        ).fetchone()
        if not row:
            abort(404)

    top = []
    try:
        top = json.loads(row["top_json"]) or []
    except Exception:
        top = []

    return render_template(
        'report.html',
        cache_bust=int(time.time()),
        analysis={
            "id": int(row["id"]),
            "created_at": row["created_at"],
            "image_url": f"/uploadimages/{row['image_filename']}",
            "prediction_name": row["prediction_name"],
            "confidence": float(row["confidence"]),
            "top": top,
        },
    )
        
    
if __name__ == "__main__":
    init_db()

    def warmup():
        try:
            model = get_model()
            dummy = tf.zeros([1, 160, 160, 3], dtype=tf.float32)
            model.predict(dummy, verbose=0)
        except Exception:
            pass

    threading.Thread(target=warmup, daemon=True).start()

    # Debug reloader can import the app twice; keeping it off makes startup faster
    # (especially when TensorFlow is involved).
    app.run(debug=True, use_reloader=False)