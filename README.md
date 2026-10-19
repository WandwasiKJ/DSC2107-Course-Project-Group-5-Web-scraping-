# Group 5 — Jiji Uganda Data Mining and Data Wrangling Project

## 1. Project Overview

This project analyses publicly available product listings from [Jiji Uganda](https://jiji.ug/) as part of the Data Mining and Data Wrangling assignment.

The project uses Python to collect, clean, store, explore, and analyse product listing data. It focuses on mobile phones and two additional product categories verified and documented by the group.

The analysis aims to identify price patterns, product characteristics, changes in listings over time, and relationships between variables such as product condition and price.

**Project:** Jiji Uganda Product Listings Analysis  
**Group 5 Members:**     **1.WANDWASI KEVIN JOEL**   
         **2.NDAMBIRE HARRY BOSCO**   
         **3.AGABA JONATHAN**   
         **4.MUSIIME MIRACLE**    
         **5.NAKITTO FAVOUR**  
**Course:** Data Mining and Data Wrangling  
**Programming language:** Python  
**Analysis environment:** Jupyter Notebook

## 2. Project Objectives

The main objectives are to:

- Inspect the website structure, available pages, and applicable `robots.txt` restrictions before collecting data.
- Collect permitted public listing information from the selected product categories.
- Clean and preprocess the collected data using pandas.
- Store raw and cleaned data in organised files and a relational database.
- Perform exploratory data analysis (EDA) using statistical summaries and visualisations.
- Investigate product prices, product conditions, brands, listing activity, and price variation.
- Present findings, limitations, and recommendations in a reproducible notebook and final report.

## 3. Data Collection

The project collects publicly displayed listing information from Jiji Uganda, subject to website rules and responsible data collection practices.

### Data fields

The intended dataset includes the following fields where publicly available:

| Field | Description |
|---|---|
| `title` | Product listing title |
| `price` | Advertised product price |
| `condition` | Product condition, where available |
| `location` | Advertised location |
| `posting_date` | Listing date, where available |
| `scraped_at` | Date and time the listing was collected |
| `category` | Product category |
| `listing_url` | Listing reference, if retained and permitted |

Unavailable fields should be recorded as missing rather than invented. Personal seller information, including names and phone numbers, is excluded from the analytical dataset.

### Collection requirements

The assignment's target is to collect at least 500 listings per run across seven consecutive days, covering Days 4–10 of the assignment schedule. The group should document the actual number of records collected on each day and explain any shortfall.

Daily raw data should be preserved separately so that the collection history can be audited and analysed over time.

### Responsible scraping policy

The collection process must follow these rules:

1. Inspect `robots.txt`, relevant website terms, and applicable access restrictions before scraping.
2. Use a descriptive User-Agent where automated access is permitted.
3. Apply a delay of approximately 2–5 seconds between requests and keep daily request volumes within the assignment's recommended limit of approximately 1,000 requests.
4. Do not collect unnecessary personal or sensitive information.
5. Do not bypass CAPTCHAs, access controls, or other anti-bot mechanisms.
6. **Stop-on-block policy:** If the website responds with a CAPTCHA, HTTP 403, HTTP 429, or another clear blocking signal, stop scraping immediately. Do not retry, rotate identities, or attempt to circumvent the restriction.
7. Record collection dates, errors, and limitations accurately. Never fabricate listings to meet the target.

## 4. Project Structure

The project directory should follow a structure similar to the one below. Replace example filenames with the actual files included in the submission.

```text
group-5-jiji-analysis/
│
├── README.md
├── requirements.txt
│
├── notebooks/
│   └── jiji_uganda_analysis.ipynb
│
├── src/
│   ├── scraper.py
│   ├── cleaning.py
│   └── database.py
│
├── data/
│   ├── raw/
│   │   ├── listings_day_04.csv
│   │   ├── listings_day_05.csv
│   │   └── ...
│   │
│   └── processed/
│       └── cleaned_listings.csv
│
├── database/
│   └── jiji_listings.db
│
├── reports/
│   └── final_report.pdf
│
└── presentation/
    └── group_5_presentation.pptx
```

This is a suggested structure, not a claim that every listed file has already been created. Keep only the folders and files that exist in the final submission.

## 5. Technologies and Libraries

The project uses the following tools, as applicable:

- **Python:** Data processing and analysis.
- **pandas:** Data cleaning, transformation, grouping, and aggregation.
- **NumPy:** Numerical calculations.
- **Matplotlib:** Data visualisation.
- **Seaborn:** Statistical visualisation.
- **Jupyter Notebook:** Reproducible analysis and documentation.
- **SQLite:** Relational storage for collected and cleaned data.
- **Requests and BeautifulSoup:** Website requests and HTML parsing, where automated access is permitted.

## 6. Installation and Setup

### Prerequisites

Install Python 3.10 or later and ensure that pip is available.

### Step 1: Clone or download the project

If the project is hosted on GitHub:

```bash
git clone <repository-url>
cd group-5-jiji-analysis
```

Alternatively, download and extract the project folder, then open a terminal in that folder.

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### Step 3: Install dependencies

If a `requirements.txt` file is available:

```bash
pip install -r requirements.txt
```

Otherwise, install the required analysis libraries:

```bash
pip install pandas numpy matplotlib seaborn jupyter requests beautifulsoup4
```

SQLite support is included with most standard Python installations.

### Step 4: Launch Jupyter Notebook

```bash
jupyter notebook
```

Open `notebooks/jiji_uganda_analysis.ipynb` or the notebook's actual location in your project.

### Step 5: Load the dataset

Check that the input paths used in the notebook point to the actual raw or cleaned data files. Run the notebook cells in order, starting with imports and data loading.

If the dataset is not included in the repository, obtain it from the group's authorised project files before running the analysis.

## 7. Data Cleaning and Preprocessing

Before analysis, the collected data should be checked and prepared through the following steps:

1. Inspect the dataset dimensions, column names, and data types.
2. Remove duplicate listings using an appropriate listing identifier or URL, where available.
3. Standardise column names and text formats.
4. Convert prices into numeric values while preserving the original currency information.
5. Handle missing prices, conditions, locations, and posting dates appropriately.
6. Check for implausible values and potential outliers without automatically assuming that every extreme price is an error.
7. Standardise category labels and date formats.
8. Preserve the collection timestamp for temporal analysis.
9. Save the cleaned dataset separately from the raw files.

All cleaning decisions should be documented in the notebook so that the process is transparent and reproducible.

## 8. Exploratory Data Analysis

The Jupyter Notebook should answer the five core assignment questions and one additional question proposed by Group 5.

The analysis should cover the relevant questions specified in the assignment, including:

- **Price distribution:** Examine typical prices, spread, skewness, and possible outliers.
- **Price and listing popularity:** Investigate the relationship between price and any available, valid popularity measure.
- **Changes over time:** Examine changes in listing counts, prices, or other suitable measures across collection dates.
- **Brands and listing characteristics:** Compare available brands and other relevant listing attributes.
- **Discounts:** Analyse verifiable original-price and discounted-price information, where available.
- **Relative price variability:** Compare price dispersion across suitable categories or product groups.
- **Group 5 additional question:** Investigate the relationship between product condition and price.

The group must ensure that each analysis is supported by the variables actually present in the dataset. If ratings, reviews, popularity indicators, or discount information are unavailable or incomplete, this limitation must be explained rather than replaced with invented values.

### Visualisation requirements

The notebook must contain at least six clear, labelled charts. Suitable visualisations include:

1. Histogram of product prices.
2. Box plot of prices by product condition.
3. Scatter plot of price against a valid popularity measure, if available.
4. Line chart of listing counts or median prices by collection date.
5. Bar chart comparing listing counts across brands or categories.
6. Bar chart showing verifiable discount records, if sufficient data exist.
7. Comparison of relative price variability across product groups.

Every chart should have a descriptive title, labelled axes, readable values, and an appropriate legend where needed. Each visualisation should be followed by a short interpretation explaining what the results show.

## 9. Database and Data Storage

The project should use SQLite or another approved relational database to organise the collected information.

The assignment requires at least two database tables. A possible design is:

- **`listings`** — Listing identifiers, product titles, prices, conditions, locations, categories, and permitted listing references.
- **`collection_logs`** — Collection dates, run identifiers, record counts, completion status, and errors.

The final schema should match the actual implementation. Document each table's purpose, columns, data types, and primary or foreign keys where applicable.

Raw daily files should remain available for auditing, while cleaned data should be stored separately for analysis.

## 10. Reproducibility

To reproduce the analysis:

1. Set up the Python environment and install the dependencies.
2. Obtain the permitted raw data files.
3. Confirm that file paths and database locations are correct.
4. Open the Jupyter Notebook.
5. Run the notebook cells in sequence.
6. Review the printed data summaries, statistical results, and charts.
7. Compare the outputs with the group's final report.

Re-running the notebook should reproduce the analysis from the same input data, subject to library versions and any documented random operations.

Data collection is a separate activity from analysis and must comply with the responsible scraping policy. Do not initiate a new scrape merely to reproduce the notebook's results.

## 11. Limitations

The results depend on the listings visible and accessible during the collection period. Potential limitations include:

- Missing or incomplete product attributes.
- Advertised prices that may not equal final transaction prices.
- Duplicate, expired, or changed listings.
- Incomplete posting dates or historical information.
- Limited availability of popularity and discount indicators.
- Differences in the number of listings collected across dates or categories.
- Website restrictions that prevent completing the planned collection schedule.

The report should state the actual collection dates, dataset size, missing-data patterns, and any deviations from the assignment requirements. Findings should not be generalised beyond what the collected data can support.

## 12. Expected Deliverables

The final submission should contain:

- [ ] README documentation.
- [ ] Python source code, where applicable.
- [ ] Raw daily datasets.
- [ ] Cleaned analytical dataset.
- [ ] Database containing at least two documented tables.
- [ ] Jupyter Notebook answering the five core questions and one additional Group 5 question.
- [ ] At least six labelled charts.
- [ ] Final written report.
- [ ] Group presentation.
- [ ] Documentation of website reconnaissance, `robots.txt` findings, selectors, pagination, and responsible collection procedures.
- [ ] Honest reporting of collection counts, errors, and limitations.

## 13. Conclusion

This project demonstrates the application of data mining and data wrangling techniques to publicly available online marketplace listings. By combining responsible data collection, data cleaning, relational storage, exploratory analysis, and visualisation, Group 5 aims to produce transparent and evidence-based insights into product pricing and listing characteristics on Jiji Uganda.

All conclusions should be based on the collected data, and all collection and analysis limitations should be documented clearly.

---

**Group 5 | Data Mining and Data Wrangling | Jiji Uganda**
