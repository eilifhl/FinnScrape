import csv
import requests
from datetime import datetime
from requests.exceptions import JSONDecodeError
from dotenv import load_dotenv
import os
from google import genai
import json
from bs4 import BeautifulSoup

load_dotenv()

def fetch_pages(q : str, deltid = False, only_IT_industry=False):
    page_num = 1
    base_url = "https://www.finn.no/job/job-search-page/api/search/SEARCH_ID_JOB_FULLTIME"
    jobs = []

    industry = "&industry=8&industry=33&industry=65" if only_IT_industry else ""
    extent = "&extent=3942" if deltid else ""

    print('Beginning fetch...')
    while True:
        url = f'{base_url}?q={q}&page={page_num}{extent}{industry}'
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch page {page_num}, status code: {response.status_code}. Stopping.")
            break

        try:
            data = response.json()
        except JSONDecodeError:
            print("Could not decode JSON, probably reached the last page. Stopping.")
            break

        docs = data.get('docs', [])

        if not docs:
            print(f'No more pages found. Stopped at page {page_num - 1}.')
            break

        for doc in docs:
            deadline_ts = doc.get('deadline')
            if deadline_ts:
                deadline = datetime.fromtimestamp(doc.get('deadline') / 1000)
            else:
                deadline = None

            job = {
                'job_title' : doc.get('job_title'),
                'location' : doc.get('location'),
                'company_name' : doc.get('company_name'),
                'heading' : doc.get('heading'),
                'url' : doc.get('canonical_url'),
                'published' : datetime.fromtimestamp(doc.get('published') / 1000 ),
                'deadline' : deadline,
                'source' : 'finn.no',
            }

            jobs.append(job)

        print(f'Found {len(docs)} jobs on page {page_num}.')
        page_num += 1

    return jobs

def fetch_arbeidsplassen_jobs(q : str, only_IT_industry=False):
    base_url = "https://arbeidsplassen.nav.no/stillinger"
    
    params = {'q': q}
    if only_IT_industry:
        params['occupationLevel1'] = 'IT'

    jobs = []
    
    print('\nBeginning fetch from arbeidsplassen.no...')
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch arbeidsplassen.no: {e}. Stopping.")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    results_section = soup.find('section', {'aria-label': lambda x: x and 'Søketreff' in x})
    
    if not results_section:
        print("Could not find job results section.")
        return []
        
    job_articles = results_section.find_all('article', recursive=False)
    
    if not job_articles:
        print("No jobs found.")
        return []
        
    for article in job_articles:
        
        title_tag = article.find('h2')
        if title_tag and title_tag.find('a'):
            title_link = title_tag.find('a')
            job_title = title_link.text.strip()
            url = 'https://arbeidsplassen.nav.no' + title_link['href'] if 'href' in title_link.attrs else 'N/A'
        else:
            job_title = 'N/A'
            url = 'N/A'

        aria_label = article.get('aria-label', '')
        parts = aria_label.split(', ')
        
        company_name = 'N/A'
        location = 'N/A'
        if len(parts) >= 3:
             location = parts[-1]
             company_name = parts[-2]
        elif len(parts) == 2:
             location = parts[-1]
             company_name = parts[-2] 

        deadline_tag = article.find('p', class_='navds-typo--color-subtle', string=lambda t: t and 'Søk senest' in t)
        if deadline_tag:
            deadline_text = deadline_tag.text.replace('Søk senest', '').strip()
        else:
            deadline_text = 'N/A (Check URL)'

        if location != 'N/A':
            location += ' (Arbeidsplassen)' 
            
        job = {
            'job_title' : job_title,
            'location' : location,
            'company_name' : company_name,
            'heading' : 'N/A (Arbeidsplassen - Scraping)',
            'url' : url,
            'published' : None, 
            'deadline' : deadline_text,
            'source' : 'arbeidsplassen.no'
        }

        jobs.append(job)

    print(f'Found {len(jobs)} jobs on arbeidsplassen.no.')
    return jobs

def classify_jobs_with_genai(jobs_list):
    if not jobs_list:
        print("No jobs to classify.")
        return []

    client = genai.Client()

    batch_size = 50

    print("Starting job classification with Generative AI...")

    for i in range(0, len(jobs_list), batch_size):
        batch = jobs_list[i:i + batch_size]

        prompt_jobs = []
        for job in batch:
            prompt_jobs.append({
                "job_title": job.get('job_title'),
                "heading": job.get('heading'),
            })

        relevance_criteria = """
        I am a Junior Developer in my 2nd. year of university studying Computer Science.
        I will apply to all jobs relevant to Comp. Sci. and software engineering, although i will exclude roles like tech support or similar.
        A job is 'relevant' if it is a junior or internship role for young fresh devs.
        A job is 'irrelevant' if it is specifically targeting senior developers,
        or it is for IT support or similar.

        Location is not important.
        """

        prompt = f"""
        Based on the following criteria:
        ---
        {relevance_criteria}
        ---
        Please classify each job in the following list as either 'relevant' or 'irrelevant'.
        Provide your response as a JSON object where the key is the exact job title from the list and the value is the classification.

        Jobs to classify:
        {json.dumps(prompt_jobs, indent=2)}

        Example of desired JSON output format:
        {{
          "Senior Python Developer": "irrelevant",
          "Frontend Developer (React)": "relevant"
        }}
        """

        print(f"\n--- Processing Batch {i//batch_size + 1} ---")
        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents = prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        
        try:
            classifications = json.loads(cleaned_response_text)
        except json.JSONDecodeError as e:
            print(f"Error decoding AI response for batch {i//batch_size + 1}: {e}. Response text: {cleaned_response_text[:200]}...")
            classifications = {}

        print("AI Classifications received:", classifications)

        for job in batch:
            title = job.get('job_title')
            classification = classifications.get(title, 'unclassified')
            job['relevance_classification'] = classification

    return jobs_list

def to_csv(jobs, filename):
    if not jobs:
        print(f"No jobs to write to {filename}.")
        return

    fieldnames = [
        'job_title', 
        'relevance_classification',
        'company_name', 
        'location', 
        'heading', 
        'url', 
        'published', 
        'deadline',
        'source',                   
    ]
    
    processed_jobs = []
    for job in jobs:
        processed_jobs.append({key: job.get(key) for key in fieldnames})


    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(processed_jobs)
    print(f"Successfully saved {len(jobs)} classified jobs to {filename}.")

if __name__ == "__main__":
    finn_jobs = fetch_pages(q = "internship", deltid = False, only_IT_industry = True)

    arbeidsplassen_jobs = fetch_arbeidsplassen_jobs(q = "internship", only_IT_industry = True)
    
    all_fetched_jobs = finn_jobs + arbeidsplassen_jobs

    classified_jobs = classify_jobs_with_genai(all_fetched_jobs)

    print("\n--- Classification Complete ---")

    if classified_jobs:
        to_csv(classified_jobs, 'jobs_classified_combined.csv')
