import cv2

from openi.core.logger import logger


class Identifier:
    def __init__(self, threshold):
        self.threshold = threshold
        self.suspect_signatures = []
        logger.debug(f"Identifier initialized with similarity threshold: {self.threshold}")

    def compute_signature(self, image_crop):
        if image_crop is None or image_crop.size == 0:
            return None

        h, w = image_crop.shape[:2]
        start_y, end_y = int(h * 0.20), int(h * 0.60)
        start_x, end_x = int(w * 0.25), int(w * 0.75)

        torso_crop = image_crop[start_y:end_y, start_x:end_x]
        if torso_crop.size == 0:
            torso_crop = image_crop

        hsv = cv2.cvtColor(torso_crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist

    def match(self, candidate_crop):
        if candidate_crop is None or candidate_crop.size == 0 or not self.suspect_signatures:
            return False

        candidate_history = self.compute_signature(candidate_crop)
        if candidate_history is None:
            return False

        for sig in self.suspect_signatures:
            similarity = cv2.compareHist(candidate_history, sig, cv2.HISTCMP_CORREL)
            if similarity >= self.threshold:
                logger.info(f"Identifier: match found (Similarity: {similarity:.2f})")
                return True
        return False

    def register_suspect(self, image_crop):
        sig = self.compute_signature(image_crop)
        if sig is not None:
            self.suspect_signatures.append(sig)
            if len(self.suspect_signatures) > 4:
                self.suspect_signatures.pop(0)
            logger.debug(
                f"Suspect signature registered in ReID Engine (Total Signatures: {len(self.suspect_signatures)})"
            )
            return True

        logger.warning("Failed to compute signature for suspect registration.")
        return False
