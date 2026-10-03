from openai import OpenAI
from app.core.config import settings
from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime
import base64
import io
import json
import re


class AIService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.enabled = True
            print("OpenAI API configured.")
        else:
            self.enabled = False
            print("OpenAI API key not set. Receipts are matched to expense account names.")
            print("  To enable: Add OPENAI_API_KEY to .env file")
            print("  Get key from: https://platform.openai.com/account/api-keys")
    
    def read_receipt(self, image_content: bytes, categories: List[Dict]) -> Optional[Dict]:
        """Read the receipt photo and return the merchant, total, date, and expense account."""
        if not self.enabled:
            return None
        try:
            from PIL import Image, ImageOps

            image = Image.open(io.BytesIO(image_content))
            image = ImageOps.exif_transpose(image) or image
            if image.mode != "RGB":
                image = image.convert("RGB")
            long_side = max(image.size)
            if long_side > 2048:
                scale = 2048 / long_side
                image = image.resize(
                    (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            account_lines = "\n".join(
                f"- {cat['name']}: {cat.get('description') or 'No description'}"
                for cat in categories
            ) or "- none"
            prompt = f"""Read this receipt photo and extract the purchase fields.
The total is the final amount paid, not the subtotal or tax.
Dates on US receipts are month/day/year.
Choose an expense account only when one of these accounts fits. Otherwise use null.

Expense accounts:
{account_lines}

Respond with ONLY JSON:
{{
  "merchant_name": "store name or null",
  "amount": 15.00,
  "date": "YYYY-MM-DD or null",
  "category_name": "exact account name or null",
  "confidence": 0.9
}}"""
            result = None
            last_error = None
            for model in ("gpt-4.1", "gpt-4o"):
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        temperature=0,
                        max_tokens=300,
                        response_format={"type": "json_object"},
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                            ],
                        }],
                    )
                    result = json.loads(response.choices[0].message.content or "{}")
                    print(f"OpenAI receipt read with {model}")
                    break
                except Exception as exc:
                    last_error = exc
                    if "model" not in str(exc).lower():
                        raise
            if result is None:
                raise last_error or Exception("OpenAI receipt read failed")

            merchant = result.get("merchant_name")
            merchant = merchant.strip() if isinstance(merchant, str) and merchant.strip() else None
            amount = None
            if result.get("amount") not in (None, ""):
                parsed_amount = Decimal(str(result["amount"])).quantize(Decimal("0.01"))
                if parsed_amount > 0:
                    amount = parsed_amount
            date = None
            raw_date = result.get("date")
            if isinstance(raw_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date.strip()):
                datetime.strptime(raw_date.strip(), "%Y-%m-%d")
                date = raw_date.strip()
            category_name = result.get("category_name")
            category = None
            if isinstance(category_name, str):
                category = next(
                    (cat for cat in categories if cat["name"].lower() == category_name.strip().lower()),
                    None,
                )
            confidence = Decimal(str(result.get("confidence") or "0.8"))
            if confidence < 0 or confidence > 1:
                confidence = Decimal("0.8")
            print(f"OpenAI fields merchant={merchant} amount={amount} date={date}")
            suggestion = None
            if category:
                suggestion = {
                    "category_id": str(category["id"]),
                    "category_name": category["name"],
                    "confidence": confidence,
                    "reasoning": "Chosen from the receipt photo.",
                }
            return {
                "merchant_name": merchant,
                "amount": amount,
                "date": date,
                "confidence": confidence,
                "raw_text": "Read from the receipt photo.",
                "category": suggestion,
            }
        except Exception as exc:
            safe = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-redacted", str(exc))
            print(f"OpenAI receipt read failed: {safe}")
            return None

    def categorize_expense(
        self,
        ocr_text: str,
        merchant_name: Optional[str],
        amount: Optional[Decimal],
        categories: List[Dict]
    ) -> Optional[Dict]:
        if not self.enabled:
            return None
        
        try:
            categories_text = "\n".join([
                f"- {cat['name']}: {cat.get('description', 'No description')}"
                for cat in categories
            ])
            
            prompt = f"""Categorize this expense based on the receipt information.

Receipt Text: {ocr_text[:500]}
Merchant: {merchant_name or 'Unknown'}
Amount: ${amount or 'Unknown'}

Available Categories:
{categories_text}

Respond with ONLY a valid JSON object in this exact format (no markdown, no explanation):
{{
    "category_name": "exact category name from list",
    "confidence": 0.85,
    "reasoning": "brief explanation"
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expense categorization assistant. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            # Find matching category
            category = next(
                (cat for cat in categories if cat['name'].lower() == result['category_name'].lower()),
                None
            )
            
            if category:
                return {
                    "category_id": str(category['id']),
                    "category_name": category['name'],
                    "confidence": Decimal(str(result['confidence'])),
                    "reasoning": result['reasoning']
                }
            
            return None
            
        except Exception as e:
            print(f"AI categorization failed: {str(e)}")
            if "invalid_api_key" in str(e).lower():
                print("ERROR: Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env")
                print("Get your API key from: https://platform.openai.com/account/api-keys")
            return None

    def choose_category(
        self,
        ocr_text: str,
        merchant_name: Optional[str],
        amount: Optional[Decimal],
        categories: List[Dict]
    ) -> Optional[Dict]:
        if self.enabled:
            suggestion = self.categorize_expense(ocr_text, merchant_name, amount, categories)
            if suggestion:
                return suggestion
        return self.match_category(ocr_text, merchant_name, categories)

    def match_category(
        self,
        ocr_text: str,
        merchant_name: Optional[str],
        categories: List[Dict]
    ) -> Optional[Dict]:
        haystack = f"{merchant_name or ''} {ocr_text}".lower()
        ignored = {
            "the", "and", "for", "with", "from", "this", "that", "are", "was",
            "expense", "account", "accounts", "general", "other", "misc",
            "miscellaneous", "store", "receipt", "purchase", "purchases",
            "service", "services", "item", "items",
        }
        best = None
        best_score = 0
        for category in categories:
            name = category["name"].lower().strip()
            description = (category.get("description") or "").lower()
            score = 0
            if len(name) >= 3 and re.search(rf"\b{re.escape(name)}\b", haystack):
                score += 10
            for word in re.findall(r"[a-z]{4,}", f"{name} {description}"):
                if word in ignored:
                    continue
                if re.search(rf"\b{re.escape(word)}\b", haystack):
                    score += 4
            if score > best_score:
                best_score = score
                best = category
        if not best or best_score < 4:
            return None
        return {
            "category_id": str(best["id"]),
            "category_name": best["name"],
            "confidence": Decimal("0.6"),
            "reasoning": "Matched the receipt text to this expense account.",
        }
    
    def suggest_gl_account(
        self,
        expense_description: str,
        category_name: str,
        merchant_name: Optional[str],
        gl_accounts: List[Dict]
    ) -> Optional[Dict]:
        if not self.enabled or not gl_accounts:
            return None
        
        try:
            gl_accounts_text = "\n".join([
                f"- {acc['account_code']}: {acc['account_name']}"
                for acc in gl_accounts
            ])
            
            prompt = f"""Suggest the most appropriate GL account for this expense.

Expense Description: {expense_description}
Category: {category_name}
Merchant: {merchant_name or 'Unknown'}

Available GL Accounts:
{gl_accounts_text}

Respond with ONLY a valid JSON object:
{{
    "account_code": "exact code from list",
    "confidence": 0.90,
    "reasoning": "brief explanation"
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a GL account mapping assistant. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            gl_account = next(
                (acc for acc in gl_accounts if acc['account_code'] == result['account_code']),
                None
            )
            
            if gl_account:
                return {
                    "gl_account_id": str(gl_account['id']),
                    "account_code": gl_account['account_code'],
                    "confidence": Decimal(str(result['confidence'])),
                    "reasoning": result['reasoning']
                }
            
            return None
            
        except Exception as e:
            print(f"GL account suggestion failed: {str(e)}")
            return None


ai_service = AIService()
