# Deployment Quick Start Guide

This is a quick reference for deploying the Neural Geometry application. For detailed information, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## ⚡ 5-Minute Setup

### Step 1: Add GitHub Secrets (Required)

Go to your repository: `Settings > Secrets and variables > Actions > New repository secret`

Add these secrets:

| Secret | Value | Get from |
|--------|-------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | https://platform.openai.com/api-keys |
| `HF_TOKEN` | (optional) HuggingFace token | https://huggingface.co/settings/tokens |
| `NDIF_API_KEY` | (optional) nnsight API key | https://nnsight.net |

**For Vercel deployment (optional):**

| Secret | Value | Get from |
|--------|-------|----------|
| `VERCEL_TOKEN` | Your Vercel API token | https://vercel.com/account/tokens |
| `VERCEL_ORG_ID` | Your Vercel organization ID | Vercel dashboard |
| `VERCEL_PROJECT_ID` | Your Vercel project ID | Vercel dashboard |

### Step 2: Choose Your Backend Hosting

Pick one:

**Option A: Railway** (Easiest)
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your repository
5. Railway automatically deploys from `app/backend/Dockerfile`

**Option B: Render**
1. Go to https://render.com
2. Create new "Web Service"
3. Connect GitHub
4. Set Root: `app/backend`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Option C: Google Cloud Run**
1. Enable Cloud Run API in Google Cloud Console
2. Connect GitHub via Cloud Build
3. Deploy automatically on push to main

**Option D: Vercel (Backend)**
1. Go to https://vercel.com/new
2. Select repository
3. Select "Other" template
4. Root directory: `app/backend`

### Step 3: Deploy Frontend (Optional - if not using automatic Vercel)

1. Go to https://vercel.com
2. Import your GitHub repository
3. Set Root directory: `app/frontend`
4. Add environment variable: `VITE_API_URL=https://your-backend-url.com`
5. Deploy

### Step 4: Configure Backend Environment Variables

In your hosting platform dashboard, add:

```
OPENAI_API_KEY=sk-...              # From GitHub secret
HF_TOKEN=hf_...                    # From GitHub secret (optional)
NDIF_API_KEY=...                   # From GitHub secret (optional)
CORS_ORIGIN=https://frontend-url   # Your Vercel frontend URL
```

## ✅ Verify Deployment

After pushing code:

1. **Check GitHub Actions**: Repository > Actions
   - Green ✓ = workflow passed
   - Red ✗ = check logs for errors

2. **Check Backend**: `curl https://your-backend-url/api/health`
   - Should return: `{"status":"ok"}`

3. **Check Frontend**: Visit `https://your-frontend-url`
   - Should load the Neural Geometry app

## 🔧 Common Issues

### "OPENAI_API_KEY secret is not set"

**Fix**: Add `OPENAI_API_KEY` to GitHub Secrets:
- Go to Settings > Secrets and variables > Actions
- Click "New repository secret"
- Name: `OPENAI_API_KEY`
- Value: Your OpenAI key from https://platform.openai.com/api-keys

### Frontend can't reach backend

**Fix**: Set `VITE_API_URL` environment variable in your frontend hosting:

**Vercel:**
1. Project Settings > Environment Variables
2. Add: `VITE_API_URL=https://your-backend-url`
3. Redeploy

**Railway/Render:**
1. Project Settings > Environment Variables
2. Add: `CORS_ORIGIN=https://your-frontend-url`

### Docker build fails

**Fix**: Ensure you have:
- Python 3.12+
- ~1GB disk space (PyTorch is large)
- 10+ minutes build time is normal

## 📊 GitHub Actions Workflows

Two workflows automatically trigger:

### 1. Backend Deployment (`.github/workflows/deploy-backend.yml`)
- **Triggers on**: Push to `main` with changes in `app/backend/**`
- **Steps**: Validate → Install → Test → Build Docker
- **Next**: Deploy to your chosen platform

### 2. Frontend Deployment (`.github/workflows/deploy-frontend.yml`)
- **Triggers on**: Push to `main` with changes in `app/frontend/**`
- **Steps**: Install → Lint → Build → Deploy to Vercel

## 📚 Full Documentation

- See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete setup guide
- See [.github/SECRETS.md](./.github/SECRETS.md) for secret management
- See [app/backend/.env.example](./app/backend/.env.example) for backend config
- See [app/frontend/README.md](./app/frontend/README.md) for frontend info

## 🚀 Next Steps

1. Add GitHub Secrets (see Step 1 above)
2. Push code to trigger workflows
3. Monitor GitHub Actions > Workflows
4. Check your hosting platform dashboard
5. Verify deployment with curl/browser

For more help, open an issue on GitHub or see [DEPLOYMENT.md](./DEPLOYMENT.md).
