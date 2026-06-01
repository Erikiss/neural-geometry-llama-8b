# GitHub Secrets Configuration Guide

This guide explains how to configure GitHub Secrets for the Neural Geometry application deployment.

## Quick Start

1. Go to your repository on GitHub
2. Navigate to `Settings > Secrets and variables > Actions`
3. Click "New repository secret"
4. Add each secret listed below

## Required Secrets

### OPENAI_API_KEY ⚠️

**Purpose:** Generate diverse prompts for concept analysis using GPT-4o-mini

**How to obtain:**
1. Visit https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the generated key
4. Add it to GitHub as secret `OPENAI_API_KEY`

**Value format:** `sk-...` (starts with `sk-`)

**Used by:** Backend (app/backend/prompt_gen.py)

**Cost consideration:** API calls cost money. Monitor usage at https://platform.openai.com/account/billing/overview

---

## Optional Secrets

### HF_TOKEN

**Purpose:** Access HuggingFace models and features

**How to obtain:**
1. Visit https://huggingface.co/settings/tokens
2. Click "New token"
3. Select "Read" access
4. Copy the token
5. Add it to GitHub as secret `HF_TOKEN`

**Value format:** `hf_...` (starts with `hf_`)

**Used by:** Backend (for model access via nnsight library)

---

### NDIF_API_KEY

**Purpose:** Neural network analysis via nnsight library

**How to obtain:**
1. Register at https://nnsight.net
2. Generate API key from your account
3. Add it to GitHub as secret `NDIF_API_KEY`

**Used by:** Backend (extraction.py)

---

## Vercel Deployment Secrets

Required only if using GitHub Actions for automatic Vercel deployment.

### VERCEL_TOKEN

**Purpose:** Authenticate deployments to Vercel

**How to obtain:**
1. Go to https://vercel.com/account/tokens
2. Click "Create"
3. Give it a name (e.g., "GitHub Actions")
4. Copy the token
5. Add it to GitHub as secret `VERCEL_TOKEN`

---

### VERCEL_ORG_ID

**Purpose:** Identify your Vercel organization

**How to obtain:**
1. Go to https://vercel.com/dashboard
2. Select your organization
3. Go to Settings > General
4. Find "ID" field
5. Add it to GitHub as secret `VERCEL_ORG_ID`

---

### VERCEL_PROJECT_ID

**Purpose:** Identify your Vercel project

**How to obtain:**
1. Go to https://vercel.com/dashboard
2. Select your project
3. Go to Settings
4. Find "Project ID" in General section
5. Add it to GitHub as secret `VERCEL_PROJECT_ID`

---

## Cloud Platform Secrets (Optional)

### For Google Cloud Run

**GCP_PROJECT_ID**
- Your Google Cloud project ID
- Find at: https://console.cloud.google.com/welcome

**GCP_SA_KEY**
- Service account key JSON (for authentication)
- Create at: Cloud Console > Service Accounts > Create Key

### For Railway

Railway can read secrets directly from GitHub repository - no separate configuration needed if you connect GitHub integration. Alternatively, add:

**RAILWAY_TOKEN**
- API token for Railway
- Create at: https://railway.app/account/tokens

### For Render

**RENDER_DEPLOY_HOOK**
- Webhook URL for automatic deployment
- Create at: Render Dashboard > Service > Settings > Deploy Hook

---

## Verification Checklist

After adding secrets:

- [ ] `OPENAI_API_KEY` is added and non-empty
- [ ] Secret values are correct (copy-paste carefully!)
- [ ] Secrets are not accidentally committed to Git
- [ ] `.env.example` has NO real secret values
- [ ] GitHub Actions workflow shows green checkmark in logs

## Testing Secrets

GitHub Actions workflows validate secrets at deployment time. Look for:

```
✓ Required secrets are configured
```

If you see:
```
ERROR: OPENAI_API_KEY secret is not set in GitHub
```

The secret was not configured. Follow the steps above to add it.

## Security Best Practices

1. **Never commit secrets to Git** - use `.gitignore` for `.env` files
2. **Rotate secrets regularly** (quarterly recommended)
3. **Use separate secrets per environment** (dev/staging/prod)
4. **Limit secret access** - only grant necessary permissions
5. **Audit secret usage** - check GitHub Actions logs regularly
6. **Use short-lived tokens** when possible

## Revoking/Rotating Secrets

If a secret is compromised:

1. **Immediately revoke** the original:
   - OpenAI: https://platform.openai.com/api-keys (delete the key)
   - HuggingFace: https://huggingface.co/settings/tokens (delete the token)
   - Vercel: https://vercel.com/account/tokens (delete the token)

2. **Generate a new secret** from the service

3. **Update GitHub secret:**
   - Go to Settings > Secrets > Select the secret
   - Click "Update"
   - Paste new value
   - Click "Update secret"

4. **Verify deployment** - redeploy to activate new secret

---

## Troubleshooting

### Secret not available in workflow

**Problem:** GitHub Actions logs show secret not found

**Solution:** 
- Secret must be added to the same branch as the workflow
- Wait 1-2 minutes after adding secret
- Try re-running the workflow manually

### Workflow shows "ERROR: OPENAI_API_KEY secret is not set"

**Problem:** Backend deployment fails with this error

**Solution:**
1. Verify secret is added: Settings > Secrets > Actions
2. Ensure the secret name matches exactly: `OPENAI_API_KEY`
3. Check that the value starts with `sk-`
4. If using workflow_dispatch, ensure you're on the correct branch

### API calls failing with "Invalid API key"

**Problem:** Deployment succeeds but API fails at runtime

**Solution:**
1. Verify the secret value is correct (doesn't have extra spaces)
2. Check API key is active in service (not revoked/expired)
3. Ensure API billing is enabled in the service
4. Check API logs: https://platform.openai.com/account/billing/overview

---

## Environment Variable Mapping

| GitHub Secret | Backend `.env` | Vercel `.env` | Docker Env |
|---------------|---|---|---|
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | N/A | `OPENAI_API_KEY` |
| `HF_TOKEN` | `HF_TOKEN` | N/A | `HF_TOKEN` |
| `NDIF_API_KEY` | `NDIF_API_KEY` | N/A | `NDIF_API_KEY` |
| N/A | `CORS_ORIGIN` | `VITE_API_URL` | `CORS_ORIGIN` |

---

## Reference Links

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [HuggingFace Tokens](https://huggingface.co/settings/tokens)
- [Vercel API Tokens](https://vercel.com/account/tokens)
- [Render Webhooks](https://render.com/docs/deploy-hooks)
- [Railway Tokens](https://docs.railway.app/reference/cli-api#authentication)
