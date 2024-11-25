import asyncio
import os
from playwright.async_api import async_playwright
import csv

async def iterate_combinations(page, dropdown_values):
    """
    Iterates through chapterName only, creating a separate CSV file for each chapterName (using text as the name).
    Each batch of CSV files will be stored in a dynamically created folder (e.g., csv1, csv2, etc.).
    """
    chapter_names = dropdown_values.get("chapterName", [])
    if not chapter_names:
        print("No chapter names found, skipping iteration.")
        return

    # Determine the base folder name
    base_folder = "csv"
    folder_index = 1
    while os.path.exists(f"{base_folder}{folder_index}"):
        folder_index += 1
    current_folder = f"{base_folder}{folder_index}"
    os.makedirs(current_folder)
    print(f"Created new folder: {current_folder}")

    base_url = "https://bnicentraldubai.ae/en-AE/memberlist"

    for chapter in chapter_names:
        chapter_value = chapter.get("value")
        chapter_text = chapter.get("text").replace(" ", "_").replace("/", "_")
        
        # Define the CSV file path within the current folder
        chapter_csv_file = os.path.join(current_folder, f"{chapter_text}.csv")

        # Initialize the counter for each chapter
        entry_count = 1

        # Create a new CSV file or append if it exists
        if not os.path.exists(chapter_csv_file) or os.path.getsize(chapter_csv_file) == 0:
            with open(chapter_csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([ 
                    "Count", "MemberName", "Region", "City", "Street", "Profession", "Company",
                    "Phone1", "Phone2", "Phone3", "SocialMedia1", "SocialMedia2", "SocialMedia3",
                    "ProfilePhotoLink", "Address", "CompanyWebsite", "CompanyLogo"
                ])
            print(f"Created CSV file for chapter: {chapter_csv_file}")

        url = (f"{base_url}?chapterName={chapter_value}"
               "&chapterCity=&chapterArea="
               "&memberFirstName=&memberKeywords=&memberLastName=&memberCompany=&regionIds=22241")

        print(f"Navigating to URL for chapter: {chapter_text}")
        print(f"URL: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            rows_with_links = await page.evaluate(''' 
                () => Array.from(document.querySelectorAll("#memberListTable tr"))
                    .slice(1)
                    .map(row => {
                        const cells = Array.from(row.querySelectorAll("td"));
                        const link = cells[0]?.querySelector("a")?.href || null;
                        return {
                            data: cells.map(cell => cell.innerText.trim()),
                            link
                        };
                    })
            ''')

            for row in rows_with_links:
                if not row['link']:
                    continue

                await page.goto(row['link'], wait_until="domcontentloaded")
                await asyncio.sleep(2)

                details = await page.evaluate(''' 
                    () => {
                        const contactElements = Array.from(document.querySelectorAll(".memberContactDetails li a"));
                        const phones = contactElements.map(el => el.innerText.trim());
                        const socialLinks = Array.from(
                            document.querySelectorAll(".memberContactDetails .smUrls a")
                        ).map(a => a.href);
                        const profilePhotoLinks = Array.from(document.querySelectorAll(".profilephoto a"))
                            .map(a => a.href);
                        const detailElement = document.querySelector(".widgetMemberCompanyDetail h6");
                        let address = " ";
                        if (detailElement) {
                            address = detailElement.innerHTML
                                .replace(/<br\\s*\\/?>/g, ", ")
                                .replace(/<\\/h6>/g, "")
                                .replace(/<h6>/g, "")
                                .trim();
                        }
                        let companyWebsite = " ";
                        const websiteElement = document.querySelector(".memberProfileInfo p a");
                        if (websiteElement) {
                            companyWebsite = websiteElement.href.trim();
                        }
                        let companyLogo = " ";
                        const logoElement = document.querySelector(".companyLogo img");
                        if (logoElement) {
                            companyLogo = logoElement.src.trim();
                        }
                        return { phones, socialLinks, profilePhotoLinks, address, companyWebsite, companyLogo };
                    }
                ''')

                detailed_row = [entry_count] + row['data'] + [
                    details.get("phones", [])[0] if len(details.get("phones", [])) > 0 else "",
                    details.get("phones", [])[1] if len(details.get("phones", [])) > 1 else "",
                    details.get("phones", [])[2] if len(details.get("phones", [])) > 2 else "",
                    details.get("socialLinks", [])[0] if len(details.get("socialLinks", [])) > 0 else "",
                    details.get("socialLinks", [])[1] if len(details.get("socialLinks", [])) > 1 else "",
                    details.get("socialLinks", [])[2] if len(details.get("socialLinks", [])) > 2 else "",
                    details.get("profilePhotoLinks", [])[0] if len(details.get("profilePhotoLinks", [])) > 0 else "",
                    details.get("address", ""),
                    details.get("companyWebsite", ""),
                    details.get("companyLogo", "")
                ]

                with open(chapter_csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(detailed_row)
                # print(f"Written row to CSV for chapter {chapter_text}: {detailed_row}")

                # Increment the counter after each entry
                entry_count += 1

        except Exception as e:
            print(f"Error navigating to {url} or extracting data for chapter {chapter_text}: {e}")

async def main():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--start-maximized"]
        )
        context = await browser.new_context(ignore_https_errors=True, viewport={"width": 1366, "height": 768})
        page = await context.new_page()
        # Navigate to URL with increased timeout
        url = "https://bnicentraldubai.ae/en-AE/findamember"
        retries = 3
        for i in range(retries):
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print("Page loaded successfully")
                break
            except Exception as e:
                print(f"Attempt {i + 1} failed: {e}")
                if i == retries - 1:
                    raise
        # Retrieve dropdown values
        dropdown_ids = ["chapterName"]
        dropdown_values = {}
        await asyncio.sleep(5)  # Initial wait for page content to load

        for dropdown_id in dropdown_ids:
            values = await page.evaluate('''
                (dropdownId) => Array.from(document.querySelectorAll("#" + dropdownId + " option"))
                    .map(option => ({
                        value: option.value.trim(),
                        text: option.innerText.trim()
                    }))
                    .filter(option => option.value !== "")  // Exclude options with empty values
            ''', dropdown_id)  # Pass dropdown_id directly
            dropdown_values[dropdown_id] = values

        print("Dropdown Values:", dropdown_values)
        # dropdown_values = {
        #     "chapterName": [
        #         {"value": "15090", "text": "BNI Champions"},
        #         {"value": "10410", "text": "BNI Gazelles"},
        #         {"value": "37851", "text": "BNI Gratitude"},
        #         {"value": "1147", "text": "BNI Insomniacs"},
        #         {"value": "39829", "text": "BNI Polaris"},
        #         {"value": "1145", "text": "BNI Rising Phoenix"},
        #         {"value": "38832", "text": "BNI Spectacular"},
        #         {"value": "38554", "text": "BNI Success"},
        #         {"value": "35472", "text": "BNI Victory"},
        #         {"value": "27711", "text": "BNI Warriors"},
        #     ]
        # }

        print("Dropdown Values:", dropdown_values)

        await iterate_combinations(page, dropdown_values)
        await browser.close()

asyncio.run(main())
