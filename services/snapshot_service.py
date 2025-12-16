import base64
import os
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from flask import current_app

from database import db
from models import Snapshot
from services.model_service import ModelService


class SnapshotService:
    def __init__(self, model_service: ModelService, upload_dir: Path):
        self.model_service = model_service
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def process_snapshot(self, image_b64: str, site: str = "Unknown") -> Dict:
        image_bytes, ext = self._decode_image(image_b64)
        prediction = self.model_service.predict(image_bytes)
        should_save_image = (prediction.get("label") or "").lower() != "helmet"
        filename = self._save_image(image_bytes, ext) if should_save_image else None

        snapshot = Snapshot(
            result=prediction["label"],
            confidence=prediction["confidence"],
            site=site or "Unknown",
            image_path=str(filename),
        )
        db.session.add(snapshot)
        db.session.commit()

        return snapshot.to_dict()

    def _decode_image(self, image_b64: str):
        if image_b64.startswith("data:image"):
            _, encoded = image_b64.split(",", 1)
            ext = image_b64.split(";")[0].split("/")[-1]
        else:
            encoded = image_b64
            ext = "png"

        image_bytes = base64.b64decode(encoded)
        return image_bytes, ext

    def _save_image(self, image_bytes: bytes, ext: str):
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"snapshot_{timestamp}.{ext}"
        filepath = self.upload_dir / filename
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filename

    def get_dashboard_stats(self) -> Dict:
        now = datetime.utcnow()
        past_week = now - timedelta(days=7)
        past_day = now - timedelta(days=1)

        total_events = Snapshot.query.filter(Snapshot.created_at >= past_week).count()
        no_helmet_events = (
            Snapshot.query.filter(
                Snapshot.created_at >= past_week, Snapshot.result == "no_helmet"
            ).count()
        )
        avg_confidence = (
            db.session.query(db.func.avg(Snapshot.confidence))
            .filter(Snapshot.created_at >= past_week)
            .scalar()
        )

        trend = self._trend_by_hour(past_day)
        composition = self._composition(past_week)
        recent = (
            Snapshot.query.order_by(Snapshot.created_at.desc()).limit(10).all()
        )

        return {
            "total_events": total_events,
            "no_helmet_ratio": round(no_helmet_events / total_events, 3)
            if total_events
            else 0,
            "average_confidence": round(avg_confidence, 3) if avg_confidence else 0,
            "trend": trend,
            "composition": composition,
            "recent_events": [s.to_dict() for s in recent],
        }

    def _trend_by_hour(self, since: datetime) -> List[Dict]:
        hourly = (
            db.session.query(
                db.func.strftime("%H", Snapshot.created_at).label("hour"),
                Snapshot.result,
                db.func.count(Snapshot.id),
            )
            .filter(Snapshot.created_at >= since)
            .group_by("hour", Snapshot.result)
            .all()
        )

        trend = {}
        for hour, result, count in hourly:
            trend.setdefault(hour, {}).update({result: count})

        formatted = []
        for hour in sorted(trend.keys()):
            formatted.append(
                {
                    "hour": hour,
                    "total": sum(trend[hour].values()),
                    "no_helmet": trend[hour].get("no_helmet", 0),
                }
            )
        return formatted

    def _composition(self, since: datetime) -> Dict:
        counts = (
            db.session.query(Snapshot.result, db.func.count(Snapshot.id))
            .filter(Snapshot.created_at >= since)
            .group_by(Snapshot.result)
            .all()
        )
        total = sum(count for _, count in counts) or 1
        return {label: round(count / total, 3) for label, count in counts}

    def clear_all(self, delete_files: bool = True) -> None:
        """Remove all snapshot records and optionally delete saved images."""
        Snapshot.query.delete()
        db.session.commit()

        if delete_files and self.upload_dir.exists():
            for file_path in self.upload_dir.glob("*"):
                if file_path.is_file():
                    with suppress(Exception):
                        file_path.unlink()
