import os
from pathlib import Path

from flask import Flask, current_app, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit

from database import db
from services.model_service import ModelService
from services.snapshot_service import SnapshotService


# Use threading to avoid eventlet/gevent compatibility hassles on newer Python versions.
socketio = SocketIO(async_mode="threading")


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///helmet_monitor.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    with app.app_context():
        db.create_all()

    upload_dir = Path(app.root_path) / "uploads"
    default_weights = Path(app.root_path) / "helmet_detection_model.pt"
    weights_path = os.environ.get("MODEL_WEIGHTS") or (default_weights if default_weights.exists() else None)
    snapshot_service = SnapshotService(ModelService(weights_path=weights_path), upload_dir)

    @app.route("/")
    def camera_page():
        return render_template("camera.html")

    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(upload_dir, filename)

    @app.route("/api/predict", methods=["POST"])
    def predict():
        payload = request.get_json(silent=True) or {}
        image_b64 = payload.get("image")
        site = payload.get("site", "Unknown")
        if not image_b64:
            return jsonify({"error": "image is required"}), 400

        snapshot = snapshot_service.process_snapshot(image_b64, site)
        return jsonify(snapshot)

    @app.route("/api/dashboard", methods=["GET"])
    def dashboard_data():
        return jsonify(snapshot_service.get_dashboard_stats())

    @app.route("/api/admin/clear", methods=["POST"])
    def clear_data():
        snapshot_service.clear_all(delete_files=True)
        return jsonify({"status": "cleared"})

    @socketio.on("predict")
    def handle_prediction(payload):
        payload = payload or {}
        image_b64 = payload.get("image")
        site = payload.get("site", "Unknown")
        if not image_b64:
            emit("prediction_error", {"error": "image is required"})
            return

        try:
            snapshot = snapshot_service.process_snapshot(image_b64, site)
            emit("prediction", snapshot)
        except Exception as exc:  # pragma: no cover - defensive
            current_app.logger.exception("Prediction websocket failed: %s", exc)
            emit("prediction_error", {"error": "prediction failed"})

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
