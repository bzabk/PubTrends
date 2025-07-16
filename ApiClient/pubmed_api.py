from dataclasses import dataclass
from typing import Optional
import pandas as pd
import requests
import xmltodict
from .singleton import Singleton
from .observer import Observable

class PubMedAPI(Observable,metaclass=Singleton):
    """
    This class is responsible for generating a DataFrame from a text file containing a list of pmids.
    """
    MIN_SIZE=10
    @dataclass
    class PmData:
        """
        Holds metadata for a specific dataset, identified by a GSE code.
        Includes:
        - Title
        - Summary
        - Organism
        - Experiment Type
        - GSE Code
        - Overall Design
        """
        Title: str
        Summary: str
        Organism: str
        Experiment_type: str
        GSE_code: str
        Overall_design: str = None


    def __init__(self):
        super().__init__()
        self.df = None
        self.session = requests.Session()
        self.rows_data = []
        self.pmids = []

    def create_dataframe(self, list_of_pmids: Optional[list[int]] = None) -> None:
        """
        Processes a list of PMIDs provided by the user (from a .txt file) and constructs a DataFrame
        by retrieving dataset information for each valid PMID. For each PMID, the function iterates
        through all related datasets, collects their details, and updates a progress bar. If the final
        DataFrame contains fewer than 10 rows, an error message is displayed.

        :param list_of_pmids: List of PMIDs to process.
        """
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
            self.notify(event_type="progress",measure=(idx+1)/len(self.pmids))

        self.df = pd.DataFrame(self.rows_data).drop_duplicates(subset=["Pmid", "Geo_dataset_ind"])
        if self.df.shape[0] <=PubMedAPI.MIN_SIZE:
            self.notify(event_type="error",message="Data Frame has less than 10 rows, please provide more unique gse_codes")
            return
        #self.df.to_csv("PubMed_data.csv", index=False)

    def _load_pmids_from_file(self) -> None:
        """
        Loads a list of PMIDs from a file named 'PMIDs_list.txt'
        """
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in self.pmids:
                    self.pmids.append(int(line))

    def _load_pmids_from_user(self, list_of_pmids: list[int]) -> None:
        self.pmids = list_of_pmids

    def _get_dataset_idx(self, pmid: int) -> list[int]:
        """
        Returns a list of datasets related to the given PMID by calling an API function.
        If no datasets are found for the provided PMID, an empty list is returned,
        `error_callback` is invoked to display a App error message, and
        the method proceeds to process the next PMID.
        :param pmid: The PubMed ID for which to retrieve related datasets.
        :return: A list of datasets related to the given PMID.
        """
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
            self.notify(event_type="error",message=f"No datasets found for PMID: {pmid}, pmid abandoned")
            return []
        except Exception:
            self.notify(event_type="error",message=f"Error with PMID: {pmid}, pmid abandoned")
            return []

    def _get_info(self, dataset_idx: int) -> PmData | None:
        """
        Retrieves information about a dataset (including Title, Summary, Organism,
        Experiment Type, and the full GSE code) based on the provided dataset index.

        :param dataset_idx: The index of the dataset to retrieve.
        :return: A PmData object containing the dataset’s details, or None if
                 any problems occur.
        """
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
            self.notify(event_type="error",message=f"Error with data from GSE code: {dataset_idx}, pmid abandoned")
            return None

    def _get_overall_design(self, gse_code: str) -> str | None:
        """
        Retrieves the overall design of a dataset based on the provided GSE code.
        :param gse_code:
        :return: Overall design of the dataset, or None if the API connection fails.
        """
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
            self.notify(event_type="error",message=f"Error with getting Overall Design from GSE code: {gse_code}, pmid abandoned")
            return None


    @staticmethod
    def _save_to_csv(df: pd.DataFrame):
        df.to_csv("PubMed_data.csv", index=False)

