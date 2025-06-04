import os
import re
import csv
import logging
import random
from typing import List
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, stop_after_attempt, wait_fixed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialReportScraper:
    def __init__(self):
        self.target_years = ['2023', '2024', '2025']
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/91.0.4472.114 Safari/537.36"
        ]

    def scrape_company_reports(self, company: str) -> List[dict]:
        company_scrapers = {
            "acousort": self._scrape_acousort,
            "carlsberg": self._scrape_carlsberg,
            "stockwik": self._scrape_stockwik
        }
        scraper = company_scrapers.get(company.lower())
        return scraper() if scraper else []

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _scrape_acousort(self) -> List[dict]:
        base_url = "https://acousort.com/investors/reports/financial-reports/"
        pdfs = []
        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            response = requests.get(base_url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            all_pdfs = []
            for a in soup.find_all('a', href=True):
                href = a['href'].lower()
                if '.pdf' in href:
                    full_url = href if href.startswith('http') else f"https://acousort.com{href}"
                    all_pdfs.append(full_url)
                    if self._is_relevant_report(full_url):
                        pdfs.append({"company": "acousort", "url": full_url})
            logger.info(f"Found {len(pdfs)} Acousort PDFs")
            logger.info(f"All Acousort PDFs: {all_pdfs}")
            if not all_pdfs:
                logger.info(f"Acousort page source: {response.text[:1000]}...")
        except Exception as e:
            logger.warning(f"Acousort failed: {str(e)}")
        return pdfs

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _scrape_carlsberg(self) -> List[dict]:
        base_url = "https://www.carlsberggroup.com/investor-relations/investor-home/company-announcements/"
        pdfs = []
        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            session = requests.Session()
            session.verify = False
            response = session.get(base_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            keywords = ['fy-', 'q1-', 'q2-', 'q3-', 'q4-', 'annual-report', 'financial-statement', 'trading-statement']
            report_links = {a['href'] if a['href'].startswith('http') else f"https://www.carlsberggroup.com{a['href']}"
                           for a in soup.find_all('a', href=True) if any(k in a['href'].lower() for k in keywords)}
            
            logger.info(f"Found {len(report_links)} Carlsberg links: {report_links}")
            for href in list(report_links)[:10]:
                try:
                    sub_response = session.get(href, headers=headers, timeout=30)
                    sub_response.raise_for_status()
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    for a in sub_soup.find_all('a', href=True):
                        sub_href = a['href'].lower()
                        if '.pdf' in sub_href:
                            full_url = sub_href if sub_href.startswith('http') else f"https://www.carlsberggroup.com{sub_href}"
                            if self._is_relevant_report(full_url):
                                pdfs.append({"company": "carlsberg", "url": full_url})
                except Exception as e:
                    logger.warning(f"Carlsberg subpage {href} failed: {str(e)}")
            logger.info(f"Found {len(pdfs)} Carlsberg PDFs")
        except Exception as e:
            logger.error(f"Carlsberg failed: {str(e)}")
        return pdfs

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _scrape_stockwik(self) -> List[dict]:
        base_url = "https://www.stockwik.se/pressmeddelanden"
        pdfs = []
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options)
            driver.get(base_url)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            elements = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
            logger.info(f"Found {len(elements)} Stockwik PDFs with Selenium")
            for elem in elements:
                href = elem.get_attribute('href').lower()
                link_text = elem.text.strip().lower()
                if href and ('(eng)' in link_text or 'eng' in href):
                    full_url = href if href.startswith('http') else f"https://www.stockwik.se{href}"
                    if self._is_relevant_report(full_url):
                        pdfs.append({"company": "stockwik", "url": full_url})
            
            driver.quit()
            logger.info(f"Found {len(pdfs)} relevant Stockwik PDFs")
        except Exception as e:
            logger.error(f"Stockwik failed: {str(e)}")
        return pdfs

    def _is_relevant_report(self, url: str) -> bool:
        year_match = re.search(r'(20\d{2})', url)
        if not year_match or year_match.group(1) not in self.target_years:
            return False
        if year_match.group(1) == "2025" and not re.search(r'(Q[1-2])', url, re.IGNORECASE):
            return False
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def download_pdf(self, url: str) -> bool:
        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {str(e)}")
            return False

    def save_reports_to_csv(self, reports: List[dict], filepath: str = "financial_reports.csv"):
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["company", "url"])
                writer.writeheader()
                writer.writerows(reports)
            logger.info(f"Saved {len(reports)} reports to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {str(e)}")

def main():
    scraper = FinancialReportScraper()
    companies = ["acousort", "carlsberg", "stockwik"]
    all_reports = []

    for company in companies:
        logger.info(f"\n=== Scraping reports for {company} ===")
        reports = scraper.scrape_company_reports(company)
        logger.info(f"Found {len(reports)} reports for {company}")
        for report in reports:
            if scraper.download_pdf(report["url"]):
                all_reports.append(report)

    scraper.save_reports_to_csv(all_reports)
    print("\n=== Final Results ===")
    for i, report in enumerate(all_reports, 1):
        print(f"{i}. {report['company']} | {report['url']}")

if __name__ == "__main__":
    main()