from dataclasses import dataclass
from typing import Optional
import pandas as pd
import requests
import xmltodict
from time import sleep
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


    def __init__(self, error_callback,tqdm_callback):
        self.df = None
        self.error_callback = error_callback
        self.tqdm_callback = tqdm_callback
        self.session = requests.Session()
        self.rows_data = []

    def create_dataframe(self, list_of_pmids: Optional[list[int]] = None) -> None:
        if list_of_pmids is None:
            self._load_pmids_from_file()
        else:
            self._load_pmids_from_user(list_of_pmids=list_of_pmids)
        for idx,pubmed_idx in enumerate(self.pmids):
            dataset_indices = self._get_dataset_idx(int(pubmed_idx))
            for dataset_idx in dataset_indices:
                pmid_data = self._get_info(dataset_idx)
                overall_design = self._get_overall_design(pmid_data.GSE_code)
                if pmid_data is None or overall_design is None:
                    continue
                row_dict = {
                    "Pmid": pubmed_idx,
                    "Geo_dataset_ind": dataset_idx,
                    "GSE_code": pmid_data.GSE_code,
                    "Title": pmid_data.Title,
                    "Summary": pmid_data.Summary,
                    "Overall_design": overall_design,
                    "Experiment_type": pmid_data.Experiment_type,
                    "Organism": pmid_data.Organism
                }

                self.rows_data.append(row_dict)
            #sleep(1)
            self.tqdm_callback((idx+1)/len(self.pmids))

        self.df = pd.DataFrame(self.rows_data)
        if self.df.shape[0] <=10:
            self.error_callback("Data Frame has less than 10 rows, please provide more unique gse_codes")
            return
        #self.df.to_csv("PubMed_data.csv", index=False)

    def _load_pmids_from_file(self) -> None:
        self.pmids = []
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in self.pmids:
                    self.pmids.append(int(line))

    def _load_pmids_from_user(self, list_of_pmids: list[int]) -> None:
        self.pmids = list_of_pmids

    def _get_dataset_idx(self, pmid: int) -> list[int]:
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
            indices = response.json().get('linksets', [])[0].get('linksetdbs', [])[0].get('links', [])
            return [int(idx) for idx in indices]
        except IndexError:
            self.error_callback(f"No datasets found for PMID: {pmid}, pmid abandoned")
            return []
        except Exception:
            self.error_callback(f"Error with PMID: {pmid}, pmid abandoned")
            return []

    def _get_info(self, dataset_idx: int) -> PmData | None:

        base_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            "db": "gds",
            "id": dataset_idx,
            "retmode": "json"
        }
        try:
            response = self.session.get(base_url, params=params)
            response.raise_for_status()
            info_part = response.json()['result'][f'{dataset_idx}']
            pmid_data = self.PmData(
                Title=info_part['title'],
                Summary=info_part['summary'],
                Organism=info_part['taxon'],
                Experiment_type=info_part['gdstype'],
                GSE_code=info_part['accession']
            )
            return pmid_data
        except Exception:
            self.error_callback(f"Error with data from GSE code: {dataset_idx}, pmid abandoned")
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
            self.error_callback(f"Error with getting Overall Design from GSE code: {gse_code}, pmid abandoned")
            return None

    def _save_to_csv(self, df: pd.DataFrame):
        df.to_csv("PubMed_data.csv", index=False)

if __name__ == "__main__":
    api = PubMedAPI()
    start = time.time()
    print(api.get_info_from_pmid("GSE56045"))
