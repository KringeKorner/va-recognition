# imports
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import json
import cv2
import numpy as np
from debug import logger

MINERVA = None

@dataclass
class MinervaFrameRecord:
    frame_id: int
    order: int
    frame: Optional[np.ndarray] = None
    landmark: str = "NONE"
    faces: list[list[int]] = field(default_factory=list)
    eyes: list[list[int]] = field(default_factory=list)
    smiles: list[list[int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "order": self.order,
            "landmark": self.landmark,
            "faces": self.faces,
            "eyes": self.eyes,
            "smiles": self.smiles,
            "npy_name": f"{self.frame_id}.npy",
            "jpg_name": f"{self.frame_id}.jpg",
        }

@dataclass
class MinervaBatch:
    cycle_number: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    frames: list[MinervaFrameRecord] = field(default_factory=list)
    vai_result: Optional[dict[str, Any]] = None
    cpm_result: Optional[dict[str, Any]] = None

    def has_frames(self) -> bool:
        return len(self.frames) > 0

    def has_video_result(self) -> bool:
        return self.vai_result is not None

    def is_commit_ready(self) -> bool:
        return self.has_frames() and self.has_video_result()

def initialize(enabled: bool = False, interval: int = 5, root_folder: str = "MINERVA_data"):
    global MINERVA
    run_number = logger.read_current_run_number()
    MINERVA = MinervaManager(run_number, enabled=enabled, interval=interval, root_folder=root_folder)

def should_sample(cycle_number: int) -> bool:
    if MINERVA is not None:
        return MINERVA.should_sample(cycle_number)
    return False

def begin_batch(cycle_number: int):
    if MINERVA is not None:
        MINERVA.begin_batch(cycle_number)

def store_recorded_frame(data):
    if MINERVA is not None:
        MINERVA.store_recorded_frame(data)

def store_recorded_frames(recorded_frames):
    if MINERVA is not None:
        MINERVA.store_recorded_frames(recorded_frames)

def store_analysis(analyzed_frames):
    if MINERVA is not None:
        MINERVA.store_analysis(analyzed_frames)

def store_video_result(data):
    if MINERVA is not None:
        MINERVA.store_video_result(data)

def store_fused_result(data):
    if MINERVA is not None:
        MINERVA.store_fused_result(data)

def drop_batch(source, reason: str = "UNSPECIFIED"):
    if MINERVA is not None:
        MINERVA.drop_batch(source, reason)

def commit_data() -> bool:
    if MINERVA is not None:
        return MINERVA.commit_data()
    return False

def activate():
    if MINERVA is not None:
        MINERVA.activate()

class MinervaManager:
    def __init__(
        self,
        run_number: str,
        enabled: bool = False,
        interval: int = 5,
        root_folder: str = "MINERVA_data",
        project_root: Optional[str | Path] = None,
        create_cycle_video: bool = True,
        fps: int = 30,
    ) -> None:
        self.enabled = enabled
        self.interval = max(1, int(interval))
        self.run_number = run_number
        self.create_cycle_video = create_cycle_video
        self.fps = fps
        self.project_root = Path(project_root) if project_root is not None else Path.cwd()
        self.root_folder = self.project_root / root_folder
        self.day_str = datetime.now().strftime("%d_%m_%Y")
        self.day_folder = self.root_folder / self.day_str
        self.run_folder = self.day_folder / self.run_number
        self.current_batch: Optional[MinervaBatch] = None
        self.committed_cycles: list[int] = []
        self.activation_complete = False
        self._initialize_directories()
        self._log(
            f"INITIALIZED | ENABLED={self.enabled} | INTERVAL={self.interval} | "
            f"RUN={self.run_number} | ROOT={self.run_folder}"
        )

    def _log(self, message: str) -> None:
        try:
            logger.main("MINERVA", message)
            return
        except Exception:
            print(f"[MINERVA] {message}")

    def _initialize_directories(self) -> None:
        self.run_folder.mkdir(parents=True, exist_ok=True)

    def _get_cycle_folder(self, cycle_number: int) -> Path:
        return self.run_folder / f"C{int(cycle_number):04d}_MINERVA"

    def _get_cycle_frames_folder(self, cycle_number: int) -> Path:
        return self._get_cycle_folder(cycle_number) / "frames"

    def _get_cycle_metadata_folder(self, cycle_number: int) -> Path:
        return self._get_cycle_folder(cycle_number) / "metadata"

    def _get_cycle_output_folder(self, cycle_number: int) -> Path:
        return self._get_cycle_folder(cycle_number) / "output"

    def should_sample(self, cycle_number: int) -> bool:
        if not self.enabled:
            return False
        return int(cycle_number) % self.interval == 0

    def begin_batch(self, cycle_number: int) -> None:
        if not self.enabled:
            return
        self.current_batch = MinervaBatch(cycle_number=int(cycle_number))
        self._log(f"BATCH OPENED | CYCLE=C{int(cycle_number):04d}")

    def drop_batch(self, source: str, reason: str = "UNSPECIFIED") -> None:
        if self.current_batch is None:
            self._log(
                f"DROP IGNORED | SOURCE={str(source).upper()} | "
                f"REASON={str(reason).upper()} | NO ACTIVE BATCH"
            )
            return
        cycle_number = self.current_batch.cycle_number
        self._log(
            f"BATCH DROPPED | CYCLE=C{cycle_number:04d} | "
            f"SOURCE={str(source).upper()} | REASON={str(reason).upper()}"
        )
        self.current_batch = None
    
    def store_recorded_frame(self, frame_packet: dict[str, Any]) -> None:
        if self.current_batch is None:
            return

        try:
            frame_id = int(frame_packet["ID"])
            frame = frame_packet["FRAME"]
        except Exception:
            self._log("STORE_RECORDED_FRAME IGNORED | INVALID FRAME PACKET")
            return

        record = MinervaFrameRecord(
            frame_id=frame_id,
            order=len(self.current_batch.frames),
            landmark="NONE",
            frame=frame,
            faces=[],
            eyes=[],
            smiles=[],
        )
        self.current_batch.frames.append(record)

    def store_recorded_frames(self, recorded_frames: list[dict[str, Any]]) -> None:
        if self.current_batch is None:
            self._log("STORE_RECORDED_FRAMES IGNORED | NO ACTIVE BATCH")
            return
        self.current_batch.frames.clear()
        for order, item in enumerate(recorded_frames):
            self.current_batch.frames.append(
                MinervaFrameRecord(
                    frame_id=self._extract_frame_id(item),
                    order=order,
                    frame=self._extract_frame(item),
                )
            )
        self._log(
            f"RECORDED FRAMES STORED | CYCLE=C{self.current_batch.cycle_number:04d} | "
            f"FRAME_COUNT={len(self.current_batch.frames)}"
        )

    def store_analysis(self, analyzed_data):
        if self.current_batch is None:
            self._log("STORE_ANALYSIS IGNORED | NO ACTIVE BATCH")
            return
        if isinstance(analyzed_data, dict):
            analyzed_items = [analyzed_data]
        else:
            analyzed_items = analyzed_data
        frame_lookup = {record.frame_id: record for record in self.current_batch.frames}
        updated_count = 0
        for item in analyzed_items:
            try:
                frame_id = self._extract_frame_id(item)
            except Exception:
                continue
            record = frame_lookup.get(frame_id)
            if record is None:
                continue
            record.landmark = self._extract_landmark(item)
            detections = self._extract_detections(item)
            record.faces = detections["faces"]
            record.eyes = detections["eyes"]
            record.smiles = detections["smiles"]
            updated_count += 1
        self._log(
            f"ANALYSIS STORED | CYCLE=C{self.current_batch.cycle_number:04d} | "
            f"UPDATED_FRAMES={updated_count}"
        )

    def store_video_result(self, vai_result: dict[str, Any]) -> None:
        if self.current_batch is None:
            self._log("STORE_VIDEO_RESULT IGNORED | NO ACTIVE BATCH")
            return
        self.current_batch.vai_result = vai_result
        self._log(
            f"VIDEO RESULT STORED | CYCLE=C{self.current_batch.cycle_number:04d} | "
            f"MOOD={vai_result.get('vai_mood', 'NONE')} | "
            f"SCORE={vai_result.get('vai_score', 'NONE')}"
        )

    def store_fused_result(self, cpm_result: dict[str, Any]) -> None:
        if self.current_batch is None:
            self._log("STORE_FUSED_RESULT IGNORED | NO ACTIVE BATCH")
            return
        self.current_batch.cpm_result = cpm_result
        self._log(
            f"FUSED RESULT STORED | CYCLE=C{self.current_batch.cycle_number:04d} | "
            f"MOOD={cpm_result.get('fused_mood', 'NONE')} | "
            f"SCORE={cpm_result.get('fused_score', 'NONE')} | "
            f"SOURCE={cpm_result.get('source', 'NONE')}"
        )

    def commit_data(self) -> bool:
        if self.current_batch is None:
            self._log("COMMIT FAILED | NO ACTIVE BATCH")
            return False
        if not self.current_batch.is_commit_ready():
            self._log(
                f"COMMIT FAILED | CYCLE=C{self.current_batch.cycle_number:04d} | "
                "BATCH NOT READY"
            )
            return False

        cycle_number = self.current_batch.cycle_number
        cycle_folder = self._get_cycle_folder(cycle_number)
        frames_folder = self._get_cycle_frames_folder(cycle_number)
        metadata_folder = self._get_cycle_metadata_folder(cycle_number)
        output_folder = self._get_cycle_output_folder(cycle_number)
        cycle_folder.mkdir(parents=True, exist_ok=True)
        frames_folder.mkdir(parents=True, exist_ok=True)
        metadata_folder.mkdir(parents=True, exist_ok=True)
        output_folder.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        for frame_record in self.current_batch.frames:
            if frame_record.frame is None:
                continue
            np.save(frames_folder / f"{frame_record.frame_id}.npy", frame_record.frame)
            saved_count += 1

        frame_map = {
            "cycle_number": cycle_number,
            "created_at": self.current_batch.created_at,
            "frame_count": len(self.current_batch.frames),
            "frames_saved": saved_count,
            "frames": [frame.to_dict() for frame in self.current_batch.frames],
        }
        with open(metadata_folder / "frame_map.json", "w", encoding="utf-8") as file:
            json.dump(frame_map, file, indent=4)
        with open(metadata_folder / "vai_result.json", "w", encoding="utf-8") as file:
            json.dump(self.current_batch.vai_result, file, indent=4)
        if self.current_batch.cpm_result is not None:
            with open(metadata_folder / "cpm_result.json", "w", encoding="utf-8") as file:
                json.dump(self.current_batch.cpm_result, file, indent=4)

        self.committed_cycles.append(cycle_number)
        self._log(
            f"COMMIT SUCCESS | CYCLE=C{cycle_number:04d} | "
            f"FRAMES_SAVED={saved_count} | PATH={cycle_folder}"
        )
        self.current_batch = None
        return True

    def activate(self) -> None:
        if not self.enabled:
            self._log("MINERVA DISABLED, SKIPPING ACTIVATION SEQUENCE")
            return
        if self.activation_complete:
            self._log("ACTIVATE IGNORED | ALREADY COMPLETE")
            return

        self._log(
            f"ACTIVATION STARTED | COMMITTED_CYCLE_COUNT={len(self.committed_cycles)}"
        )
        for cycle_number in self.committed_cycles:
            try:
                self._build_cycle_output(cycle_number)
                self._log(f"ACTIVATION CYCLE COMPLETE | CYCLE=C{cycle_number:04d}")
            except Exception as exc:
                self._log(
                    f"ACTIVATION CYCLE FAILED | CYCLE=C{cycle_number:04d} | ERROR={exc}"
                )

        self.activation_complete = True
        self._log("ACTIVATION COMPLETE")

    def _extract_frame_id(self, item: dict[str, Any]) -> int:
        if "FRAME_ID" in item:
            return int(item["FRAME_ID"])
        if "frame_id" in item:
            return int(item["frame_id"])
        if "FRAME" in item and isinstance(item["FRAME"], dict) and "ID" in item["FRAME"]:
            return int(item["FRAME"]["ID"])
        if "ID" in item:
            return int(item["ID"])
        raise KeyError("MINERVA COULD NOT EXTRACT FRAME ID FROM PACKET")

    def _extract_landmark(self, item: dict[str, Any]) -> str:
        if "landmark" in item:
            return str(item.get("landmark", "NONE"))
        return str(item.get("LANDMARK", "NONE"))

    def _extract_frame(self, item: dict[str, Any]) -> Optional[np.ndarray]:
        if "frame" in item:
            return item.get("frame")
        frame_packet = item.get("FRAME")
        if isinstance(frame_packet, dict):
            return frame_packet.get("FRAME")
        return None

    def _extract_detections(self, item: dict[str, Any]) -> dict[str, list[list[int]]]:
        detections: Any = item.get("detections", item.get("DETECTIONS", {}))
        if not isinstance(detections, dict):
            detections = {}
        return {
            "faces": self._normalize_rect_list(detections.get("faces", detections.get("FACE_RECTS", []))),
            "eyes": self._normalize_rect_list(detections.get("eyes", detections.get("EYE_RECTS", []))),
            "smiles": self._normalize_rect_list(detections.get("smiles", detections.get("SMILE_RECTS", []))),
        }

    def _normalize_rect_list(self, rects: Any) -> list[list[int]]:
        normalized: list[list[int]] = []
        if rects is None:
            return normalized
        for rect in rects:
            if rect is None:
                continue
            try:
                x, y, w, h = rect
                normalized.append([int(x), int(y), int(w), int(h)])
            except Exception:
                continue
        return normalized

    def _build_cycle_output(self, cycle_number: int) -> None:
        frames_folder = self._get_cycle_frames_folder(cycle_number)
        metadata_folder = self._get_cycle_metadata_folder(cycle_number)
        output_folder = self._get_cycle_output_folder(cycle_number)

        with open(metadata_folder / "frame_map.json", "r", encoding="utf-8") as file:
            frame_map = json.load(file)
        with open(metadata_folder / "vai_result.json", "r", encoding="utf-8") as file:
            vai_result = json.load(file)

        cpm_result = None
        cpm_path = metadata_folder / "cpm_result.json"
        if cpm_path.exists():
            with open(cpm_path, "r", encoding="utf-8") as file:
                cpm_result = json.load(file)

        frame_entries = sorted(frame_map["frames"], key=lambda item: item["order"])
        rendered_paths: list[Path] = []

        for frame_entry in frame_entries:
            frame_id = int(frame_entry["frame_id"])
            landmark = str(frame_entry.get("landmark", "NONE"))
            faces = self._normalize_rect_list(frame_entry.get("faces", []))
            eyes = self._normalize_rect_list(frame_entry.get("eyes", []))
            smiles = self._normalize_rect_list(frame_entry.get("smiles", []))

            npy_path = frames_folder / f"{frame_id}.npy"
            if not npy_path.exists():
                self._log(
                    f"FRAME LOAD SKIPPED | CYCLE=C{cycle_number:04d} | FRAME_ID={frame_id}"
                )
                continue

            frame = np.load(npy_path)
            stamped = self._stamp_frame(
                frame=frame,
                frame_id=frame_id,
                landmark=landmark,
                faces=faces,
                eyes=eyes,
                smiles=smiles,
                vai_result=vai_result,
                cpm_result=cpm_result,
                cycle_number=cycle_number,
            )
            jpg_path = output_folder / f"{frame_id}.jpg"
            cv2.imwrite(str(jpg_path), stamped)
            rendered_paths.append(jpg_path)

        if self.create_cycle_video and rendered_paths:
            self._try_build_cycle_video(cycle_number, rendered_paths, output_folder)

    def _stamp_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        landmark: str,
        faces: list[list[int]],
        eyes: list[list[int]],
        smiles: list[list[int]],
        vai_result: dict[str, Any],
        cpm_result: Optional[dict[str, Any]],
        cycle_number: int,
    ) -> np.ndarray:
        canvas = frame.copy()
        if len(canvas.shape) == 2:
            canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

        self._draw_rectangles(canvas, faces, (0, 255, 0), 2)
        self._draw_rectangles(canvas, eyes, (0, 0, 255), 2)
        self._draw_rectangles(canvas, smiles, (255, 0, 0), 2)

        video_mood = vai_result.get("vai_mood", "NONE")
        video_score = vai_result.get("vai_score", "NONE")
        lines = [
            f"CYCLE ID: C{cycle_number:04d}",
            f"FRAME ID: {frame_id}",
            f"LANDMARK: {landmark}",
            f"FACES: {len(faces)} | EYES: {len(eyes)} | SMILES: {len(smiles)}",
            f"VIDEO MOOD: {video_mood}",
            f"VIDEO SCORE: {video_score}",
        ]
        if cpm_result is not None:
            lines.append(f"FUSED MOOD: {cpm_result.get('fused_mood', 'NONE')}")
            lines.append(f"FUSED SCORE: {cpm_result.get('fused_score', 'NONE')}")
            lines.append(f"SOURCE: {cpm_result.get('source', 'NONE')}")

        y0 = 30
        dy = 30
        for idx, line in enumerate(lines):
            y = y0 + (idx * dy)
            text_size, _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            text_w, text_h = text_size
            cv2.rectangle(canvas, (10, y - text_h - 8), (20 + text_w, y + 8), (0, 0, 0), thickness=-1)
            cv2.putText(canvas, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        return canvas

    def _draw_rectangles(
        self,
        canvas: np.ndarray,
        rectangles: list[list[int]],
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        for rect in rectangles:
            try:
                x, y, w, h = rect
                cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness)
            except Exception:
                continue

    def _try_build_cycle_video(
        self,
        cycle_number: int,
        rendered_paths: list[Path],
        output_folder: Path,
    ) -> None:
        writer = None
        try:
            first_frame = cv2.imread(str(rendered_paths[0]))
            if first_frame is None:
                self._log(f"VIDEO BUILD SKIPPED | CYCLE=C{cycle_number:04d} | FIRST FRAME INVALID")
                return
            height, width = first_frame.shape[:2]
            video_path = output_folder / f"C{cycle_number:04d}_MINERVA.avi"
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"XVID"), self.fps, (width, height))
            if not writer.isOpened():
                self._log(f"VIDEO BUILD FAILED | CYCLE=C{cycle_number:04d} | WRITER NOT OPENED")
                return
            for image_path in rendered_paths:
                frame = cv2.imread(str(image_path))
                if frame is None:
                    continue
                writer.write(frame)
            self._log(f"VIDEO BUILD SUCCESS | CYCLE=C{cycle_number:04d} | PATH={video_path}")
        except Exception as exc:
            self._log(f"VIDEO BUILD FAILED | CYCLE=C{cycle_number:04d} | ERROR={exc}")
        finally:
            if writer is not None:
                writer.release()
