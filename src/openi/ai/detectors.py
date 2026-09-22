from ultralytics import YOLO

from openi.core.logger import logger


class SecurityDetectors:
    def __init__(self, weapon_path, person_path, weapon_conf, person_conf, keywords):
        logger.debug("Loading YOLOv26 models into memory... (This may take a moment)")
        try:
            self.weapon_model = YOLO(weapon_path)
            self.person_model = YOLO(person_path)
            self.weapon_conf = weapon_conf
            self.person_conf = person_conf
            self.keywords = keywords
            logger.debug("YOLOv26 models loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO models: {e}")
            raise e

    def get_weapons(self, frame):
        results = self.weapon_model(frame, verbose=False, imgsz=416, conf=self.weapon_conf)
        raw_weapons = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                name = self.weapon_model.names[cls_id].lower()
                if any(k in name for k in self.keywords):
                    raw_weapons.append(
                        {
                            "name": name,
                            "conf": float(box.conf[0]),
                            "coords": list(map(int, box.xyxy[0])),
                        }
                    )
        return raw_weapons

    def get_tracked_persons(self, frame):
        results = self.person_model.track(
            frame, verbose=False, imgsz=416, conf=self.person_conf, classes=[0], persist=True
        )
        raw_persons = []
        # Ultralytics track can sometimes return boxes without IDs if tracking fails momentarily,
        # the 'is not None' check successfully prevents crashes here.
        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            for box, trk_id, conf in zip(boxes, track_ids, confs):
                raw_persons.append(
                    {"track_id": trk_id, "conf": float(conf), "coords": box.tolist()}
                )
        return raw_persons


def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    return interArea / float(boxAArea + boxBArea - interArea + 1e-6)


def find_primary_carrier(weapon_coords, persons):
    if not persons:
        return None

    wx1, wy1, wx2, wy2 = weapon_coords
    w_cx, w_cy = (wx1 + wx2) / 2, (wy1 + wy2) / 2
    best_idx = None
    min_dist = float("inf")
    margin = 10

    for idx, p in enumerate(persons):
        px1, py1, px2, py2 = p["coords"]
        p_cx, p_cy = (px1 + px2) / 2, (py1 + py2) / 2

        if (px1 - margin <= w_cx <= px2 + margin) and (py1 - margin <= w_cy <= py2 + margin):
            dist = (w_cx - p_cx) ** 2 + (w_cy - p_cy) ** 2
            if dist < min_dist:
                min_dist = dist
                best_idx = idx

    return best_idx
