import pytesseract
from PIL import Image
import io
from app.core.config import settings
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
import re


class TesseractOCRService:
    """
    Free and open-source OCR using Tesseract
    No API costs, runs locally
    """
    def __init__(self):
        # Set tesseract command path if specified
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        
        # Test if tesseract is available
        try:
            pytesseract.get_tesseract_version()
            self.available = True
        except Exception as e:
            print(f"Tesseract not available: {str(e)}")
            print("Install Tesseract: https://github.com/tesseract-ocr/tesseract")
            self.available = False
    
    def extract_text_from_image(self, image_content: bytes) -> Dict:
        if not self.available:
            return {
                "raw_text": "Tesseract OCR not installed. Please install Tesseract.",
                "merchant_name": None,
                "amount": None,
                "date": None,
                "confidence": 0.0
            }
        
        try:
            # Open image
            image = Image.open(io.BytesIO(image_content))
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            
            # Get confidence data
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                confidence = Decimal(str(avg_confidence / 100))
            except:
                confidence = Decimal("0.80")  # Default confidence
            
            # Parse receipt data
            merchant_name = self._extract_merchant_name(text)
            amount = self._extract_amount(text)
            date = self._extract_date(text)
            
            return {
                "raw_text": text,
                "merchant_name": merchant_name,
                "amount": amount,
                "date": date,
                "confidence": confidence
            }
        except Exception as e:
            raise Exception(f"Tesseract OCR failed: {str(e)}")
    
    def _extract_merchant_name(self, text: str) -> Optional[str]:
        """Extract merchant name from first few lines"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Usually merchant name is in first 3 lines
            for line in lines[:3]:
                if len(line) > 2 and not line.replace('.', '').isdigit():
                    # Skip lines that look like dates or amounts
                    if not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line):
                        if not re.search(r'\$\d+\.?\d*', line):
                            return line
        return None
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """Extract dollar amount from text"""
        # Common patterns for receipt totals
        patterns = [
            r'(?:TOTAL|Total|AMOUNT|Amount|SUBTOTAL|Subtotal)[:\s]*\$?\s*(\d+[.,]\d{2})',
            r'\$\s*(\d+[.,]\d{2})',
            r'(\d+[.,]\d{2})\s*USD',
            r'TOTAL\s+(\d+[.,]\d{2})',
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.replace(',', '.')
                try:
                    amounts.append(Decimal(amount_str))
                except:
                    continue
        
        # Return the largest amount found (usually the total)
        return max(amounts) if amounts else None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None


class GoogleVisionOCRService:
    """
    Optional Google Cloud Vision OCR
    Only used if OCR_ENGINE=google
    """
    def __init__(self):
        try:
            from google.cloud import vision
            import os
            
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
                self.client = vision.ImageAnnotatorClient()
                self.available = True
            else:
                self.available = False
        except ImportError:
            print("Google Cloud Vision not installed. Install: pip install google-cloud-vision")
            self.available = False
    
    def extract_text_from_image(self, image_content: bytes) -> Dict:
        if not self.available:
            return {
                "raw_text": "Google Cloud Vision not configured",
                "merchant_name": None,
                "amount": None,
                "date": None,
                "confidence": 0.0
            }
        
        try:
            from google.cloud import vision
            
            image = vision.Image(content=image_content)
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            
            if not texts:
                return {
                    "raw_text": "",
                    "merchant_name": None,
                    "amount": None,
                    "date": None,
                    "confidence": 0.0
                }
            
            full_text = texts[0].description
            confidence = texts[0].confidence if hasattr(texts[0], 'confidence') else 0.9
            
            merchant_name = self._extract_merchant_name(full_text)
            amount = self._extract_amount(full_text)
            date = self._extract_date(full_text)
            
            return {
                "raw_text": full_text,
                "merchant_name": merchant_name,
                "amount": amount,
                "date": date,
                "confidence": round(Decimal(str(confidence)), 2)
            }
        except Exception as e:
            raise Exception(f"Google Cloud Vision OCR failed: {str(e)}")
    
    def _extract_merchant_name(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 2 and not first_line.replace('.', '').isdigit():
                return first_line
        return None
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        amount_patterns = [
            r'(?:TOTAL|Total|AMOUNT|Amount|SUBTOTAL|Subtotal)[:\s]*\$?\s*(\d+[.,]\d{2})',
            r'\$\s*(\d+[.,]\d{2})',
            r'(\d+[.,]\d{2})\s*USD',
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                amount_str = matches[-1].replace(',', '.')
                try:
                    return Decimal(amount_str)
                except:
                    continue
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None


class OCRService:
    """
    Unified OCR service that uses the configured engine
    Default: Tesseract (free and open-source)
    """
    def __init__(self):
        ocr_engine = settings.OCR_ENGINE.lower()
        
        if ocr_engine == "google":
            self.service = GoogleVisionOCRService()
            self.engine_name = "Google Cloud Vision"
        elif ocr_engine == "tesseract":
            self.service = TesseractOCRService()
            self.engine_name = "Tesseract OCR (Free)"
        else:
            # No OCR
            self.service = None
            self.engine_name = "None"
    
    def extract_text_from_image(self, image_content: bytes) -> Dict:
        """Extract text from receipt image using configured OCR engine"""
        if self.service is None:
            return {
                "raw_text": "OCR disabled",
                "merchant_name": None,
                "amount": None,
                "date": None,
                "confidence": 0.0
            }
        
        try:
            result = self.service.extract_text_from_image(image_content)
            print(f"OCR extracted using {self.engine_name}: {len(result.get('raw_text', ''))} characters")
            return result
        except Exception as e:
            print(f"OCR error with {self.engine_name}: {str(e)}")
            return {
                "raw_text": f"OCR failed: {str(e)}",
                "merchant_name": None,
                "amount": None,
                "date": None,
                "confidence": 0.0
            }


# Initialize the OCR service
ocr_service = OCRService()
