### Application Description

The application enables the visualization of interrelated medical articles using the **TF-IDF** and **t-SNE** algorithms. The application takes a text file (e.g., in `.txt` format) from the user, containing a list of **PMID** identifiers from the **PubMed** database. Based on these PMIDs, it retrieves additional PMIDs that are linked to them.

For each retrieved **PMID**, the application fetches dataset identifiers from the **GEO DataSets** database that were used in the corresponding publication. Each record in **GEO DataSets** contains the following fields:

- `Title`  
- `Summary`  
- `Overall_design`  
- `Experiment_type`  
- `Organism`  

These fields are merged into a single text string, with punctuation removed. Next, **TF-IDF** analysis is performed on this processed text, and the resulting vectors are dimensionally reduced using **t-SNE**, allowing for 3D visualization. 

However, it should be noted that if the number of features is too low, some texts may be reduced to the same point in space and become indistinguishable in the 3D plot.

### Data Retrieval

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

### Issues and Notes

During the development of the application, I encountered a situation where the first API used to fetch the list of related datasets stopped working. When the user provides their own list of PMIDs, they should submit a `.txt` file formatted like the one below:

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
.
```
It may happen that a given **PMID** does not have any associated datasets. In such cases, that **PMID** is skipped.