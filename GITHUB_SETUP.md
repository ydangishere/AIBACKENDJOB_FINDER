# Push to GitHub (Private Repo)

## Step 1: Create private repo on GitHub

1. Go to https://github.com/new
2. Repository name: `AIbackendjobscraper` (or any name)
3. Select **Private**
4. Do NOT check "Add a README" (you already have one)
5. Click **Create repository**

## Step 2: Push from your PC

GitHub will show you commands. Or run:

```powershell
cd d:\AI\AIbackendjobscraper
git remote add origin https://github.com/YOUR_USERNAME/AIbackendjobscraper.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 3: Share with others (optional)

- **Private repo:** Only people you invite (Settings → Collaborators) can clone
- To share: give them the repo link, then add them as collaborator so they can clone
