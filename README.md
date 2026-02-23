# FinnScrape

This project scrapes job listings from **Finn.no** and **arbeidsplassen.nav.no** (NAV), aggregates them, and uses Google's Gemini AI to classify each job as "relevant" or "irrelevant" for a junior developer/intern.

The results are saved to a CSV file named `jobs_classified_combined.csv`.

## Prerequisites

- Python 3.x
- A Google Cloud API Key (for Gemini)

## Installation

1. Clone this repository.
2. Install the required Python packages:

```bash
pip install requests python-dotenv google-genai beautifulsoup4
```

# Configuration

This project uses `python-dotenv` to load sensitive configuration. 

Create a file named `.env` in the root directory (this file is ignored by git).
Add your Google API Key to the file:

```
GOOGLE_API_KEY=your_google_api_key_here
```

# Usage
Run the main script:

```
python main.py
```


The script will:

1. Fetch "internship" listings from Finn.no (IT industry filters applied).
2. Fetch "internship" listings from arbeidsplassen.nav.no (IT industry filters applied).
3. Send job titles and headings to the GenAI model for classification.
4. Generate a CSV file with the results.