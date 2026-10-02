from openai import OpenAI
from app.core.config import settings
from typing import Optional, Dict, List
from decimal import Decimal
import json


class AIService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.enabled = True
            print("✓ OpenAI API configured (using ChatGPT Business key)")
        else:
            self.enabled = False
            print("⚠ OpenAI API key not set. AI categorization disabled.")
            print("  To enable: Add OPENAI_API_KEY to .env file")
            print("  Get key from: https://platform.openai.com/account/api-keys")
    
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
