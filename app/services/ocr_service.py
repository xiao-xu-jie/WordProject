"""
OCR Service using PaddleOCR for text extraction from images.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR text extraction using PaddleOCR."""

    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = "ch",
        use_gpu: bool = False,
        show_log: bool = False
    ):
        """
        Initialize PaddleOCR.

        Args:
            use_angle_cls: Whether to use angle classification
            lang: Language code ('ch' for Chinese+English, 'en' for English only)
            use_gpu: Whether to use GPU acceleration
            show_log: Whether to show PaddleOCR logs
        """
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
            use_gpu=use_gpu,
            show_log=show_log
        )
        logger.info(f"OCR Service initialized with lang={lang}, use_gpu={use_gpu}")

    def extract_text_from_image(
        self,
        image_path: str,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Extract text from a single image.

        Args:
            image_path: Path to the image file
            confidence_threshold: Minimum confidence score to include text

        Returns:
            List of dictionaries containing:
                - text: Extracted text
                - confidence: Confidence score (0-1)
                - bbox: Bounding box coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                - position: Simplified position (top, left, width, height)
        """
        try:
            # Run OCR
            result = self.ocr.ocr(image_path, cls=True)

            if not result or not result[0]:
                logger.warning(f"No text detected in image: {image_path}")
                return []

            # Parse results
            extracted_texts = []
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)
                text = text_info[0]
                confidence = text_info[1]

                # Filter by confidence
                if confidence < confidence_threshold:
                    continue

                # Calculate simplified position
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                left = min(x_coords)
                top = min(y_coords)
                width = max(x_coords) - left
                height = max(y_coords) - top

                extracted_texts.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox,
                    "position": {
                        "left": float(left),
                        "top": float(top),
                        "width": float(width),
                        "height": float(height)
                    }
                })

            logger.info(f"Extracted {len(extracted_texts)} text blocks from {image_path}")
            return extracted_texts

        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {str(e)}")
            raise

    def extract_text_from_images(
        self,
        image_paths: List[str],
        confidence_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract text from multiple images.

        Args:
            image_paths: List of image file paths
            confidence_threshold: Minimum confidence score

        Returns:
            Dictionary mapping image path to extracted text blocks
        """
        results = {}
        for image_path in image_paths:
            try:
                results[image_path] = self.extract_text_from_image(
                    image_path,
                    confidence_threshold
                )
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {str(e)}")
                results[image_path] = []

        return results

    def extract_text_from_numpy(
        self,
        image_array: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Extract text from a numpy array (useful for in-memory processing).

        Args:
            image_array: Image as numpy array
            confidence_threshold: Minimum confidence score

        Returns:
            List of extracted text blocks
        """
        try:
            result = self.ocr.ocr(image_array, cls=True)

            if not result or not result[0]:
                return []

            extracted_texts = []
            for line in result[0]:
                bbox = line[0]
                text_info = line[1]
                text = text_info[0]
                confidence = text_info[1]

                if confidence < confidence_threshold:
                    continue

                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                left = min(x_coords)
                top = min(y_coords)
                width = max(x_coords) - left
                height = max(y_coords) - top

                extracted_texts.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox,
                    "position": {
                        "left": float(left),
                        "top": float(top),
                        "width": float(width),
                        "height": float(height)
                    }
                })

            return extracted_texts

        except Exception as e:
            logger.error(f"Error extracting text from numpy array: {str(e)}")
            raise

    def format_for_llm(
        self,
        extracted_texts: List[Dict[str, Any]],
        sort_by_position: bool = True
    ) -> str:
        """
        Format extracted text for LLM processing.

        Args:
            extracted_texts: List of extracted text blocks
            sort_by_position: Whether to sort by vertical position (top to bottom)

        Returns:
            Formatted text string suitable for LLM input
        """
        if not extracted_texts:
            return ""

        # Sort by vertical position if requested
        if sort_by_position:
            extracted_texts = sorted(
                extracted_texts,
                key=lambda x: (x["position"]["top"], x["position"]["left"])
            )

        # Format as structured text
        formatted_lines = []
        for i, item in enumerate(extracted_texts, 1):
            text = item["text"]
            confidence = item["confidence"]
            formatted_lines.append(f"{i}. {text} (confidence: {confidence:.2f})")

        return "\n".join(formatted_lines)


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service(
    use_angle_cls: bool = True,
    lang: str = "ch",
    use_gpu: bool = False
) -> OCRService:
    """
    Get or create OCR service singleton.

    Args:
        use_angle_cls: Whether to use angle classification
        lang: Language code
        use_gpu: Whether to use GPU

    Returns:
        OCRService instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService(
            use_angle_cls=use_angle_cls,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False
        )
    return _ocr_service
