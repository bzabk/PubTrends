It enables the visualization of interrelated medical articles using the **TF-IDF** and **t-SNE** algorithms.  
The application takes a text file (e.g., in `.txt` format) from the user, containing a list of **PMID** identifiers from the **PubMed** database. Based on those PMIDs, it retrieves additional PMIDs that are linked to them.

For each retrieved **PMID**, the application fetches dataset identifiers from the **GEO DataSets** database that were used in the corresponding publication. Each record in **GEO DataSets** contains the following fields:  
- `Title`  
- `Summary`  
- `Overall_design`  
- `Experiment_type`  
- `Organism`

These fields are merged into a single text string, with punctuation removed. Next, the **TF-IDF** analysis is performed on this processed text, and the resulting vectors are dimensionally reduced using **t-SNE**, allowing for 3D visualization.  
However, it should be noted that if the number of features is too low, some texts may be reduced to the same point in space and become indistinguishable in the 3D plot.