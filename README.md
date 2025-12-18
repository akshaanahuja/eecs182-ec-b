# Ed Forum Scraper

A simple Python script to scrape posts from your Ed forum with titles starting with "Special Participation B: " and generate a beautiful static website.

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Setup

1. **Get your API token:**
   - Go to [https://edstem.org/us/settings/api-tokens](https://edstem.org/us/settings/api-tokens)
   - Generate a new API token
   - Copy the token

2. **Configure the script:**
   - Open `generate_site.py`
   - Update the configuration section at the top:
     - Set `API_TOKEN` (or set `ED_API_TOKEN` environment variable)
     - Set `COURSE_ID` (find this in your Ed forum URL)

## Usage

Simply run:

```bash
python generate_site.py
```

No command-line arguments needed! Just update the configuration in the script.

## Output

The script generates a static HTML website in the `output/` directory. Open `output/index.html` in your web browser to view the scraped posts.

## Deployment

The `output/` directory contains a complete static website that can be deployed to any static hosting service:

- **GitHub Pages**: Push the `output/` directory to a GitHub repository and enable Pages
- **Netlify**: Drag and drop the `output/` folder to Netlify
- **Vercel**: Deploy the `output/` directory
- **Any web server**: Upload the contents of `output/` to your web server

## Features

- ✅ Beautiful, modern UI with responsive design
- ✅ No CLI arguments needed - just configure and run
- ✅ Filters posts by title prefix automatically
- ✅ Displays post metadata (author, date, comments, votes)
- ✅ Ready for deployment to any static hosting service

## Example

1. Set your API token:
   ```bash
   export ED_API_TOKEN="your_token_here"
   ```

2. Update `COURSE_ID` in `generate_site.py`

3. Run the script:
   ```bash
   python generate_site.py
   ```

4. Open `output/index.html` in your browser or deploy the `output/` directory!

