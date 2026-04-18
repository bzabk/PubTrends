import pandas as pd

from api_client.dtos import CachedDatasetRecord, DatasetSummaryDto, OverallDesignDto


class ApiDataFrameMapper:

    @staticmethod
    def create_dataframe_from_single_pmid(
            pmid: str,
            summaries: list[DatasetSummaryDto],
            overall_designs: list[OverallDesignDto],
    ) -> pd.DataFrame:
        if not summaries or not overall_designs or not pmid:
            return pd.DataFrame(columns=ApiDataFrameMapper.dataframe_columns())

        summary_rows = [
            {
                "db_idx": summary.db_idx,
                "Title": summary.title,
                "Summary": summary.summary,
                "Organism": summary.organism,
                "Experiment_type": summary.experiment_type,
                "GSE_code": summary.gse_code,
            }
            for summary in summaries
        ]
        overall_design_rows = [
            {
                "GSE_code": overall_design.gse_code,
                "Overall_design": overall_design.overall_design,
            }
            for overall_design in overall_designs
        ]
        pmid_rows = [
            {
                "Pmid": int(pmid),
                "db_idx": int(summary.db_idx),
            }
            for summary in summaries
        ]

        summary_df = pd.DataFrame(summary_rows).drop_duplicates(subset=["db_idx"])
        overall_design_df = pd.DataFrame(overall_design_rows).drop_duplicates(
            subset=["GSE_code"]
        )
        pmid_df = pd.DataFrame(pmid_rows)

        return pmid_df.merge(summary_df, on="db_idx", how="left").merge(
            overall_design_df, on="GSE_code", how="left"
        )

    @staticmethod
    def combine_dataframes(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        filtered_dataframes = [
            dataframe
            for dataframe in dataframes
            if dataframe is not None and not dataframe.empty
        ]
        if not filtered_dataframes:
            return pd.DataFrame(columns=ApiDataFrameMapper.dataframe_columns())
        return pd.concat(filtered_dataframes, axis=0, ignore_index=True)

    @staticmethod
    def records_to_dataframe(records: list[CachedDatasetRecord]) -> pd.DataFrame:
        if not records:
            return pd.DataFrame(columns=ApiDataFrameMapper.dataframe_columns())

        rows = [
            {
                "Pmid": record.pmid,
                "db_idx": record.db_idx,
                "Title": record.title,
                "Summary": record.summary,
                "Organism": record.organism,
                "Experiment_type": record.experiment_type,
                "GSE_code": record.gse_code,
                "Overall_design": record.overall_design,
            }
            for record in records
        ]
        return pd.DataFrame(rows, columns=ApiDataFrameMapper.dataframe_columns())

    @staticmethod
    def dataframe_to_records(dataframe: pd.DataFrame
    ) -> list[CachedDatasetRecord]:
        return [
            CachedDatasetRecord(
                pmid=row.Pmid,
                db_idx=row.db_idx,
                title=row.Title,
                summary=row.Summary,
                organism=row.Organism,
                experiment_type=row.Experiment_type,
                gse_code=row.GSE_code,
                overall_design=row.Overall_design,
            )
            for row in dataframe.itertuples(index=False)
        ]


    @staticmethod
    def dataframe_columns() -> list[str]:
        return [
            "Pmid",
            "db_idx",
            "Title",
            "Summary",
            "Organism",
            "Experiment_type",
            "GSE_code",
            "Overall_design",
        ]