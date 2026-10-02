# Quick Setup Guide for Beginners

This guide walks you through setting up the Expense Tracker with **zero additional costs** using free Tesseract OCR and your ChatGPT Business subscription.

## What You'll Need

1. **A computer** (Windows, Mac, or Linux)
2. **ChatGPT Business subscription** (for AI features - optional but recommended)
3. **15 minutes** of your time

## Step 1: Install Tesseract OCR (FREE)

Tesseract is free, open-source software that reads text from receipt images.

### Windows

1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer
3. **Important**: Check "Add to PATH" during installation
4. That's it!

### Mac

Open Terminal and run:
```bash
brew install tesseract
```

### Linux

```bash
sudo apt install tesseract-ocr
```

**Verify it worked:**
```bash
tesseract --version
```

You should see version information. If not, see [TESSERACT_SETUP.md](TESSERACT_SETUP.md).

## Step 2: Get Your OpenAI API Key (Optional but Recommended)

If you have ChatGPT Business, Plus, or Pro, you can use the API for AI-powered expense categorization.

1. Go to: https://platform.openai.com/account/api-keys
2. Sign in (same account as your ChatGPT)
3. Click "Create new secret key"
4. Name it "Expense Tracker"
5. **Copy the key** (starts with `sk-...`)
6. **Save it securely** - you can't view it again!

**Cost**: About $1-2 per 100 receipts (very affordable)

**Don't have ChatGPT Business?** That's okay! The system works without it - you'll just categorize expenses manually using dropdowns.

## Step 3: Setup the Backend

### Download the Code

```bash
git clone https://github.com/yourusername/expense-tracker.git
cd expense-tracker/backend
```

### Create Configuration File

Copy the example file:
```bash
cp .env.example .env
```

### Edit Configuration

Open `.env` in a text editor and set these two things:

```env
# REQUIRED: Change this to a long random string
SECRET_KEY=your-random-string-here-make-it-long-and-secure

# OPTIONAL: Add your OpenAI API key if you have ChatGPT Business
OPENAI_API_KEY=sk-your-actual-key-here
```

**To generate a secure SECRET_KEY:**

```bash
# On Mac/Linux
python -c "import secrets; print(secrets.token_urlsafe(32))"

# On Windows PowerShell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste it as your SECRET_KEY.

### Install and Run

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Create admin user
python -c "
from app.core.database import SessionLocal
from app.models import User, UserRole
from app.core.security import get_password_hash

db = SessionLocal()
admin = User(
    email='admin@example.com',
    hashed_password=get_password_hash('admin123'),
    full_name='Admin User',
    role=UserRole.ADMIN
)
db.add(admin)
db.commit()
print('Admin user created!')
print('Email: admin@example.com')
print('Password: admin123')
print('CHANGE THIS PASSWORD AFTER FIRST LOGIN!')
"

# Start the server
uvicorn app.main:app --reload
```

## Step 4: Access the Application

Open your browser and go to:

- **Admin Portal**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs

**Login:**
- Email: `admin@example.com`
- Password: `admin123`

**⚠️ IMPORTANT**: Change this password immediately after logging in!

## Step 5: Test It Out

1. **Upload a receipt** image
2. **Watch the OCR extract text** (using free Tesseract)
3. **See AI suggest a category** (if you added OpenAI key)
4. **Approve the expense**

That's it! You're running a full expense tracking system.

## What You Just Set Up

✅ **Backend API** - FastAPI server at http://localhost:8000
✅ **Admin Portal** - React app for managing expenses
✅ **OCR** - Free Tesseract extracts text from receipts
✅ **AI Categorization** - OpenAI suggests expense categories (if enabled)
✅ **Database** - SQLite stores all your data
✅ **File Storage** - Receipts saved in `uploads/` folder

## Common Issues

### "Tesseract not found"

**Solution**: Install Tesseract (see Step 1) or set the path in `.env`:
```env
# Windows
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe

# Mac
TESSERACT_CMD=/usr/local/bin/tesseract
```

### "Invalid OpenAI API key"

**Solutions**:
1. Double-check you copied the full key (starts with `sk-`)
2. Make sure there are no spaces before/after the key
3. Verify the key at: https://platform.openai.com/account/api-keys
4. If you don't have API access, leave `OPENAI_API_KEY=` empty

### "Port 8000 already in use"

**Solution**: Something else is using port 8000. Either:
1. Stop that program, OR
2. Use a different port:
   ```bash
   uvicorn app.main:app --port 8001
   ```
   Then access at http://localhost:8001

### "Database locked"

**Solution**: Close any other processes accessing the database:
```bash
# Delete lock file
rm expense_tracker.db-journal

# Restart the server
```

## Next Steps

### 1. Create Categories

1. Go to Admin Portal → Categories
2. Add categories like:
   - Meals & Entertainment
   - Travel
   - Office Supplies
   - Fuel
   - etc.

### 2. Setup GL Accounts

1. Go to Admin Portal → GL Accounts
2. Add your accounting codes (e.g., 6100, 6200)
3. Map categories to GL accounts

### 3. Test the Workflow

1. Upload a receipt
2. Review the OCR extraction
3. Confirm or adjust the category
4. Submit for approval
5. Approve as admin

### 4. Integrate with Django ERP

See [Django Integration Guide](django_integration.py) for connecting to your ERP system.

## Costs Breakdown

**What you're paying for:**
- ✅ AWS t3.small: ~$18/month (if deployed to AWS)
- ✅ That's it!

**What's FREE:**
- ✅ Tesseract OCR: $0 (open source)
- ✅ SQLite database: $0 (built-in)
- ✅ Local file storage: $0 (uses disk space)
- ✅ Application itself: $0 (open source)

**What's optional:**
- OpenAI API: ~$1-2 per 100 receipts (included with ChatGPT Business)
- AWS S3: ~$3-5/month for receipt storage (can use local storage instead)
- Google Cloud Vision: ~$15 per 1000 receipts (Tesseract is free alternative)

## Getting Help

1. **Tesseract issues**: See [TESSERACT_SETUP.md](TESSERACT_SETUP.md)
2. **OpenAI setup**: See [OPENAI_SETUP.md](OPENAI_SETUP.md)
3. **Deployment**: See [DEPLOYMENT.md](../DEPLOYMENT.md)
4. **Django integration**: See [django_integration.py](django_integration.py)
5. **API docs**: Visit http://localhost:8000/docs

## Security Notes

**Before deploying to production:**

1. ✅ Change admin password
2. ✅ Use a strong SECRET_KEY
3. ✅ Enable HTTPS
4. ✅ Set firewall rules
5. ✅ Regular backups
6. ✅ Keep software updated

## You're All Set!

You now have a fully functional expense tracking system running with:
- FREE OCR (Tesseract)
- AI categorization (if you have ChatGPT Business)
- Professional admin portal
- Django ERP integration ready
- All for ~$18/month (just the server cost)

Questions? Check the docs or open an issue on GitHub.

Happy expense tracking! 🎉
