# Getting Your OpenAI API Key (ChatGPT Business)

If you have a ChatGPT Business, Plus, or Pro subscription, you have access to the OpenAI API.

## Step 1: Get Your API Key

1. Go to https://platform.openai.com/account/api-keys
2. Sign in with your OpenAI account (same account as ChatGPT)
3. Click "Create new secret key"
4. Give it a name like "Expense Tracker"
5. Copy the key (starts with `sk-...`)
6. **Important**: Save it securely - you can't view it again!

## Step 2: Add to Your Environment

Open your `.env` file and add:

```env
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 3: Verify It Works

Start the backend server:

```bash
uvicorn app.main:app --reload
```

You should see:
```
✓ OpenAI API configured (using ChatGPT Business key)
```

If you see an error, the key is either missing or invalid.

## Pricing

**If you have ChatGPT Business/Plus/Pro**: API usage is separate from your subscription, but the rates are very affordable:
- GPT-4: ~$0.03 per 1,000 tokens (about 750 words)
- For expense categorization: ~1-2 cents per receipt

**Example costs**:
- 100 expenses/month: ~$1-2/month
- 500 expenses/month: ~$5-10/month
- 1,000 expenses/month: ~$10-20/month

## What If I Don't Have API Access?

The expense tracker will still work! Without the OpenAI API key:
- OCR will still extract text from receipts (using free Tesseract)
- You'll just need to manually select categories
- All other features work normally

## Troubleshooting

**"Invalid API key" error**:
- Check that you copied the entire key (starts with `sk-`)
- Make sure there are no spaces before/after the key
- Verify the key hasn't been revoked at https://platform.openai.com/account/api-keys

**"Rate limit exceeded"**:
- You're making too many API calls
- Wait a few minutes and try again
- Consider adding a small delay between bulk operations

**"Insufficient quota"**:
- You need to add payment method at https://platform.openai.com/account/billing
- Add at least $5 credit to get started
- Set up billing limits to control costs

## Free Alternative

If you don't want to use OpenAI at all:
1. Set `OPENAI_API_KEY=` (leave empty)
2. The system will work without AI categorization
3. You'll manually categorize expenses using the dropdowns

## API Usage Monitoring

Monitor your API usage at:
https://platform.openai.com/usage

You can set:
- Usage limits (e.g., $10/month max)
- Email alerts when approaching limit
- Hard limits to prevent overage

## Best Practices

1. **Set a monthly budget**: Start with $10/month
2. **Monitor usage**: Check dashboard weekly at first
3. **Enable billing alerts**: Get notified at 50%, 75%, 90%
4. **Keep key secure**: Never commit to git, share in chat, etc.
5. **Rotate keys**: Create new keys every 6 months for security

## Questions?

- OpenAI API Docs: https://platform.openai.com/docs
- Pricing: https://openai.com/pricing
- Support: https://help.openai.com
