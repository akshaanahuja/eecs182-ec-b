# Ed Forum Scraper - Special Participation B

A one-time script to scrape Ed forum posts with titles containing "special participation b" and generate a beautiful static website.

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

2. **Set your API token:**
   
   **Option 1: Environment variable (recommended)**
   ```bash
   export ED_API_TOKEN='your_token_here'
   ```
   
   **Option 2: Create a .env file**
   Create a `.env` file in the project root:
   ```
   ED_API_TOKEN=your_token_here
   ```

3. **Configure the script:**
   - Open `generate_site.py`
   - Update `COURSE_ID` with your actual course ID (you can find this in your Ed forum URL)

## Usage

Simply run:

```bash
python generate_site.py
```

The script will:
1. Authenticate with the Ed API
2. Fetch all threads from your course
3. Filter threads with titles containing "special participation b" (case-insensitive)
4. Generate a static HTML website in the `output/` directory

## Output

The script generates a static HTML website in the `output/` directory. Open `output/index.html` in your web browser to view the scraped posts.

Each post displays:
- Title
- Author name
- Creation date
- Post content (parsed from Ed's XML format)
- Comment count
- Vote count

## Deployment

The `output/` directory contains a complete static website that can be deployed to any static hosting service:

- **GitHub Pages**: Push the `output/` directory to a GitHub repository and enable Pages
- **Netlify**: Drag and drop the `output/` folder to Netlify
- **Vercel**: Deploy the `output/` directory
- **Any web server**: Upload the contents of `output/` to your web server

## Features

- ✅ Beautiful, modern UI with responsive design
- ✅ Case-insensitive title filtering
- ✅ Parses Ed's XML document format to readable text
- ✅ Displays post metadata (author, date, comments, votes)
- ✅ Sorted by date (newest first)
- ✅ Ready for deployment to any static hosting service

## Notes

- This is a one-time script - run it whenever you want to update the website
- The API token should be kept secret and not committed to version control
- The `.env` file is already in `.gitignore` for your protection

