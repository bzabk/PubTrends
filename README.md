# PubTrends: Data Insights for Enhanced Paper Relevance
Application is part of Jetbrains Summer Internship 2025.
Application visualizes how datasets from GSE base related to the same medical article are 
positioned in 3D Dimension. Web App takes as an input from user .txt files
containing pmids user is instered in
```text
30530648
31820734
31018141
38539015
33763704
32572264
31002671
33309739
21057496
.
.
```
To retrieve the data, three URLs are used:

1. **Fetching the list of related datasets:**

   `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=gds&linkname=pubmed_gds&id={pmid}&retmode=json`

   This URL provides a list of datasets linked to a given article.

2. **Fetching detailed information about the datasets:**

   `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id={dataset_id}&retmode=json`

   Based on each dataset's ID, we can retrieve information such as:
   - `Title`
   - `Summary`
   - `Organism`
   - `Experiment_type`
   
   However, to get the **Overall Design** field, we need to query another source:

3. **Fetching Overall Design information:**

   `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_code}&form=xml`

   This URL provides the required **Overall Design** data.

It may happen that a given **PMID** does not have any associated datasets. In such cases, that **PMID** is skipped.
We execute some data cleaning on columns Title,Summary,Overall_design,Experiment_type,Organism and then perform TFIDF ecoding.
Later on, TSNE algorithm is being used to reduce feature vectors to 3 dimension space and display them on the plot.
User can filter specified medical article by selecting specific pmid, then on the plots data points which represent GEO datasets which are
present in the same artcile will be highlighted. Ideally, these points should be close to each other in the 3D space and belong to the same cluster, which would visually confirm the consistency of clustering with respect to the original publications.
 # Instalation Guide
#### Cloning Repository
```
   git clone https://github.com/bzabk/PubTrends.git
   cd PubTrends
```
#### Creating virtual environment
```
    python -m venv venv
    source venv/bin/activate
```
#### Installing dependencies
```
   pip install -r requirements.txt
```