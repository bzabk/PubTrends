import string
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from abc import ABC, abstractmethod


class Processor(ABC):
    @abstractmethod
    def process(self,data):
        pass

class ProcessorFactory:
    """
    Returns an instance of a processor based on the given processor name.
    Parameters:
    processor_name (str): The name of the processor to create.
                          Options are "remove_punctuation", "tsne", "kmeans", "tfidf".
    **kwargs: Additional keyword arguments to pass to the processor's constructor.
    Returns:
    Processor: An instance of the requested processor.
    """
    @staticmethod
    def get_processor(processor_name,**kwargs):
        if processor_name == "remove_punctuation":
            return TextProcessor()
        elif processor_name == "tsne":
            return TSNEProcessor(**kwargs)
        elif processor_name == "kmeans":
            return KMeansProcessor(**kwargs)
        elif processor_name == "tfidf":
            return TFIDFProcessor(**kwargs)

class TextProcessor(Processor):
    """
    Processor class for handling text preprocessing tasks.

    This class is responsible for:
    - Concatenating relevant columns to be passed to the TF-IDF algorithm,
    - Removing punctuation,
    - Standardizing 'Experiment_type' strings,
    - Setting the 'is_selected' flag for each row.
    """
    def process(self, data):
        data["Experiment_type"] = data["Experiment_type"].apply(self._standardize_experiment_type)
        data = self._concatenate_text(data)
        data["Text"] = data["Text"].apply(lambda x: self._remove_punctuation(x))
        data = self._set_selected(data)
        return data
    @staticmethod
    def _set_selected(data):
        data["is_selected"]=1
        return data
    @staticmethod
    def _concatenate_text(data):
        data["Text"] = data[
            ["Title", "Summary", "Overall_design", "Experiment_type", "Organism"]
        ].apply(lambda x: ' '.join(x), axis=1)
        return data
    @staticmethod
    def _remove_punctuation(text) -> str:
        return text.translate(str.maketrans('', '', string.punctuation))
    @staticmethod
    def _standardize_experiment_type(text: str) -> str:
        """
        In some cases, the only difference between two experiment-type strings is the order
        of their phrases (e.g., “Genome binding/occupancy profiling” followed by “Expression
        profiling” vs. the reverse). This function standardizes such strings by sorting
        their phrases so they match.

        For example:
        1) 'Genome binding/occupancy profiling by high throughput sequencing;
           Expression profiling by high throughput sequencing;
           Methylation profiling by high throughput sequencing'
        2) 'Genome binding/occupancy profiling by high throughput sequencing;
           Methylation profiling by high throughput sequencing;
           Expression profiling by high throughput sequencing'

        Here, the only variation is the order of the three profiling phrases,
        so we treat these as identical.

        In some cases, an additional word like 'Other' appears in one of the strings,
        e.g.:
        1) 'Expression profiling by high throughput sequencing; Other'
        2) 'Expression profiling by high throughput sequencing'

        We similarly assume these represent the same experiment type.
        """
        text = text.split(";")
        text = [t.strip() for t in text]
        text.sort()
        if "Other" in text:
            text.remove("Other")
        text = [t for t in text if t.strip() != "Other"]
        new_text = ";".join(text)
        return new_text

class TSNEProcessor(Processor):
    """
    Processor class for performing t-SNE dimensionality reduction on data.
    """
    def __init__(self,perplexity=30):
        """
        Initializes the TSNEProcessor with a t-SNE instance.

        Parameters:
        perplexity (int): The perplexity parameter for t-SNE. Default is 30.
        """
        self.tsne_reduction = TSNE(n_components=3,perplexity=perplexity)
    def process(self,data):
        """
        Applies t-SNE dimensionality reduction to the input data.

        Parameters:
        data (iterable): The input data to be reduced.

        Returns:
        numpy.ndarray: The reduced data.
        """
        return self.tsne_reduction.fit_transform(data)

class KMeansProcessor(Processor):
    """
    Processor class for performing K-Means clustering on data.
    """
    def __init__(self,n_clusters=8):
        """
        Initializes the KMeansProcessor with a KMeans instance.

        Parameters:
        n_clusters (int): The number of clusters to form. Default is 8.
        """
        self.cluster = KMeans(n_clusters=n_clusters)
    def process(self,data):
        """
        Applies K-Means clustering to the input data.

        Parameters:
        data (iterable): The input data to be clustered.

        Returns:
        numpy.ndarray: The cluster centers.
        """
        self.cluster.fit_transform(data)

class TFIDFProcessor(Processor):
    """
    Processor class for transforming text data into TF-IDF features.
    """
    def __init__(self,max_features=100):
        """
        Initializes the TFIDFProcessor with a TfidfVectorizer.

        Parameters:
        max_features (int): The maximum number of features to consider. Default is 100.
        """
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english', min_df=2)
    def process(self,data):
        """
        Transforms the input data into TF-IDF features.

        Parameters:
        data (iterable): The input data to be transformed.

        Returns:
        numpy.ndarray: The transformed data as a dense array.
        """
        return self.vectorizer.fit_transform(data).toarray()





