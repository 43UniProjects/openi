from openi.core.logger import logger


class SecurityTracker:
    def __init__(self):
        self.known_suspect_track_ids = set()
        self.weapon_strike_counter = {}
        self.reid_strike_counter = {}
        logger.debug("SecurityTracker initialized.")

    def update_weapon_strike(self, trk_id: int, is_holding: bool) -> bool:
        """Updates the weapon strike counter and returns True if confirmed armed."""
        if is_holding:
            self.weapon_strike_counter[trk_id] = self.weapon_strike_counter.get(trk_id, 0) + 1
            if self.weapon_strike_counter[trk_id] == 2:
                logger.warning(f"Weapon strike threshold reached for ID #{trk_id}")
        else:
            self.weapon_strike_counter[trk_id] = max(
                0, self.weapon_strike_counter.get(trk_id, 0) - 1
            )

        return self.weapon_strike_counter.get(trk_id, 0) >= 2

    def update_reid_strike(self, trk_id: int, matched: bool) -> bool:
        """Updates the ReID match counter and returns True if confirmed match."""
        if matched:
            self.reid_strike_counter[trk_id] = self.reid_strike_counter.get(trk_id, 0) + 1
            if self.reid_strike_counter[trk_id] == 3:
                logger.warning(f"ReID match threshold reached for ID #{trk_id}")
        else:
            self.reid_strike_counter[trk_id] = 0

        return self.reid_strike_counter.get(trk_id, 0) >= 3

    def is_prior_suspect(self, trk_id: int) -> bool:
        return trk_id in self.known_suspect_track_ids

    def register_suspect(self, trk_id: int):
        if trk_id not in self.known_suspect_track_ids:
            self.known_suspect_track_ids.add(trk_id)
            logger.critical(f"NEW SUSPECT REGISTERED: Track ID #{trk_id} flagged globally.")
