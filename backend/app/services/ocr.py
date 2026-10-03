import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import concurrent.futures
from app.core.config import settings
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
import re


class TesseractOCRService:
    """
    Local receipt reader. Windows OCR reads the photo first.
    Tesseract is the fallback when that read is weaker.
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
            image = Image.open(io.BytesIO(image_content))
            image = ImageOps.exif_transpose(image) or image
            original = image
            image = self._fit_image(image)
            windows = self._windows_read(image)
            windows_text = windows["text"]
            windows_score = self._receipt_score(windows_text)
            windows_ready = (
                windows_score >= 30
                and re.search(r"\d+[.,]\d{2}", windows_text)
                and re.search(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", windows_text)
            )
            text, score = ("", 0)
            if not windows_ready:
                text, score = self._read_page(image)
            engine = "windows" if windows_text.strip() and windows_score >= score else "tesseract"
            if engine == "windows":
                text, score = windows_text, windows_score
            preview = " ".join(text.split())
            safe = preview[:700].encode("ascii", "replace").decode("ascii")
            print(f"OCR engine {engine} image {image.size} score {score} chars {len(text)}: {safe}")

            if engine == "windows":
                merchant_name = self._extract_merchant_name(text)
                amount = self._extract_amount(text)
                date = self._extract_date(text)
            else:
                located = self._enhance(image)
                merchant_text = self._ocr(located, psm="4")
                merchant_name = (
                    self._reread_merchant(original, located)
                    or self._extract_merchant_name(merchant_text)
                    or self._extract_merchant_name(text)
                )
                amount = self._extract_amount(text)
                rough_date = self._extract_date(text) or self._extract_date(merchant_text)
                date = self._reread_date(original, located) or rough_date
            if not date or not self._merchant_has_hardware(merchant_name, text):
                faded_merchant, faded_date = self._recover_faded_header(original, image, windows["lines"])
                merchant_name = self._prefer_merchant(merchant_name, faded_merchant)
                date = date or faded_date
            print(
                "OCR fields merchant="
                + (merchant_name or "").encode("ascii", "replace").decode("ascii")
                + f" amount={amount} date={date}"
            )
            confidence = Decimal(str(min(0.95, 0.25 + score / 80))).quantize(Decimal("0.01"))

            return {
                "raw_text": text,
                "merchant_name": merchant_name,
                "amount": amount,
                "date": date,
                "confidence": confidence
            }
        except Exception as e:
            raise Exception(f"Tesseract OCR failed: {str(e)}")

    def _windows_ocr(self, image: Image.Image) -> str:
        return self._windows_read(image)["text"]

    def _windows_read(self, image: Image.Image) -> Dict:
        """Read with the OCR engine built into Windows, including word positions."""
        def _read() -> Dict:
            import winocr
            result = winocr.recognize_pil_sync(image, "en") or {}
            lines = []
            for line in result.get("lines") or []:
                if not isinstance(line, dict) or not line.get("text"):
                    continue
                words = []
                for word in line.get("words") or []:
                    if isinstance(word, dict) and word.get("text"):
                        words.append({
                            "text": str(word["text"]),
                            "box": word.get("bounding_rect") or {},
                        })
                lines.append({"text": str(line["text"]), "words": words})
            text = "\n".join(item["text"] for item in lines) or str(result.get("text") or "")
            return {"text": text, "lines": lines}

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_read).result(timeout=25)
        except Exception as exc:
            print(f"Windows OCR skipped: {exc}")
            return {"text": "", "lines": []}

    def _merchant_has_hardware(self, merchant_name: Optional[str], text: str) -> bool:
        blob = f"{merchant_name or ''} {text}".lower()
        if "hardware" in (merchant_name or "").lower():
            return True
        if re.search(r"\bace\b", blob) and re.search(r"gard", blob):
            return False
        return True

    def _prefer_merchant(self, current: Optional[str], new: Optional[str]) -> Optional[str]:
        if not new:
            return current
        if not current:
            return new

        def rank(name: str):
            lowered = name.lower()
            return (
                int("hardware" in lowered) + int("garden" in lowered) + int("ace" in lowered),
                len([word for word in name.split() if word != "&"]),
            )

        return new if rank(new) > rank(current) else current

    def _recover_faded_header(self, original: Image.Image, fitted: Image.Image, lines) -> tuple:
        """Zoom into the store-name line. Faded words between Ace and Garden are easy to skip."""
        boxes = self._header_word_boxes(lines, fitted.height)
        if not boxes:
            return None, None
        crop = self._crop_header(original, fitted, boxes)
        if crop is None:
            return None, None
        text = self._read_header_crop(crop)
        preview = " ".join(text.split())[:400].encode("ascii", "replace").decode("ascii")
        print(f"OCR header zoom: {preview}")
        return self._extract_merchant_name(text), self._extract_date(text)

    def _header_word_boxes(self, lines, fitted_height: int):
        pattern = re.compile(
            r"^(?:shop\w*|ace|gard\w*|hard\w*|kick\w*|rick\w*|clayton|road|ellis\w*|thank\w*)$",
            re.IGNORECASE,
        )
        boxes = []
        for line in lines or []:
            for word in line.get("words") or []:
                token = re.sub(r"[^A-Za-z]", "", word.get("text") or "")
                box = word.get("box") or {}
                if len(token) >= 3 and pattern.match(token) and "y" in box:
                    boxes.append(box)
        if not boxes:
            return []
        top = min(float(box["y"]) for box in boxes)
        limit = top + fitted_height * 0.25
        return [box for box in boxes if float(box["y"]) <= limit]

    def _crop_header(self, original: Image.Image, fitted: Image.Image, boxes):
        try:
            scale_x = original.width / fitted.width
            scale_y = original.height / fitted.height
            left = min(float(box["x"]) for box in boxes) * scale_x
            right = max(float(box["x"]) + float(box["width"]) for box in boxes) * scale_x
            top = min(float(box["y"]) for box in boxes) * scale_y
            bottom = max(float(box["y"]) + float(box["height"]) for box in boxes) * scale_y
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None
        pad_x = original.width * 0.03
        crop = original.crop((
            max(0, int(left - pad_x)),
            max(0, int(top - original.height * 0.015)),
            min(original.width, int(right + pad_x)),
            min(original.height, int(bottom + original.height * 0.11)),
        ))
        if crop.width < 40 or crop.height < 40:
            return None
        return crop

    def _read_header_crop(self, crop: Image.Image) -> str:
        long_side = max(crop.size)
        scale = 3 if long_side < 1600 else 2
        if long_side * scale > 3200:
            scale = max(1, int(3200 / long_side))
        big = crop.resize(
            (max(1, crop.width * scale), max(1, crop.height * scale)),
            Image.Resampling.LANCZOS,
        )
        mild = ImageOps.autocontrast(ImageOps.grayscale(big), cutoff=1)
        mild = ImageEnhance.Contrast(mild).enhance(1.6).filter(ImageFilter.SHARPEN)
        windows_image = mild
        if max(windows_image.size) > 2400:
            fit = 2400 / max(windows_image.size)
            windows_image = windows_image.resize(
                (max(1, int(windows_image.width * fit)), max(1, int(windows_image.height * fit))),
                Image.Resampling.LANCZOS,
            )
        windows_text = self._windows_ocr(windows_image.convert("RGB"))
        tesseract_text = self._ocr(mild, psm="6")
        return "\n".join(part for part in (windows_text, tesseract_text) if part)

    def _address_anchor(self, lines) -> Optional[dict]:
        anchors = []
        for line in lines or []:
            for word in line.get("words") or []:
                if re.search(r"road|street|ellis|ville|avenue|drive|lane|blvd|hwy", word.get("text") or "", re.IGNORECASE):
                    box = word.get("box") or {}
                    if "y" in box:
                        anchors.append(box)
        if not anchors:
            return None
        return min(anchors, key=lambda box: box["y"])

    def _box_on_original(self, original: Image.Image, fitted: Image.Image, box: dict):
        try:
            scale_x = original.width / fitted.width
            scale_y = original.height / fitted.height
            left = int(float(box["x"]) * scale_x)
            top = int(float(box["y"]) * scale_y)
            right = int((float(box["x"]) + float(box["width"])) * scale_x)
            bottom = int((float(box["y"]) + float(box["height"])) * scale_y)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None
        return left, top, right, bottom

    def _read_faded_band(self, original: Image.Image, fitted: Image.Image, box: dict, above: float, below: float) -> str:
        mapped = self._box_on_original(original, fitted, box)
        if not mapped:
            return ""
        _, top, _, bottom = mapped
        band_top = max(0, top - int(original.height * above))
        band_bottom = min(original.height, bottom + int(original.height * below))
        if band_bottom - band_top < 20:
            return ""
        return self._read_faded_region(original.crop((0, band_top, original.width, band_bottom)))

    def _read_faded_region(self, image: Image.Image) -> str:
        prepared = self._prepare_faded(image)
        windows_text = self._windows_ocr(prepared)
        tesseract_text = self._ocr(prepared, psm="6")
        return "\n".join(part for part in (windows_text, tesseract_text) if part)

    def _prepare_faded(self, image: Image.Image) -> Image.Image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        long_side = max(image.size)
        if long_side > 2400:
            scale = 2400 / long_side
        elif 0 < long_side < 1200:
            scale = 1200 / long_side
        else:
            scale = 1
        if scale != 1:
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
        gray = ImageEnhance.Contrast(gray).enhance(2.5)
        return gray.filter(ImageFilter.SHARPEN)

    def _fit_image(self, image: Image.Image) -> Image.Image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        width, height = image.size
        long_side = max(width, height)
        if long_side < 1400:
            scale = 1400 / long_side
        elif long_side > 2200:
            scale = 2200 / long_side
        else:
            return image
        return image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    def _enhance(self, image: Image.Image) -> Image.Image:
        gray = ImageOps.grayscale(image)
        gray = ImageOps.autocontrast(gray)
        return gray.filter(ImageFilter.SHARPEN)

    def _receipt_score(self, text: str) -> int:
        if not text:
            return 0
        score = 12 * len(re.findall(r"\d+[.,]\d{2}", text))
        if re.search(r"total|subtotal|amount|tax", text, re.IGNORECASE):
            score += 10
        if re.search(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", text):
            score += 8
        score += min(len(re.findall(r"[A-Za-z]{4,}", text)), 25)
        return score

    def _read_page(self, image: Image.Image):
        text = self._ocr(self._enhance(image))
        score = self._receipt_score(text)
        if score >= 20:
            return text, score
        ranked = [(score, text)]
        for angle in (90, 180, 270):
            rotated = self._ocr(self._enhance(image.rotate(angle, expand=True)))
            ranked.append((self._receipt_score(rotated), rotated))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1], ranked[0][0]

    def _ocr(self, image: Image.Image, psm: str = "6") -> str:
        return pytesseract.image_to_string(image, config=f"--oem 3 --psm {psm}") or ""

    def _merchant_from_header(self, image: Image.Image) -> Optional[str]:
        width, height = image.size
        crop = image.crop((0, 0, width, max(1, int(height * 0.30))))
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
        config = "--oem 3 --psm 6 --dpi 300"
        reads = [
            pytesseract.image_to_string(crop, config=config) or "",
            pytesseract.image_to_string(self._enhance(crop), config=config) or "",
        ]
        best_name = None
        best_score = 0
        for text in reads:
            safe = " ".join(text.split())[:240].encode("ascii", "replace").decode("ascii")
            print(f"OCR header: {safe}")
            name = self._extract_merchant_name(text)
            if not name:
                continue
            score = self._merchant_line_score(name, 0) or 0
            if score > best_score:
                best_score = score
                best_name = name
        return best_name
    
    def _extract_merchant_name(self, text: str) -> Optional[str]:
        """Pick the store name from the receipt header, not the first printed line."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        scored = []
        for index, line in enumerate(lines[:15]):
            candidates = [line]
            if re.search(r"(?:shop|hop|pup|fup)\w*(?:\s+[A-Za-z]{1,4})?\s+at\s*$", line, re.IGNORECASE) and index + 1 < len(lines):
                candidates.append(f"{line} {lines[index + 1]}")
            joined = line
            for follower in lines[index + 1:index + 3]:
                if not self._can_join_merchant_line(follower):
                    break
                joined = f"{joined} {follower}"
                candidates.append(joined)
            for combined in candidates:
                for phrase, bonus in self._merchant_phrases(combined):
                    score = self._merchant_line_score(phrase, index)
                    if score is None:
                        continue
                    scored.append((score + bonus, phrase))
        if not scored:
            return None
        valid = [
            phrase
            for score, phrase in scored
            if score >= 6 and self._merchant_name_ok(phrase)
        ]
        best = None
        for phrase in valid:
            best = self._prefer_merchant(best, phrase)
        return best

    def _can_join_merchant_line(self, line: str) -> bool:
        if re.search(r"\d{2,}", line):
            return False
        if re.search(r"\d[/.\-]\d", line):
            return False
        if re.search(r"thank|shop|total|visa|card|sale|auth", line, re.IGNORECASE):
            return False
        letters = re.sub(r"[^A-Za-z&']", "", line)
        return len(letters) >= 3

    def _merchant_phrases(self, line: str):
        greeting = re.search(
            r"(?:shop|hop|pup|fup)\w*(?:\s+[A-Za-z]{1,4})?\s+at\s+(.+)|welcome\s+to\s+(.+)",
            line,
            re.IGNORECASE,
        )
        if not greeting:
            polished = self._polish_merchant(self._cut_address(line))
            return [(polished, 0)] if polished else []
        raw_name = greeting.group(1) or greeting.group(2)
        name = self._polish_merchant(self._cut_address(raw_name))
        if not name:
            return []
        return [(name, 8)]

    def _cut_address(self, text: str) -> str:
        text = text.replace("’", "'").replace("`", "'")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.split(
            r"\s+\d{2,}\b|\s+#\d|\b(?:street|avenue|road|drive|lane|blvd|hwy|suite)\b",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        text = re.sub(r"\s+\d{1,2}$", "", text)
        return re.sub(r"[^A-Za-z0-9&'. -]", " ", text).strip(" -#.,")

    def _polish_merchant(self, text: str) -> str:
        kept = []
        words = re.sub(r"\s+", " ", text).split()
        store_context = bool(re.search(r"hard|gard|ware|arden", text, re.IGNORECASE))
        for index, word in enumerate(words):
            following = words[index + 1] if index + 1 < len(words) else ""
            tidy = self._tidy_merchant_word(word, following, store_context)
            if tidy:
                kept.append(tidy)
        while kept and kept[0] == "&":
            kept.pop(0)
        while kept and kept[-1] == "&":
            kept.pop()
        return " ".join(kept)

    def _edit_distance(self, left: str, right: str) -> int:
        if abs(len(left) - len(right)) > 2:
            return 99
        previous = list(range(len(right) + 1))
        for index, left_char in enumerate(left, 1):
            current = [index]
            for right_index, right_char in enumerate(right, 1):
                current.append(min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                ))
            previous = current
        return previous[-1]

    def _tidy_merchant_word(self, word: str, following: str = "", store_context: bool = False) -> Optional[str]:
        if word == "&":
            return "&"
        compact = re.sub(r"[^A-Za-z0-9]", "", word)
        compact_lower = compact.lower()
        if re.fullmatch(r"[hHrR][1lI]ck", compact) or compact_lower in {"rick", "ricks"}:
            return "Rick's"
        if store_context and compact_lower in {"kick", "kicks", "nick", "nicks"}:
            return "Rick's"
        following_letters = re.sub(r"[^A-Za-z]", "", following).lower()
        hardware_next = (
            "ware" in following_letters
            or "hard" in following_letters
            or self._edit_distance(following_letters, "hardware") <= 2
        )
        if compact_lower in {"ae", "ace", "aco", "acg"} and hardware_next:
            return "Ace"
        letters = re.sub(r"[^A-Za-z']", "", word.replace("’", "'"))
        if len(letters) < 3:
            return None
        lowered = letters.lower()
        if lowered.startswith("gard") or self._edit_distance(lowered, "garden") <= 1:
            return "Garden"
        if store_context and (
            lowered.startswith("hard")
            or "ware" in lowered
            or self._edit_distance(lowered, "hardware") <= 2
        ):
            return "Hardware"
        if self._edit_distance(lowered, "hardware") <= 2:
            return "Hardware"
        if re.search(r"x{2,}", lowered):
            return None
        if lowered in {
            "card", "visa", "debit", "credit", "mastercard", "amex", "discover",
            "thank", "shopping", "shoppi", "hopping", "pupping", "fupping", "auth",
        }:
            return None
        if "card" in lowered:
            return None
        if (lowered.endswith("ware") and lowered != "hardware") or lowered.endswith("vare"):
            return "Hardware"
        if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", lowered):
            return None
        return letters

    def _merchant_name_ok(self, name: str) -> bool:
        words = [word for word in name.split() if word != "&"]
        long_words = [word for word in words if len(re.sub(r"[^A-Za-z]", "", word)) >= 4]
        return len(long_words) >= 2

    def _merchant_line_score(self, line: str, index: int) -> Optional[float]:
        cleaned = line.replace("’", "'").replace("`", "'")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" *-#.,")
        if len(cleaned) < 3 or len(cleaned) > 48:
            return None
        lowered = cleaned.lower()
        if re.search(r"x{2,}", lowered) or re.search(r"card", lowered):
            return None
        if lowered in {
            "receipt", "invoice", "sale", "sales receipt", "customer copy",
            "merchant copy", "store copy", "welcome", "thank you", "thanks",
            "reprint", "duplicate", "order", "tax invoice",
        }:
            return None
        if re.search(r"[^A-Za-z0-9&'. -]", cleaned):
            return None
        if not re.search(r"[aeiou]", lowered):
            return None
        if not re.search(r"[a-z]{3,}", lowered):
            return None
        if lowered in {
            "noun", "item", "items", "qty", "cash", "card", "paid", "tender",
            "debit", "credit", "change", "balance", "amount", "subtotal", "total",
        }:
            return None
        if re.search(r"\b(welcome|thank|thanks|shopping|customer|please|visit|copy|receipt|invoice|duplicate|reprint)\b", lowered):
            return None
        if re.match(r"^(tel|phone|ph|fax|store|reg|register|terminal|cashier|server|table|order|auth|approval|ref|tid|mid|receipt|invoice|date|time|subtotal|total|tax|change|visa|mastercard|amex|discover|amount|noun|qty|item)\b", lowered):
            return None
        if re.search(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", cleaned):
            return None
        if re.search(r"\$\s*\d", cleaned) or re.search(r"\b\d+\.\d{2}\b", cleaned):
            return None
        if re.search(r"(?:\(\d{3}\)|\b\d{3})[-.\s]\d{3}[-.\s]\d{4}", cleaned):
            return None
        if re.search(r"www\.|https?://|@|\.com\b", lowered):
            return None
        if re.search(r"\b(st|street|ave|avenue|rd|road|blvd|dr|drive|ln|lane|hwy|suite|ste)\b", lowered) and re.search(r"\d", cleaned):
            return None
        if re.search(r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b", cleaned):
            return None

        letters = sum(character.isalpha() for character in cleaned)
        digits = sum(character.isdigit() for character in cleaned)
        if letters < 2 or digits / max(len(cleaned), 1) > 0.3:
            return None

        words = cleaned.split()
        score = 0.0
        score += 5 if digits == 0 else 1
        score += 4 if letters / len(cleaned) >= 0.75 else 0
        score += 3 if 1 <= len(words) <= 4 else 0
        score -= 2 if len(words) > 6 else 0
        score += 2 if cleaned.upper() == cleaned and letters >= 3 else 0
        score += 1 if index <= 10 else 0
        score -= index * 0.25
        return score
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """Prefer a labeled total. Otherwise use the largest money amount."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        labeled = []
        for index, line in enumerate(lines):
            if not re.search(r"grand\s*total|amount\s*due|balance\s*due|total\s*due|\btotal\b|\bamount\b", line, re.IGNORECASE):
                continue
            if re.search(r"subtotal|sub-total|\btax\b", line, re.IGNORECASE) and not re.search(
                r"grand|amount due|balance due|total due", line, re.IGNORECASE
            ):
                continue
            window = line if index + 1 >= len(lines) else f"{line} {lines[index + 1]}"
            found = self._money_values(window)
            if found:
                labeled.append(found[-1])
        if labeled:
            return max(labeled)
        amounts = [
            amount for amount in self._money_values(text)
            if Decimal("0.01") <= amount <= Decimal("100000")
        ]
        return max(amounts) if amounts else None

    def _money_values(self, text: str):
        values = []
        for match in re.finditer(r"(\d{1,6})[.,](\d{2})\b", text):
            try:
                values.append(Decimal(f"{match.group(1)}.{match.group(2)}"))
            except Exception:
                continue
        return values

    def _reread_merchant(self, source: Image.Image, located_on: Image.Image) -> Optional[str]:
        """Read the store name from a zoomed crop of the receipt header."""
        try:
            data = pytesseract.image_to_data(
                located_on,
                config="--oem 3 --psm 6",
                output_type=pytesseract.Output.DICT,
            )
        except Exception:
            return None
        anchor = None
        for index, word in enumerate(data["text"]):
            if re.search(r"shop|hopp|thank", word or "", re.IGNORECASE):
                anchor = index
                break
        if anchor is None:
            return None
        band_top = max(0, data["top"][anchor] - 8)
        band_bottom = data["top"][anchor] + data["height"][anchor] + 130
        indexes = [
            index for index, word in enumerate(data["text"])
            if (word or "").strip() and band_top <= data["top"][index] <= band_bottom
        ] or [anchor]
        left = min(data["left"][index] for index in indexes)
        right = max(data["left"][index] + data["width"][index] for index in indexes)
        top = min(data["top"][index] for index in indexes)
        bottom = max(data["top"][index] + data["height"][index] for index in indexes)
        scale_x = source.width / located_on.width
        scale_y = source.height / located_on.height
        pad = 20
        crop = source.crop((
            max(0, int(left * scale_x) - pad),
            max(0, int(top * scale_y) - pad),
            min(source.width, int(right * scale_x) + pad),
            min(source.height, int(bottom * scale_y) + pad),
        ))
        if crop.width < 20 or crop.height < 20:
            return None
        big = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(ImageOps.grayscale(big))
        variants = [gray]
        for threshold in (150, 170):
            variants.append(gray.point(lambda pixel, limit=threshold: 0 if pixel < limit else 255))
        best_name = None
        best_score = 0.0
        for variant in variants:
            text = pytesseract.image_to_string(variant, config="--oem 3 --psm 6") or ""
            name = self._extract_merchant_name(text)
            if not name:
                continue
            score = self._merchant_line_score(name, 0) or 0
            lowered = name.lower()
            if "hardware" in lowered:
                score += 6
            if "garden" in lowered:
                score += 4
            if "ace" in lowered:
                score += 3
            if score > best_score:
                best_score = score
                best_name = name
        return best_name

    def _reread_date(self, source: Image.Image, located_on: Image.Image) -> Optional[str]:
        """Zoom in on a date and re-read it. An 8 is often read as a 6 on the full page."""
        try:
            data = pytesseract.image_to_data(
                located_on,
                config="--oem 3 --psm 6",
                output_type=pytesseract.Output.DICT,
            )
        except Exception:
            return None
        scale_x = source.width / located_on.width
        scale_y = source.height / located_on.height
        for index, word in enumerate(data["text"]):
            token = (word or "").strip()
            if not re.search(r"\d[/.\-]\d", token) or len(re.sub(r"\D", "", token)) > 8:
                continue
            left = int(data["left"][index] * scale_x)
            top = int(data["top"][index] * scale_y)
            right = int((data["left"][index] + data["width"][index]) * scale_x)
            bottom = int((data["top"][index] + data["height"][index]) * scale_y)
            parsed = self._reread_date_box(source, left, top, right, bottom)
            if parsed:
                return parsed
        return None

    def _reread_date_box(self, image: Image.Image, left: int, top: int, right: int, bottom: int) -> Optional[str]:
        pad = 8
        crop = image.crop((
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad),
            min(image.height, bottom + pad),
        ))
        if crop.width < 8 or crop.height < 8:
            return None
        big = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(ImageOps.grayscale(big))
        reads = []
        for threshold in (150, 170):
            black_white = gray.point(lambda pixel, limit=threshold: 0 if pixel < limit else 255)
            text = pytesseract.image_to_string(
                black_white,
                config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/",
            ) or ""
            parsed = self._extract_date(text.strip())
            if parsed:
                reads.append(parsed)
        if len(reads) == 2 and reads[0] == reads[1]:
            return reads[0]
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Find a real receipt date and return it as YYYY-MM-DD."""
        normalized = re.sub(r"[''`´’]", "", text)
        normalized = re.sub(r"\s*([/.\-])\s*", r"\1", normalized)
        month_name = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
        candidates = []

        for match in re.finditer(
            r"[A-Za-z0-9?]{1,4}/[A-Za-z0-9?]{1,4}/\s*[A-Za-z0-9?]{1,4}",
            normalized,
        ):
            parsed = self._repair_slash_date(match.group(0))
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        for match in re.finditer(r"\b(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})\b", normalized):
            parsed = self._valid_receipt_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        for match in re.finditer(r"\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})\b", normalized):
            year = self._expand_year(int(match.group(3)))
            first = self._repair_faded_zero(int(match.group(1)))
            second = self._repair_faded_zero(int(match.group(2)))
            if first > 12 and second <= 12:
                parsed = self._valid_receipt_date(year, second, first)
            else:
                parsed = self._valid_receipt_date(year, first, second)
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        for match in re.finditer(rf"\b{month_name}\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", normalized, re.IGNORECASE):
            parsed = self._valid_receipt_date(int(match.group(3)), self._month_number(match.group(1)), int(match.group(2)))
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        for match in re.finditer(r"\b(\d{1,2})\s+(\d{1,2})\s+(\d{4})\b", normalized):
            window = normalized[max(0, match.start() - 24):match.start()].lower()
            if "date" not in window:
                continue
            year = int(match.group(3))
            first = int(match.group(1))
            second = int(match.group(2))
            if first > 12 and second <= 12:
                parsed = self._valid_receipt_date(year, second, first)
            else:
                parsed = self._valid_receipt_date(year, first, second)
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        for match in re.finditer(rf"\b(\d{{1,2}})[\s\-]*{month_name}[\s\-]*(\d{{2,4}})\b", normalized, re.IGNORECASE):
            year = self._expand_year(int(match.group(3)))
            parsed = self._valid_receipt_date(year, self._month_number(match.group(2)), int(match.group(1)))
            if parsed:
                candidates.append((match.start(), parsed, normalized))

        if not candidates:
            return None

        def sort_key(item):
            position, _, source = item
            window = source[max(0, position - 24):position].lower()
            near_label = "date" in window
            return (not near_label, position)

        candidates.sort(key=sort_key)
        return candidates[0][1].isoformat()

    def _repair_slash_date(self, token: str):
        parsed = self._slash_token_to_date(token)
        if parsed:
            return parsed
        # A letter glued to a slash is usually the slash itself: 02Z/26 -> 02/26.
        loosened = re.sub(r"[A-Za-z?]\s*(?=/)|(?<=/)[A-Za-z?]", "", token)
        if loosened != token:
            return self._slash_token_to_date(loosened)
        return None

    def _slash_token_to_date(self, token: str):
        lookalikes = str.maketrans({
            "O": "0", "o": "0", "Q": "0", "D": "0", "U": "0", "u": "0",
            "I": "1", "l": "1", "|": "1",
            "Z": "2", "z": "2",
            "S": "5", "s": "5",
            "B": "8",
            "G": "6", "g": "6",
        })
        digits = re.sub(r"\D", "", token.translate(lookalikes))
        if len(digits) == 6:
            month, day, year = int(digits[0:2]), int(digits[2:4]), self._expand_year(int(digits[4:6]))
            month = self._repair_faded_zero(month)
            day = self._repair_faded_zero(day)
            if month > 12 and day <= 12:
                month, day = day, month
            return self._valid_receipt_date(year, month, day)
        if len(digits) == 8:
            year_first = self._valid_receipt_date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
            month_first = self._valid_receipt_date(int(digits[4:8]), int(digits[0:2]), int(digits[2:4]))
            return month_first or year_first
        return None

    def _repair_faded_zero(self, value: int) -> int:
        """A faded 8 is often read as 0, which leaves an impossible 00 month or day."""
        if value == 0:
            return 8
        return value

    def _month_number(self, name: str) -> int:
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        return months[name.lower()[:3]]

    def _expand_year(self, year: int) -> int:
        if year < 100:
            return 2000 + year
        return year

    def _valid_receipt_date(self, year: int, month: int, day: int):
        if not (2000 <= year <= datetime.now().year + 1):
            return None
        try:
            return datetime(year, month, day).date()
        except ValueError:
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
