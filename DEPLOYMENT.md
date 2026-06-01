# Deployment Guide

This document explains how to set up and deploy the Neural Geometry Llama application using GitHub Actions and various hosting platforms.

## Architecture

- **Frontend**: React + Vite (deployed to Vercel)
- **Backend**: FastAPI + Python (deployed to Railway, Render, Cloud Run, or similar)

## Prerequisites

### GitHub Secrets Setup

Configure the following secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

#### Backend Secrets

- `OPENAI_API_KEY` ⚠️ **REQUIRED** - OpenAI API key for GPT-4o-mini prompt generation
  - Obtain from: https://platform.openai.com/api-keys
  - Used for: Generating diverse prompts for concept analysis

- `HF_TOKEN` (optional) - HuggingFace token for model access
  - Obtain from: https://huggingface.co/settings/tokens

- `NDIF_API_KEY` (optional) - nnsight API key for neural analysis
  - Used for: Advanced activation extraction

#### Frontend Secrets (Vercel deployment)

- `VERCEL_TOKEN` - Personal access token for Vercel
  - Obtain from: https://vercel.com/account/tokens

- `VERCEL_ORG_ID` - Your Vercel organization ID
  - Find in: Vercel dashboard under organization settings

- `VERCEL_PROJECT_ID` - Your Vercel project ID
  - Find in: Vercel dashboard > Project Settings

## Deployment Workflows

### Automatic Deployment

Two GitHub Actions workflows are configured:

#### 1. Backend Deployment (`.github/workflows/deploy-backend.yml`)

**Triggers on:**
- Push to `main` branch with changes in `app/backend/**`
- Manual trigger via GitHub Actions

**Steps:**
1. Validates environment configuration
2. Installs Python dependencies
3. Runs syntax checks
4. Verifies required secrets
5. Builds Docker image (for manual trigger)
6. Ready for deployment to your chosen platform

**Next steps:** Configure your hosting platform (see below)

#### 2. Frontend Deployment (`.github/workflows/deploy-frontend.yml`)

**Triggers on:**
- Push to `main` branch with changes in `app/frontend/**`
- Manual trigger via GitHub Actions

**Steps:**
1. Installs Node.js dependencies
2. Runs ESLint
3. Builds the application
4. Deploys to Vercel (if configured)

## Platform-Specific Setup

### Option A: Railway (Recommended for simplicity)

Railway is the easiest option for deploying the backend.

**Setup:**
1. Connect GitHub repository to Railway: https://railway.app
2. Create new service for backend
3. Set environment variables in Railway dashboard:
   - `OPENAI_API_KEY` (from GitHub secrets)
   - `HF_TOKEN`
   - `NDIF_API_KEY`
4. Railway will automatically deploy on `main` branch push

**Docker support:** ✓ Automatic (uses `app/backend/Dockerfile`)

### Option B: Google Cloud Run

Google Cloud Run offers free tier and automatic scaling.

**Setup:**
1. Create Google Cloud project
2. Enable Cloud Run API
3. Connect GitHub repository via Cloud Build
4. Set environment variables in Cloud Run service settings
5. Configure for push-on-deploy

**Update workflow:** Modify `.github/workflows/deploy-backend.yml` to push to Google Artifact Registry:

```yaml
- name: Setup Cloud SDK
  uses: google-github-actions/setup-gcloud@v1
  
- name: Push Docker image to Cloud Artifact Registry
  run: |
    gcloud auth configure-docker gcr.io
    docker build -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/neural-geometry:latest app/backend
    docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/neural-geometry:latest
```

### Option C: Render

Render provides free tier with easy GitHub integration.

**Setup:**
1. Connect GitHub to Render: https://render.com
2. Create new Web Service from repository
3. Configure:
   - Root directory: `app/backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables from GitHub secrets

### Option D: Heroku (Legacy)

Heroku deprecated free tier, but paid options available.

**Setup:**
1. Connect GitHub repository
2. Configure Procfile in root:
   ```
   web: cd app/backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Set environment variables via Heroku CLI or dashboard

## Vercel Frontend Setup

### Initial Setup

1. Connect GitHub repository to Vercel: https://vercel.com
2. Configure build settings:
   - Root directory: `app/frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Set environment variables:
   - `VITE_API_URL`: Your backend API URL (e.g., `https://your-backend.railway.app`)

### Automatic Deployment

The frontend workflow automatically deploys to Vercel on push to `main`.

**Required secrets in GitHub:**
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Get these from your Vercel dashboard.

## Environment Variables

### Backend (`app/backend/.env`)

```bash
# REQUIRED
OPENAI_API_KEY=sk-...

# OPTIONAL
HF_TOKEN=hf_...
NDIF_API_KEY=...
CORS_ORIGIN=https://your-frontend-url.vercel.app
```

### Frontend (`app/frontend/.env.local`)

```bash
VITE_API_URL=https://your-backend-url.railway.app
```

## Local Development

### Backend

```bash
cd app/backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python -m uvicorn main:app --reload
```

### Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Access at `http://localhost:5173`

## Troubleshooting

### Deployment fails with "OPENAI_API_KEY secret is not set"

**Solution:** Add `OPENAI_API_KEY` to your GitHub repository secrets.

Steps:
1. Go to `Settings > Secrets and variables > Actions`
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY`
4. Value: Your OpenAI API key from https://platform.openai.com/api-keys

### Frontend can't reach backend API

**Solution:** Set `VITE_API_URL` environment variable in Vercel project settings.

1. Go to Vercel project > Settings > Environment Variables
2. Add: `VITE_API_URL=https://your-backend-url`
3. Redeploy

### Docker build fails

**Solution:** Check Python version and dependency compatibility.

- Python 3.12+ required (specified in Dockerfile)
- PyTorch CPU version is large (~500MB)
- Build may take 5-10 minutes

## Monitoring

### GitHub Actions Logs

Monitor deployment status at: `Repository > Actions > Workflows`

### Vercel Dashboard

Monitor frontend deployment: https://vercel.com/dashboard

### Platform-Specific Logs

- **Railway**: Dashboard > Deployments > Logs
- **Render**: Dashboard > Services > Logs
- **Cloud Run**: Cloud Console > Cloud Run > Service Logs
- **Heroku**: `heroku logs --tail`

## CI/CD Best Practices

1. **Always use secrets** for sensitive data (API keys, tokens)
2. **Test locally first** before pushing to main
3. **Monitor logs** after deployment
4. **Set environment variables** in production platform, not in `.env` files
5. **Keep secrets rotated** regularly
6. **Use different secrets** for dev/staging/prod (if applicable)

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Railway Documentation](https://docs.railway.app)
- [Vercel Documentation](https://vercel.com/docs)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Render Documentation](https://render.com/docs)
