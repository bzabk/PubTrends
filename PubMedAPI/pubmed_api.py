from dataclasses import dataclass
from typing import Optional
import pandas as pd
import requests
import xmltodict
from time import sleep
from bs4 import BeautifulSoup
import time


class PubMedAPI:
    @dataclass
    class PmData:
        Title: str
        Summary: str
        Organism: str
        Experiment_type: str
        GSE_code: str
        Overall_design: str = None

        def __str__(self):
            return f"Title: {self.Title}\nSummary: {self.Summary}\nOrganism: {self.Organism}\nExperiment_type: {self.Experiment_type}\nGSE_code: {self.GSE_code}\nOverall_design: {self.Overall_design}"

    def __init__(self, error_callback):
        self.error_callback = error_callback
        self.session = requests.Session()
        self.df = pd.DataFrame(
            columns=["Original_PMID", "Related_PMID", "Title", "Summary", "Overall_design", "Experiment_type",
                     "Organism"])
        self.rows_data = []

    def create_dataframe(self, list_of_pmids: Optional[list[int]] = None) -> None:
        if list_of_pmids is None:
            self._load_pmids_from_file()
        else:
            self._load_pmids_from_user(list_of_pmids=list_of_pmids)
        for pubmed_idx in self.pmids:
            related_pmds = self._get_related_pmids(int(pubmed_idx))
            for pmid in related_pmds:
                pm_data = self._get_info(pmid)
                overall_design = self._get_overall_design(pm_data.GSE_code)
                if pm_data is None or overall_design is None:
                    continue
                row_dict = {
                    "Original_PMID": pubmed_idx,
                    "Related_PMID": pmid,
                    "GSE_code": pm_data.GSE_code,
                    "Title": pm_data.Title,
                    "Summary": pm_data.Summary,
                    "Overall_design": overall_design,
                    "Experiment_type": pm_data.Experiment_type,
                    "Organism": pm_data.Organism
                }

                self.rows_data.append(row_dict)
            sleep(1)

        self.df = pd.DataFrame(self.rows_data)
        # self.df.to_csv("PubMed_data.csv", index=False)

    def _load_pmids_from_file(self) -> list[int]:
        self.pmids = []
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in self.pmids:
                    self.pmids.append(int(line))

    def _load_pmids_from_user(self, list_of_pmids: list[int]) -> list[int]:
        self.pmids = list_of_pmids

    def _get_related_pmids(self, pmid: int) -> list[int]:
        base_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
        params = {
            "dbfrom": "pubmed",
            "db": "gds",
            "linkname": "pubmed_gds",
            "id": pmid,
            "retmode": "json"
        }
        try:
            response = self.session.get(base_url, params=params)
            response.raise_for_status()
            links = response.json().get('linksets', [])[0].get('linksetdbs', [])[0].get('links', [])
            return [int(link) for link in links]
        except IndexError:
            self.error_callback(f"No related PMIDs found for PMID: {pmid}, pmid abandoned")
            return []
        except Exception:
            self.error_callback(f"Error with PMID: {pmid}, pmid abandoned")
            return []

    def _get_info(self, uid: int) -> PmData | None:

        base_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            "db": "gds",
            "id": uid,
            "retmode": "json"
        }
        try:
            response = self.session.get(base_url, params=params)
            response.raise_for_status()
            info_part = response.json()['result'][f'{uid}']
            pm_data = self.PmData(
                Title=info_part['title'],
                Summary=info_part['summary'],
                Organism=info_part['taxon'],
                Experiment_type=info_part['gdstype'],
                GSE_code=info_part['accession']
            )
            return pm_data
        except Exception:
            self.error_callback(f"Error with data from GSE code: {uid}, pmid abandoned")
            return None

    def _get_overall_design(self, gse_code: str) -> str | None:
        if gse_code[:3] == "GDS":
            gse_code = "GSE" + gse_code[3:]
        base_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
        params = {
            "acc": gse_code,
            "form": "xml"
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = xmltodict.parse(response.content)
            return data["MINiML"]["Series"].get("Overall-Design")
        except Exception:
            self.error_callback(f"Error with data from GSE code: {gse_code}, pmid abandoned")
            return None

    def _save_to_csv(self, df: pd.DataFrame):
        df.to_csv("PubMed_data.csv", index=False)

    # ----------------------------Getting Info By Web Scraping--------------------------------

    def create_dataframe_by_web_scraping(self, list_of_pmids: Optional[list[int]] = None) -> None:

        for pubmed_idx in list_of_pmids:
            pass

    def get_gse_from_website(self, uid: int) -> str:
        base_url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        response = self.session.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        button = soup.find('button', {'class': 'supplemental-data-actions-trigger'})
        if button:
            gse_code = button.get('aria-controls').split('-')[-1]
            return gse_code
        return None

    def get_info_from_pmid(self, gse_code: str) -> PmData:
        base_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_code}"
        response = self.session.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_td = soup.find("td", text="Title")
        if title_td:
            parent_row = title_td.find_parent("tr")
            target_td = parent_row.find("td", style=lambda s: s and "text-align: justify" in s)
            title = target_td.get_text(strip=True)

        organism_td = soup.find("td", text="Organism")
        if organism_td:
            parent_row = organism_td.find_parent("tr")
            target_td = parent_row.find("a")
            organism = target_td.get_text(strip=True)

        summary_td = soup.find("td", text="Summary")
        if summary_td:
            parent_row = summary_td.find_parent("tr")
            target_td = parent_row.find("td", style=lambda s: s and "text-align: justify" in s)
            summary = target_td.get_text(strip=True)

        experiment_td = soup.find("td", text="Experiment type")
        if experiment_td:
            parent_row = experiment_td.find_parent("tr")
            experiment = parent_row.find_all("td")[1].get_text(strip=True)

        overall_design_td = soup.find("td", text="Overall design")
        if overall_design_td:
            parent_row = overall_design_td.find_parent("tr")
            target_td = parent_row.find("td", style=lambda s: s and "text-align: justify" in s)
            overall_design = target_td.get_text(strip=True)
        pm_data = self.PmData(
            Title=title,
            Summary=summary,
            Organism=organism,
            Experiment_type=experiment,
            Overall_design=overall_design,
            GSE_code=gse_code
        )
        return pm_data


if __name__ == "__main__":
    api = PubMedAPI()
    start = time.time()
    print(api.get_info_from_pmid("GSE56045"))
