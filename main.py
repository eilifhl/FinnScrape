import csv
import requests
from datetime import datetime
from requests.exceptions import JSONDecodeError
from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
client = genai.Client()

def fetch_pages(q : str, deltid = False):
    page_num = 1
    base_url = "https://www.finn.no/job/job-search-page/api/search/SEARCH_ID_JOB_FULLTIME"
    jobs = []

    extent = "&extent=3942" if deltid else ""

    print('Beginning fetch...')
    while True:
        url = f'{base_url}?q={q}&page={page_num}{extent}'
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

def to_csv(dics):
    if not dics:
        print("No jobs found to write to CSV.")
        return

    with open('job_utvikler.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, dics[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(dics)

to_csv(fetch_pages(q="utvikler", deltid = True))
