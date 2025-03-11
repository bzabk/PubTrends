from dataclasses import dataclass
from logging import raiseExceptions

import pandas as pd
import requests
import xmltodict


class PubMedAPI:

    @dataclass
    class PmData:
        Title: str
        Summary: str
        Organism: str
        Experiment_type: str
        GSE_code: str

    def __init__(self):
        self.session = requests.Session()
        self.df = pd.DataFrame(columns=["Original_PMID","Related_PMID","Title","Summary","Overall_design","Experiment_type",
                                        "Organism"])

    def create_dataframe(self) -> None:
        with open('PMIDs_list.txt','r') as f:
            for line in f:
                related_pmds = self._get_related_pmids(int(line))
                for pmid in related_pmds:

                    pm_data = self._get_info(pmid)
                    overall_design = self._get_overall_design(pm_data.GSE_code)
                    self.df = pd.concat([self.df, pd.DataFrame([{"Original_PMID": line, "Related_PMID": pmid, "Title": pm_data.Title,
                                                 "Summary": pm_data.Summary, "Overall_design": overall_design,
                                                 "Experiment_type": pm_data.Experiment_type,
                                                 "Organism": pm_data.Organism}])], ignore_index=True)

        self.df.to_csv("PubMed_data.csv",index=False)

    def _load_pmids_from_file(self) -> list[int]:
        pmids = []
        try:
            with open('PMIDs_list.txt','r') as f:

                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        pmids.append(int(line))
        except FileNotFoundError:
            raise

        return pmids

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
        except:
            return []


    def _get_info(self,uid: int) -> PmData:

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
        except:
            return None

    def _get_overall_design(self,gse_code : str) -> str:
        if(gse_code[:3]=="GDS"):
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
        except:
            return None



    def _save_to_csv(self,df: pd.DataFrame):
        df.to_csv("PubMed_data.csv",index=False)


pubmed = PubMedAPI()
pubmed.create_dataframe()