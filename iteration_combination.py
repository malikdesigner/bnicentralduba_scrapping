async def iterate_combinations(page, dropdown_values):
    """
    Iterates through all combinations of chapterName, chapterCity, and chapterArea,
    constructs URLs, navigates to them, and retrieves data.
    """
    chapter_names = dropdown_values.get("chapterName", [])
    chapter_cities = dropdown_values.get("chapterCity", [])
    chapter_areas = dropdown_values.get("chapterArea", [])
    
    base_url = "https://bnicentraldubai.ae/en-AE/memberlist"

    results = []

    for chapter_name in chapter_names:
        for chapter_city in chapter_cities:
            for chapter_area in chapter_areas:
                # Construct the URL with current combination
                url = (f"{base_url}?chapterName={chapter_name}"
                       f"&chapterCity={chapter_city}"
                       f"&chapterArea={chapter_area}"
                       f"&memberFirstName=&memberKeywords=&memberLastName=&memberCompany=&regionIds=22241")

                print(f"Navigating to URL: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(2)  # Allow time for the page to load

                    # Example: Retrieve page content or specific data
                    # Extract table data
                    rows = await page.evaluate('''
                        () => Array.from(document.querySelectorAll("#memberListTable tr"))
                            .slice(1)  // Skip the header row
                            .map(row => Array.from(row.querySelectorAll("td")).map(cell => cell.innerText.trim()))
                    ''')
                    print(f"Extracted rows: {rows}")

                    # Save data to CSV
                    with open(csv_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        for row in rows:
                            if len(row) == 6:  # Ensure row has all 6 columns
                                writer.writerow(row)

                except Exception as e:
                    print(f"Error navigating to {url}: {e}")

    # Save the results to a JSON file
    with open("results.json", "w") as json_file:
        json.dump(results, json_file, indent=4)
    print("All combinations processed and saved to results.json")
