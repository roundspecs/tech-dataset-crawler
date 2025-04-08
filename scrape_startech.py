from typing import Any
from playwright.sync_api import sync_playwright, Page
import csv


def fetch_category_urls(page: Page) -> list[str]:
    page.goto("https://www.startech.com.bd/", wait_until="domcontentloaded")
    categories_list = page.query_selector("ul.navbar-nav")
    if not categories_list:
        print("No categories found")
        return []
    category_urls = [
        a.get_attribute("href") for a in categories_list.query_selector_all("> li > a")
    ]
    return [url for url in category_urls if url]


def fetch_product_urls(page: Page, category_url: str) -> list[str]:
    page.goto(f"{category_url}?limit=90", wait_until="domcontentloaded")
    product_list = page.query_selector("div.main-content.p-items-wrap")
    if not product_list:
        print(f"No products found in {category_url}")
        return []
    product_urls = [
        a.get_attribute("href") for a in product_list.query_selector_all("h4 > a")
    ]
    return [url for url in product_urls if url]


def fetch_product_details(page: Page, product_url: str):
    page.goto(product_url, wait_until="domcontentloaded")

    # Title
    title_element = page.query_selector("h1.product-name")
    title = title_element.inner_text() if title_element else None

    # Price
    price_element = page.query_selector("td.product-regular-price")
    price_unsanitized = price_element.inner_text() if price_element else None
    try:
        price = (
            int(price_unsanitized.replace(",", "").replace("৳", "").strip())
            if price_unsanitized
            else None
        )
    except ValueError:
        print(f"Error converting price to integer: {price_unsanitized}")
        price = None

    # Short Description
    short_description_element = page.query_selector("div.short-description")
    short_description = (
        short_description_element.inner_text() if short_description_element else None
    )

    # Full Description
    full_description_element = page.query_selector("div.full-description")
    full_description = (
        full_description_element.inner_text() if full_description_element else None
    )

    details: dict[str, Any] = {
        "title": title,
        "price": price,
        "short_description": short_description,
        "full_description": full_description,
    }

    # Specifications
    specifications_tab = page.query_selector("section.specification-tab")
    if specifications_tab:
        rows = specifications_tab.query_selector_all("table > tbody > tr")
        for row in rows:
            key_em = row.query_selector("td.name")
            key = key_em.inner_text().strip() if key_em else None
            value_em = row.query_selector("td.value")
            value = value_em.inner_text().strip() if value_em else None
            if key and value:
                key = key.replace(":", "").strip()
                details[key] = value

    return details


def save_dict_list_to_csv(filename: str, data: list[dict[str, Any]]) -> None:
    # Collect all unique keys
    all_keys: set[str] = set()
    for item in data:
        all_keys.update(item.keys())

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_keys))
        writer.writeheader()
        for row in data:
            writer.writerow(row)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    category_urls = fetch_category_urls(page)
    print(f"Successfully fetched {len(category_urls)} category URLs.")

    all_product_details: list[dict[str, Any]] = []

    for category_url in category_urls:
        product_urls = fetch_product_urls(page, category_url)
        print(
            f"Successfully fetched {len(product_urls)} product URLs from {category_url}."
        )
        for product_url in product_urls[:2]:
            details = fetch_product_details(page, product_url)

            # TODO: Perhaps we should keep the details even if price is not found
            # if not details['price']:
            #     print(f"Price not found for {product_url}")
            #     continue

            all_product_details.append(details)

    print(f"Successfully fetched details for {len(all_product_details)} products.")
    save_dict_list_to_csv("startech_products.csv", all_product_details)
    print("Product details saved to startech_products.csv.")
    browser.close()
