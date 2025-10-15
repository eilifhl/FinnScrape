#!/usr/bin/env python3

import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def fetch_pages(query):
    """
    Henter data for bærbare PC-er fra FINN Torget ved å iterere gjennom sidene for et gitt søk.
    """
    base_url = "https://www.finn.no/recommerce/forsale/search"
    page_num = 1
    laptops = []

    print(f"Starter henting for søket: '{query}'...")
    while True:
        params = {
            "price_to": "7000",
            "product_category": "2.93.3215.43",
            "page": page_num,
            "q": query,  # Bruker nå query-parameteret
            # "location": "1.20016.20318",  # trondheim
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Stopper hvis statuskoden er en feil (f.eks. 404, 500)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("article", class_="sf-search-ad")

            if not articles:
                print(
                    f"Ingen flere annonser funnet for '{query}'. Stopper på side {page_num - 1}."
                )
                break

            for article in articles:
                title_element = article.find("h2", class_="h4")
                title = (
                    title_element.get_text(strip=True)
                    if title_element
                    else "Ingen tittel"
                )

                price_container = article.find("div", class_="font-bold")
                price_element = (
                    price_container.find("span") if price_container else None
                )
                price = (
                    price_element.get_text(strip=True)
                    if price_element
                    else "Ingen pris"
                )

                link_element = article.find("a", class_="sf-search-ad-link")
                url = link_element["href"] if link_element else "Ingen URL"

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

            print(
                f"Fant {len(articles)} bærbare PC-er på side {page_num} for '{query}'."
            )
            page_num += 1

        except requests.exceptions.RequestException as e:
            print(
                f"En feil oppstod under henting av side {page_num} for '{query}': {e}. Stopper."
            )
            break
        except Exception as e:
            print(f"En uventet feil oppstod for '{query}': {e}. Stopper.")
            break

    return laptops


def to_csv(laptops, filename):
    """Skriver en liste med data om bærbare PC-er til en CSV-fil."""
    if not laptops:
        print(f"Ingen data å skrive til {filename}.")
        return

    fieldnames = laptops[0].keys()

    with open(filename, "w", newline="", encoding="utf-8") as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(laptops)
    print(f"Lagret {len(laptops)} annonser til {filename}.")


if __name__ == "__main__":
    # Definer søkene du vil kjøre i denne listen
    search_queries = ["oled"]
    all_fetched_laptops = []

    # Går gjennom hvert søk og legger til resultatene i en felles liste
    for query in search_queries:
        laptops_for_query = fetch_pages(query)
        if laptops_for_query:
            all_fetched_laptops.extend(laptops_for_query)

    if all_fetched_laptops:
        to_csv(all_fetched_laptops, "oled_laptops_from_finn.csv")
