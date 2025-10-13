#!/usr/bin/env python3

import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def fetch_pages():
    """
    Henter data for bærbare PC-er fra FINN Torget ved å iterere gjennom sidene.
    """
    base_url = "https://www.finn.no/recommerce/forsale/search"
    page_num = 1
    laptops = []

    print("Starter henting...")
    while True:
        params = {
            "price_to": "7000",
            "product_category": "2.93.3215.43",
            "page": page_num,
            "q": "16gb",
            # "location": "1.20016.20318",  # trondheim
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Stopper hvis statuskoden er en feil (f.eks. 404, 500)

            soup = BeautifulSoup(response.text, "html.parser")
            # Finner alle <article>-elementer, som representerer en annonse
            articles = soup.find_all("article", class_="sf-search-ad")

            if not articles:
                print(f"Ingen flere annonser funnet. Stopper på side {page_num - 1}.")
                break

            for article in articles:
                # Henter tittel fra <h2>-elementet inni artikkelen
                title_element = article.find("h2", class_="h4")
                title = (
                    title_element.get_text(strip=True)
                    if title_element
                    else "Ingen tittel"
                )

                price_container = article.find("div", class_="font-bold")

                # Then, find the <span> within that container
                price_element = (
                    price_container.find("span") if price_container else None
                )

                price = (
                    price_element.get_text(strip=True)
                    if price_element
                    else "Ingen pris"
                )

                # Henter lenken til annonsen
                link_element = article.find("a", class_="sf-search-ad-link")
                url = link_element["href"] if link_element else "Ingen URL"

                # Henter lokasjon
                location_element = article.find("span", class_="whitespace-nowrap")
                location = (
                    location_element.get_text(strip=True)
                    if location_element
                    else "Ingen lokasjon"
                )

                laptop = {
                    "tittel": title,
                    "pris": price,
                    "lokasjon": location,
                    "url": url,
                    "hentet_dato": datetime.now().strftime("%Y-%m-%d"),
                }
                laptops.append(laptop)

            print(f"Fant {len(articles)} bærbare PC-er på side {page_num}.")
            page_num += 1

        except requests.exceptions.RequestException as e:
            print(f"En feil oppstod under henting av side {page_num}: {e}. Stopper.")
            break
        except Exception as e:
            print(f"En uventet feil oppstod: {e}. Stopper.")
            break

    return laptops


def to_csv(laptops, filename):
    """Skriver en liste med data om bærbare PC-er til en CSV-fil."""
    if not laptops:
        print(f"Ingen data å skrive til {filename}.")
        return

    # Bruker den første ordboken til å bestemme kolonnenavnene
    fieldnames = laptops[0].keys()

    with open(filename, "w", newline="", encoding="utf-8") as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(laptops)
    print(f"Lagret {len(laptops)} annonser til {filename}.")


if __name__ == "__main__":
    all_fetched_laptops = fetch_pages()

    if all_fetched_laptops:
        to_csv(all_fetched_laptops, "laptops_from_finn.csv")
