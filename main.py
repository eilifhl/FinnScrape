import csv
import requests
from datetime import datetime
from requests.exceptions import JSONDecodeError
from dotenv import load_dotenv
import os
from google import genai
import json

load_dotenv()

def fetch_pages(q : str, deltid = False, only_IT_industry=False):
    """

    """


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
                deadline = datetime.fromtimestamp(deadline_ts / 1000)
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
            }

            jobs.append(job)

        print(f'Found {len(docs)} jobs on page {page_num}.')
        page_num += 1

    return jobs

def classify_jobs_with_genai(jobs_list):
    """
    Enriches each job dictionary in a list with a new 'relevance_classification' key
    based on a generative AI model's output.
    """
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
        A job is 'irrelevant' if it is specifically targeting senior developers, or it is for IT support or similar.

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
          "Senior Python Developer": "relevant",
          "Frontend Developer (React)": "irrelevant"
        }}
        """

        print(f"\n--- Processing Batch {i//batch_size + 1} ---")
        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents = prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        classifications = json.loads(cleaned_response_text)

        print("AI Classifications received:", classifications)

        for job in batch:
            title = job.get('job_title')
            classification = classifications.get(title, 'unclassified')
            job['relevance_classification'] = classification

    return jobs_list

def to_csv(jobs, filename):
    """Writes a list of job dictionaries to a single CSV file."""
    if not jobs:
        print(f"No jobs to write to {filename}.")
        return

    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, jobs[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(jobs)
    print(f"Successfully saved {len(jobs)} classified jobs to {filename}.")

if __name__ == "__main__":
    all_fetched_jobs = fetch_pages(q = "developer", deltid = True, only_IT_industry = True)

    classified_jobs = classify_jobs_with_genai(all_fetched_jobs)

    print("\n--- Classification Complete ---")

    if classified_jobs:
        to_csv(classified_jobs, 'jobs_classified.csv')
