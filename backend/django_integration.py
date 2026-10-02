"""
Django ERP Integration Examples

This file contains example code for integrating the Expense Tracker API
with a Django-based ERP system.
"""

import requests
from datetime import date, timedelta
from typing import List, Dict, Optional
import hmac
import hashlib


class ExpenseTrackerClient:
    """
    Python client for Expense Tracker API
    Use this in your Django management commands or views
    """
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        })
    
    def get_approved_expenses(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'json'
    ) -> Dict:
        """
        Fetch approved expenses from the API
        
        Args:
            start_date: Filter expenses from this date
            end_date: Filter expenses until this date
            format: 'json' or 'csv'
        
        Returns:
            Dictionary with 'count' and 'expenses' keys (for JSON)
            or CSV string (for CSV format)
        """
        params = {
            'status': 'approved',
            'format': format
        }
        
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        response = self.session.get(
            f'{self.base_url}/api/v1/expenses/export',
            params=params
        )
        response.raise_for_status()
        
        if format == 'json':
            return response.json()
        else:
            return response.text
    
    def get_expense_by_id(self, expense_id: str) -> Dict:
        """Get a single expense by ID"""
        response = self.session.get(
            f'{self.base_url}/api/v1/expenses/export/{expense_id}'
        )
        response.raise_for_status()
        return response.json()
    
    def get_expenses_batch(self, expense_ids: List[str], format: str = 'json') -> Dict:
        """Get multiple expenses by IDs"""
        params = {
            'expense_ids': ','.join(expense_ids),
            'format': format
        }
        response = self.session.get(
            f'{self.base_url}/api/v1/expenses/export/batch',
            params=params
        )
        response.raise_for_status()
        
        if format == 'json':
            return response.json()
        else:
            return response.text


# ============================================================================
# Django Management Command Example
# ============================================================================

"""
Save this as: yourapp/management/commands/import_expenses.py

Usage:
    python manage.py import_expenses
    python manage.py import_expenses --start-date 2026-10-01
    python manage.py import_expenses --days 7
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Import approved expenses from Expense Tracker API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Import expenses from last N days (default: 30)'
        )
    
    def handle(self, *args, **options):
        # Initialize client
        client = ExpenseTrackerClient(
            base_url=settings.EXPENSE_TRACKER_API_URL,
            api_token=settings.EXPENSE_TRACKER_API_TOKEN
        )
        
        # Determine date range
        if options['start_date']:
            start_date = date.fromisoformat(options['start_date'])
        else:
            start_date = date.today() - timedelta(days=options['days'])
        
        end_date = date.fromisoformat(options['end_date']) if options['end_date'] else date.today()
        
        self.stdout.write(f'Fetching expenses from {start_date} to {end_date}...')
        
        # Fetch expenses
        try:
            result = client.get_approved_expenses(
                start_date=start_date,
                end_date=end_date,
                format='json'
            )
            
            expenses = result['expenses']
            self.stdout.write(f'Found {len(expenses)} approved expenses')
            
            # Import into Django models
            from yourapp.models import Expense, GLAccount, Employee
            
            imported_count = 0
            skipped_count = 0
            
            for exp_data in expenses:
                # Check if already imported
                if Expense.objects.filter(external_id=exp_data['id']).exists():
                    skipped_count += 1
                    continue
                
                # Get or create employee
                employee, _ = Employee.objects.get_or_create(
                    email=exp_data['employee_email'],
                    defaults={'name': exp_data['employee_name']}
                )
                
                # Get GL account
                gl_account = None
                if exp_data['gl_account_code']:
                    gl_account = GLAccount.objects.filter(
                        code=exp_data['gl_account_code']
                    ).first()
                
                # Create expense
                Expense.objects.create(
                    external_id=exp_data['id'],
                    date=exp_data['expense_date'],
                    merchant=exp_data['merchant_name'],
                    description=exp_data['description'],
                    amount=exp_data['amount'],
                    currency=exp_data['currency'],
                    employee=employee,
                    gl_account=gl_account,
                    receipt_url=exp_data['receipt_url'],
                    approved_at=exp_data['approved_at'],
                    notes=exp_data['notes']
                )
                imported_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {imported_count} expenses '
                    f'(skipped {skipped_count} duplicates)'
                )
            )
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'API error: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import error: {str(e)}'))


# ============================================================================
# Django Webhook Receiver Example
# ============================================================================

"""
Add this to your Django views.py for real-time expense notifications
"""

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import hmac
import hashlib


@csrf_exempt
@require_http_methods(["POST"])
def expense_webhook(request):
    """
    Webhook endpoint to receive expense approval notifications
    
    Configure in Expense Tracker backend:
    WEBHOOK_ENABLED=True
    WEBHOOK_URL=https://your-erp.com/api/webhook/expenses
    WEBHOOK_SECRET=your-secret
    
    Add to urls.py:
    path('api/webhook/expenses', views.expense_webhook, name='expense_webhook'),
    """
    
    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature', '')
    webhook_secret = getattr(settings, 'EXPENSE_TRACKER_WEBHOOK_SECRET', '')
    
    if webhook_secret:
        expected_signature = 'sha256=' + hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return HttpResponseBadRequest('Invalid signature')
    
    # Parse webhook payload
    try:
        payload = json.loads(request.body)
        event_type = payload.get('event')
        data = payload.get('data')
        
        if event_type == 'expense.approved':
            # Handle approved expense
            from yourapp.tasks import import_approved_expense
            import_approved_expense.delay(data['id'])
            
            return JsonResponse({'status': 'received', 'event': event_type})
        
        elif event_type == 'expense.rejected':
            # Handle rejected expense if needed
            return JsonResponse({'status': 'received', 'event': event_type})
        
        else:
            return JsonResponse({'status': 'ignored', 'event': event_type})
    
    except Exception as e:
        return HttpResponseBadRequest(f'Error processing webhook: {str(e)}')


# ============================================================================
# Django Settings Configuration
# ============================================================================

"""
Add these to your Django settings.py:

# Expense Tracker API Integration
EXPENSE_TRACKER_API_URL = os.environ.get(
    'EXPENSE_TRACKER_API_URL',
    'http://localhost:8000'
)
EXPENSE_TRACKER_API_TOKEN = os.environ.get('EXPENSE_TRACKER_API_TOKEN', '')
EXPENSE_TRACKER_WEBHOOK_SECRET = os.environ.get('EXPENSE_TRACKER_WEBHOOK_SECRET', '')
"""


# ============================================================================
# Django Model Example
# ============================================================================

"""
Example Django models for storing imported expenses
Save as: yourapp/models.py
"""

from django.db import models


class Employee(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class GLAccount(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Expense(models.Model):
    external_id = models.UUIDField(unique=True, help_text="ID from Expense Tracker")
    date = models.DateField()
    merchant = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    gl_account = models.ForeignKey(
        GLAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    receipt_url = models.URLField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.merchant} - ${self.amount} ({self.date})"
