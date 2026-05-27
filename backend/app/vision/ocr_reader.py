import logging
from typing import List, Dict, Any, Optional
import cv2
try:
    import easyocr
except ImportError:
    easyocr = None

logger = logging.getLogger("alas.vision.ocr")

class OCRReader:
    """
    ALAS Optical Character Recognition (OCR).
    Uses EasyOCR to read handwritten notes, whiteboards, and text from images.
    """
    def __init__(self, languages: List[str] = ['en'], use_gpu: bool = False):
        if easyocr is None:
            logger.error("EasyOCR is not installed. Please run: pip install easyocr")
            self.reader = None
        else:
            logger.info(f"Initializing OCR Reader for languages: {languages} (GPU={use_gpu})...")
            # This downloads the model weights on first run
            self.reader = easyocr.Reader(languages, gpu=use_gpu)
            logger.info("📝 OCRReader initialized.")

    def read_text(self, image_path_or_array) -> str:
        """
        Extract text from an image.
        Returns the combined extracted text.
        """
        if self.reader is None:
            return "[OCR Engine Unavailable]"
            
        try:
            # detail=0 returns just the text list
            results = self.reader.readtext(image_path_or_array, detail=0, paragraph=True)
            extracted = "\n".join(results)
            logger.debug(f"Extracted OCR text length: {len(extracted)}")
            return extracted
        except Exception as e:
            logger.error(f"OCR reading failed: {e}")
            return f"[OCR Error: {e}]"

    def read_detailed(self, image_path_or_array) -> List[Dict[str, Any]]:
        """
        Extract detailed OCR data including bounding boxes and confidence scores.
        """
        if self.reader is None:
            return []
            
        try:
            # detail=1 returns [bbox, text, confidence]
            results = self.reader.readtext(image_path_or_array, detail=1)
            detailed_results = []
            for (bbox, text, conf) in results:
                detailed_results.append({
                    "bounding_box": bbox,
                    "text": text,
                    "confidence": float(conf)
                })
            return detailed_results
        except Exception as e:
            logger.error(f"Detailed OCR reading failed: {e}")
            return []
