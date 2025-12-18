# Deployment Guide

This guide will help you deploy your static website to various hosting services.

## Quick Deploy Options

### GitHub Pages

1. Create a new GitHub repository
2. Copy the contents of the `output/` directory to the repository
3. Go to Settings → Pages
4. Select the branch and folder (usually `main` and `/ (root)`)
5. Your site will be available at `https://yourusername.github.io/repository-name/`

### Netlify

1. Go to [netlify.com](https://netlify.com)
2. Drag and drop the `output/` folder onto the Netlify dashboard
3. Your site will be live instantly with a random URL
4. You can customize the domain in site settings

### Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Navigate to the `output/` directory: `cd output`
3. Run: `vercel`
4. Follow the prompts to deploy

### Manual Upload

1. Upload all files from the `output/` directory to your web server
2. Ensure `index.html` is in the root of your web directory
3. Your site should be accessible immediately

## Automated Deployment

You can set up automated deployments by:

1. Running `generate_site.py` on a schedule (cron job, GitHub Actions, etc.)
2. Automatically deploying the `output/` directory after generation
3. This keeps your site updated with the latest posts

### Example GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Site

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.x'
      - run: pip install -r requirements.txt
      - run: python generate_site.py
        env:
          ED_API_TOKEN: ${{ secrets.ED_API_TOKEN }}
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
```

## Notes

- The `output/` directory contains everything needed for deployment
- No server-side code is required - it's a pure static website
- You can customize the styling in `generate_site.py` if needed

