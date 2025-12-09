"""
PDF Processing Service for converting PDF pages to images.
"""
import logging
from typing import List, Optional, Tuple
from pathlib import Path
import tempfile
import shutil
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF processing and conversion to images."""

    def __init__(
        self,
        dpi: int = 300,
        fmt: str = "PNG",
        thread_count: int = 4
    ):
        """
        Initialize PDF service.

        Args:
            dpi: Resolution for image conversion (higher = better quality)
            fmt: Output image format (PNG, JPEG, etc.)
            thread_count: Number of threads for parallel processing
        """
        self.dpi = dpi
        self.fmt = fmt
        self.thread_count = thread_count
        logger.info(f"PDF Service initialized with dpi={dpi}, format={fmt}")

    def convert_pdf_to_images(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None
    ) -> List[str]:
        """
        Convert PDF pages to images.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save images (if None, uses temp directory)
            first_page: First page to convert (1-indexed, None = from start)
            last_page: Last page to convert (1-indexed, None = to end)

        Returns:
            List of image file paths

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If conversion fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="pdf_images_")
        else:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Converting PDF {pdf_path} to images (DPI={self.dpi})")

            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt=self.fmt.lower(),
                thread_count=self.thread_count,
                first_page=first_page,
                last_page=last_page
            )

            # Save images
            image_paths = []
            for i, image in enumerate(images, start=1):
                page_num = (first_page or 1) + i - 1
                image_path = Path(output_dir) / f"page_{page_num:04d}.{self.fmt.lower()}"
                image.save(str(image_path), self.fmt)
                image_paths.append(str(image_path))

            logger.info(f"Converted {len(images)} pages to images in {output_dir}")
            return image_paths

        except Exception as e:
            logger.error(f"Error converting PDF {pdf_path}: {str(e)}")
            raise

    def convert_pdf_page_to_image(
        self,
        pdf_path: str,
        page_number: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert a single PDF page to an image.

        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to convert (1-indexed)
            output_path: Path to save the image (if None, uses temp file)

        Returns:
            Path to the saved image

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If page number is invalid
            Exception: If conversion fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if page_number < 1:
            raise ValueError(f"Invalid page number: {page_number}")

        try:
            logger.info(f"Converting page {page_number} of {pdf_path}")

            # Convert single page
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt=self.fmt.lower(),
                first_page=page_number,
                last_page=page_number
            )

            if not images:
                raise ValueError(f"Page {page_number} not found in PDF")

            # Save image
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=f".{self.fmt.lower()}",
                    delete=False
                )
                output_path = temp_file.name
                temp_file.close()

            images[0].save(output_path, self.fmt)
            logger.info(f"Saved page {page_number} to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting page {page_number} of {pdf_path}: {str(e)}")
            raise

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get basic information about a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with PDF information:
                - total_pages: Number of pages
                - file_size: File size in bytes
                - file_name: Name of the file

        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # Convert first page to get page count
            # Note: pdf2image doesn't provide direct page count
            # We need to convert at least one page to validate the PDF
            images = convert_from_path(
                pdf_path,
                dpi=72,  # Low DPI for quick check
                first_page=1,
                last_page=1
            )

            # Get total pages by trying to convert all pages with low DPI
            all_images = convert_from_path(pdf_path, dpi=72)
            total_pages = len(all_images)

            return {
                "total_pages": total_pages,
                "file_size": pdf_file.stat().st_size,
                "file_name": pdf_file.name
            }

        except Exception as e:
            logger.error(f"Error getting PDF info for {pdf_path}: {str(e)}")
            raise

    def convert_pdf_to_images_batch(
        self,
        pdf_path: str,
        output_dir: str,
        batch_size: int = 10
    ) -> List[List[str]]:
        """
        Convert PDF to images in batches (useful for large PDFs).

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save images
            batch_size: Number of pages per batch

        Returns:
            List of batches, where each batch is a list of image paths

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If conversion fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Get total pages
        info = self.get_pdf_info(pdf_path)
        total_pages = info["total_pages"]

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        batches = []
        for start_page in range(1, total_pages + 1, batch_size):
            end_page = min(start_page + batch_size - 1, total_pages)

            logger.info(f"Processing batch: pages {start_page}-{end_page}")

            batch_images = self.convert_pdf_to_images(
                pdf_path,
                output_dir=output_dir,
                first_page=start_page,
                last_page=end_page
            )

            batches.append(batch_images)

        logger.info(f"Converted {total_pages} pages in {len(batches)} batches")
        return batches

    @staticmethod
    def cleanup_temp_images(image_paths: List[str]) -> None:
        """
        Clean up temporary image files.

        Args:
            image_paths: List of image file paths to delete
        """
        for image_path in image_paths:
            try:
                Path(image_path).unlink(missing_ok=True)
                logger.debug(f"Deleted temporary image: {image_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {image_path}: {str(e)}")

    @staticmethod
    def cleanup_temp_directory(directory: str) -> None:
        """
        Clean up temporary directory and all its contents.

        Args:
            directory: Path to the directory to delete
        """
        try:
            shutil.rmtree(directory, ignore_errors=True)
            logger.debug(f"Deleted temporary directory: {directory}")
        except Exception as e:
            logger.warning(f"Failed to delete directory {directory}: {str(e)}")


# Singleton instance
_pdf_service: Optional[PDFService] = None


def get_pdf_service(dpi: int = 300, fmt: str = "PNG") -> PDFService:
    """
    Get or create PDF service singleton.

    Args:
        dpi: Resolution for image conversion
        fmt: Output image format

    Returns:
        PDFService instance
    """
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService(dpi=dpi, fmt=fmt)
    return _pdf_service
