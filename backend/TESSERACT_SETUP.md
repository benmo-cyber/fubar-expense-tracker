# Tesseract OCR Setup Guide

Tesseract is a **free and open-source** OCR engine that extracts text from receipt images with no API costs.

## Why Tesseract?

- ✅ **100% Free** - No API costs ever
- ✅ **Open Source** - No vendor lock-in
- ✅ **Runs Locally** - No internet required
- ✅ **Good Accuracy** - Works well for receipts
- ✅ **Privacy** - Receipt data stays on your server

## Installation

### Windows

**Option 1: Official Installer (Recommended)**

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (`tesseract-ocr-w64-setup-v5.3.3.exe`)
3. **Important**: Check "Add to PATH" during installation
4. Default install location: `C:\Program Files\Tesseract-OCR`

**Option 2: Chocolatey**

```powershell
choco install tesseract
```

**Verify Installation:**

```cmd
tesseract --version
```

**If PATH not set:**

```env
# In your .env file
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### macOS

**Using Homebrew (Recommended):**

```bash
brew install tesseract
```

**Verify:**

```bash
tesseract --version
which tesseract  # Should show: /usr/local/bin/tesseract
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install tesseract-ocr
```

**For RHEL/CentOS/Amazon Linux:**

```bash
sudo yum install epel-release
sudo yum install tesseract
```

**Verify:**

```bash
tesseract --version
which tesseract  # Should show: /usr/bin/tesseract
```

## Configuration

In your `.env` file:

```env
# Use Tesseract (free OCR)
OCR_ENGINE=tesseract

# Path to tesseract executable (optional - auto-detects if empty)
TESSERACT_CMD=
```

**Only set `TESSERACT_CMD` if:**
- Tesseract is not in your PATH
- You get "Tesseract not found" errors
- You have multiple versions installed

## Testing Tesseract

Test that it's working:

```bash
# Create a test image with text
echo "Test Receipt" > test.txt

# Convert to image (requires ImageMagick)
convert -pointsize 48 label:"Test Receipt\nTotal: \$12.50" test.png

# Run OCR
tesseract test.png stdout
```

Expected output:
```
Test Receipt
Total: $12.50
```

## Docker Deployment

The Dockerfile includes Tesseract automatically:

```dockerfile
# Dockerfile already includes this:
RUN apk add --no-cache tesseract-ocr tesseract-ocr-data-eng
```

No extra configuration needed for Docker!

## AWS Deployment

For EC2 instances:

```bash
# Amazon Linux 2
sudo amazon-linux-extras install epel
sudo yum install tesseract

# Ubuntu
sudo apt install tesseract-ocr
```

Add to your systemd service or startup script.

## Language Support

By default, Tesseract includes English. For other languages:

**Windows:**
- Download language packs from: https://github.com/tesseract-ocr/tessdata
- Place in: `C:\Program Files\Tesseract-OCR\tessdata\`

**macOS:**
```bash
# Spanish
brew install tesseract-lang
```

**Linux:**
```bash
# Spanish
sudo apt install tesseract-ocr-spa

# French
sudo apt install tesseract-ocr-fra
```

**Use in code:**
```python
# In ocr.py, modify:
pytesseract.image_to_string(image, lang='spa')  # Spanish
```

## Improving OCR Accuracy

For better results with receipts:

1. **Good lighting** when taking photos
2. **Flat receipts** - straighten curled edges
3. **Clear focus** - avoid blurry images
4. **Crop to receipt** - remove background
5. **High resolution** - at least 300 DPI

## Troubleshooting

### "Tesseract not found"

**Check if installed:**
```bash
# Windows
where tesseract

# macOS/Linux
which tesseract
```

**If not found, install it** (see Installation above)

**If installed but not found:**

Set the full path in `.env`:
```env
# Windows
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe

# macOS
TESSERACT_CMD=/usr/local/bin/tesseract

# Linux
TESSERACT_CMD=/usr/bin/tesseract
```

### "Failed to execute tesseract"

**Check permissions:**
```bash
# Linux/macOS
ls -la $(which tesseract)
chmod +x $(which tesseract)
```

### Poor OCR Quality

1. **Check image quality** - Take a clearer photo
2. **Try preprocessing:**
   ```python
   # Add to ocr.py:
   from PIL import ImageEnhance
   enhancer = ImageEnhance.Contrast(image)
   image = enhancer.enhance(2)  # Increase contrast
   ```
3. **Use higher resolution** images
4. **Crop to just the receipt** area

### Windows: "tesseract.exe has stopped working"

- Reinstall Tesseract from the official installer
- Make sure you have Visual C++ Redistributable installed
- Try running as Administrator once

## Comparison: Tesseract vs Google Cloud Vision

| Feature | Tesseract (FREE) | Google Vision ($) |
|---------|------------------|-------------------|
| Cost | $0 | ~$1.50/1000 images |
| Accuracy | 85-90% | 95-98% |
| Speed | Fast (local) | Slower (API) |
| Setup | Install once | API key + billing |
| Privacy | Data stays local | Sent to Google |
| Offline | ✅ Works offline | ❌ Needs internet |

**Recommendation**: Start with Tesseract (free), upgrade to Google Vision only if accuracy is critical.

## Switching to Google Cloud Vision

If you want to use Google Vision instead:

1. Set up Google Cloud Project
2. Enable Cloud Vision API
3. Create service account and download JSON key
4. Update `.env`:
   ```env
   OCR_ENGINE=google
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   GCP_PROJECT_ID=your-project-id
   ```
5. Install: `pip install google-cloud-vision`

## Best Practices

1. **Start with Tesseract** - It's free and good enough for most receipts
2. **Good phone camera** - Better than expensive OCR
3. **Test with real receipts** - See if accuracy meets your needs
4. **Upgrade if needed** - Only switch to paid OCR if Tesseract doesn't work
5. **Manual fallback** - Always allow manual entry for problem receipts

## Performance Tips

For better performance with many receipts:

1. **Resize images** before OCR:
   ```python
   max_size = 1200
   image.thumbnail((max_size, max_size))
   ```

2. **Process in batches** rather than one-by-one

3. **Cache results** for the same receipt

4. **Use image preprocessing** to improve accuracy

## Support

- Official Docs: https://tesseract-ocr.github.io/
- GitHub: https://github.com/tesseract-ocr/tesseract
- Wiki: https://github.com/tesseract-ocr/tesseract/wiki
- Python Wrapper: https://github.com/madmaze/pytesseract

## Questions?

**Q: Is Tesseract really free?**
A: Yes! It's open source under Apache 2.0 license. Use it commercially with no fees.

**Q: How accurate is it?**
A: About 85-90% for clear receipt images. Good enough for most use cases.

**Q: Can I use it for production?**
A: Absolutely! Many companies use Tesseract in production.

**Q: What if it can't read a receipt?**
A: Users can manually enter the data. The system always has a manual entry option.

**Q: Will it work on my phone?**
A: The mobile app (if built) would send images to the backend where Tesseract runs.
