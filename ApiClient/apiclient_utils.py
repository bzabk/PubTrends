from dataclasses import dataclass
from typing import List

import pandas as pd
import xmltodict


@dataclass
class PmData:
    Title: str = None
    Summary: str = None
    Organism: str = None
    Experiment_type: str = None
    GSE_code: str = None
    Overall_design: str = None

async def overall_design_parser(response):
    response_text = await response.text()
    data = xmltodict.parse(response_text)
    return data["MINiML"]["Series"].get("Overall-Design")

async def pmid_to_db_idx_parser(response):
    json_response = await response.json()
    return json_response['linksets'][0]['linksetdbs'][0]['links']

async def info_from_db_idx_parser(response, idx: int):
    json_response = await response.json()
    data_response = json_response['result'][f'{idx}']
    pmid_data = PmData(
        Title=data_response['title'],
        Summary=data_response['summary'],
        Organism=data_response['taxon'],
        Experiment_type=data_response['gdstype'],
        GSE_code=data_response['accession']
    )
    return pmid_data

def load_pmids_from_file():
    pmid_list = set()
    with open('PMIDs_list.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line.isdigit() and int(line) not in pmid_list:
                pmid_list.add(int(line))
    return list(pmid_list)

def combine_all_data_frames(df_db, df_info, df_overall_design):
    combined_1 = df_db.merge(df_info, on='db_idx', how='left')
    combined_2 = combined_1.merge(df_overall_design, on='GSE_code', how='left')
    return combined_2

def create_pmid_to_db_idx_df(pmid_idx: int, db_idx_list: List[int]) -> pd.DataFrame:
    df = pd.DataFrame({"pmid_idx": [pmid_idx] * len(db_idx_list), "db_idx": db_idx_list})
    return df.explode("db_idx").reset_index(drop=True)


def create_db_idx_to_info_df(db_idx_list: List[int], pmdata_list: List[PmData]) -> pd.DataFrame:
    return pd.DataFrame({"db_idx": db_idx_list,
                         "Title": [pmdata.Title for pmdata in pmdata_list],
                         "Summary": [pmdata.Summary for pmdata in pmdata_list],
                         "Organism": [pmdata.Organism for pmdata in pmdata_list],
                         "Experiment_type": [pmdata.Experiment_type for pmdata in pmdata_list],
                         "GSE_code": [pmdata.GSE_code for pmdata in pmdata_list]})

def create_gse_to_overall_design_df(gse_list, overall_design_list) -> pd.DataFrame:
    return pd.DataFrame({"GSE_code": [gse for gse in gse_list],
                         "overall_design": [overall_design for overall_design in overall_design_list]})


def stack_data_frames(list_of_data_frames: List[pd.DataFrame]) -> pd.DataFrame:
    filtered_list_of_data_frames = list(filter(lambda x: x is not None,list_of_data_frames))
    return pd.concat(filtered_list_of_data_frames,axis=0)



