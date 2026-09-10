import os
import cv2
import time
from config import *
from reid_engine import ReIDEngine
from detectors import SecurityDetectors, compute_iou, find_primary_carrier

def main():
    print("[1/3] Initializing security architecture...")
    detectors = SecurityDetectors(
        WEAPON_MODEL_PATH, PERSON_MODEL_PATH, 
        WEAPON_CONF, PERSON_CONF, WEAPON_KEYWORDS
    )
    reid_system = ReIDEngine(REID_THRESHOLD)

    video_path = "src/knife/knife-cover-2.MOV"
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}.")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    playback_delay = int(1000 / original_fps) if original_fps > 0 else 30

    cv2.namedWindow("Museum Security System", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Museum Security System", 1280, 720)

    frame_count = 0
    known_suspect_track_ids = set()
    weapon_strike_counter = {}
    reid_strike_counter = {}

    print("[2/3] Modules loaded successfully.")
    print("[3/3] Video stream active. Press 'q' to stop.")

    while True:
        start_time = time.time()
        success, frame = cap.read()
        if not success:
            break

        frame_count += 1
        h, w, _ = frame.shape

        if frame_count % 2 == 0 or frame_count == 1:
            cached_draw_items = []
            raw_weapons = detectors.get_weapons(frame)
            raw_persons = detectors.get_tracked_persons(frame)

            overlapping_indices = set()
            for i in range(len(raw_persons)):
                for j in range(i + 1, len(raw_persons)):
                    if compute_iou(raw_persons[i]['coords'], raw_persons[j]['coords']) > 0.15:
                        overlapping_indices.add(i)
                        overlapping_indices.add(j)

            currently_holding_indices = set()
            for w_item in raw_weapons:
                carrier_idx = find_primary_carrier(w_item['coords'], raw_persons)
                if carrier_idx is not None:
                    currently_holding_indices.add(carrier_idx)

            for idx, p in enumerate(raw_persons):
                trk_id = p['track_id']
                px1, py1, px2, py2 = p['coords']
                px1, py1 = max(0, px1), max(0, py1)
                px2, py2 = min(w, px2), min(h, py2)
                
                person_crop = frame[py1:py2, px1:px2]

                if idx in currently_holding_indices:
                    weapon_strike_counter[trk_id] = weapon_strike_counter.get(trk_id, 0) + 1
                else:
                    weapon_strike_counter[trk_id] = max(0, weapon_strike_counter.get(trk_id, 0) - 1)

                is_confirmed_armed = (weapon_strike_counter.get(trk_id, 0) >= 2)
                is_prior_suspect = (trk_id in known_suspect_track_ids)

                matched_reid = False
                if not is_prior_suspect and not is_confirmed_armed:
                    if reid_system.match(person_crop):
                        reid_strike_counter[trk_id] = reid_strike_counter.get(trk_id, 0) + 1
                        if reid_strike_counter[trk_id] >= 3:
                            matched_reid = True
                    else:
                        reid_strike_counter[trk_id] = 0

                is_suspect = is_confirmed_armed or is_prior_suspect or matched_reid

                if is_suspect:
                    known_suspect_track_ids.add(trk_id)
                    if is_confirmed_armed and (idx not in overlapping_indices) and person_crop.size > 0:
                        if reid_system.register_suspect(person_crop):
                            crop_file = os.path.join(SUSPECT_DIR, f"suspect_{int(time.time()*1000)}.jpg")
                            cv2.imwrite(crop_file, person_crop)
                            print(f"[VERIFIED] Clean suspect snapshot saved: {crop_file}")

                    cached_draw_items.append({
                        'coords': (px1, py1, px2, py2),
                        'label': f"SUSPECT #{trk_id}",
                        'color': (0, 0, 255),
                        'thickness': 3
                    })
                else:
                    cached_draw_items.append({
                        'coords': (px1, py1, px2, py2),
                        'label': f"PERSON #{trk_id}",
                        'color': (0, 255, 0),
                        'thickness': 2
                    })

            for w_item in raw_weapons:
                cached_draw_items.append({
                    'coords': w_item['coords'],
                    'label': f"{w_item['name'].upper()} {w_item['conf']:.2f}",
                    'color': (0, 0, 255),
                    'thickness': 2
                })

        for item in cached_draw_items:
            x1, y1, x2, y2 = item['coords']
            cv2.rectangle(frame, (x1, y1), (x2, y2), item['color'], item['thickness'])
            cv2.putText(frame, item['label'], (x1, max(25, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, item['color'], 2)

        if any("SUSPECT" in item['label'] for item in cached_draw_items):
            cv2.putText(frame, "CRITICAL: SUSPECT FLAGGED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        cv2.imshow("Museum Security System", frame)

        elapsed_ms = int((time.time() - start_time) * 1000)
        delay = max(1, playback_delay - elapsed_ms)

        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
