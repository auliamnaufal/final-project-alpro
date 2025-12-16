import hashlib
import io
import logging
import random
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ModelService:
    """
    Minimal YOLO-based predictor with a deterministic stub fallback.
    """

    def __init__(self, weights_path: Optional[str] = None, seed: int = 42, device: str = "cpu"):
        random.seed(seed)
        self.device = device
        self.model = None
        self.weights_path = Path(weights_path) if weights_path else None
        self.class_names = []

        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            try:
                # Allow ultralytics DetectionModel in torch.load for PyTorch >= 2.6
                import torch
                from ultralytics.nn.tasks import DetectionModel

                torch.serialization.add_safe_globals([DetectionModel])

                # Ensure torch.load defaults to weights_only=False for YOLO checkpoints.
                _orig_load = torch.load

                def _patched_load(*args, **kwargs):
                    kwargs.setdefault("weights_only", False)
                    return _orig_load(*args, **kwargs)

                torch.load = _patched_load
            except Exception:
                pass

            # If a weights path is provided, load it; otherwise load default YOLO weights.
            self.model = YOLO(str(self.weights_path)) if self.weights_path else YOLO()
            self.class_names = getattr(self.model, "names", [])
            logger.info("Loaded YOLO model from %s", self.weights_path or "default model")
        except ImportError:
            logger.warning("ultralytics not installed; falling back to stub predictions")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load YOLO model %s (%s); falling back to stub predictions", self.weights_path, exc)
            self.model = None

    def predict(self, image_bytes: bytes) -> Dict[str, float]:
        if self.model:
            return self._predict_with_yolo(image_bytes)
        return self._predict_stub(image_bytes)

    def _predict_with_yolo(self, image_bytes: bytes) -> Dict[str, float]:
        """Run YOLO detection model and convert detections into a helmet/no-helmet verdict."""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            frame = np.array(image)

            results = self.model(frame, verbose=False)[0]
            names = getattr(results, "names", self.class_names) or self.class_names

            classes_raw = [names[int(c)] if int(c) < len(names) else str(int(c)) for c in results.boxes.cls]

            classes = []
            for c in classes_raw:
                c_lower = c.lower()
                if c_lower in {"head", "person"}:
                    classes.append("person")
                elif "helmet" in c_lower:
                    classes.append("helmet")
                else:
                    classes.append(c_lower)

            person_count = classes.count("person")
            helmet_count = classes.count("helmet")
            violation_count = max(person_count - helmet_count, 0)

            label = "uncertain"
            if person_count > 0:
                label = "no_helmet" if violation_count > 0 else "helmet"

            conf_scores = results.boxes.conf.tolist() if getattr(results, "boxes", None) is not None else []
            confidence = float(sum(conf_scores) / len(conf_scores)) if conf_scores else 0.5

            return {"label": label, "confidence": round(confidence, 3)}
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("YOLO inference failed (%s); using stub prediction", exc)
            return self._predict_stub(image_bytes)

    def _predict_stub(self, image_bytes: bytes) -> Dict[str, float]:
        digest = hashlib.sha1(image_bytes).digest()
        score = int.from_bytes(digest[:2], "big") / 65535

        if score > 0.7:
            label = "helmet"
            confidence = score
        elif score < 0.3:
            label = "no_helmet"
            confidence = 1 - score
        else:
            label = "uncertain"
            confidence = 0.5

        return {"label": label, "confidence": round(confidence, 3)}
