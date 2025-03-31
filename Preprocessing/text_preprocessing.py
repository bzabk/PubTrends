import string
import random
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

random.seed(42)

class RemovePunctuationTransformer(BaseEstimator, TransformerMixin):
        """
        A custom scikit-learn like transformer for removing punctuation from text data.
        It is being used as preprocessing before running TF-IDF encoding on text data.
        """

        def __init__(self):
            pass

        def fit(self, X, y=None):
            return self

        def transform(self, X, y=None):
            if isinstance(X, pd.Series):
                X_transformed = X.apply(lambda x: x.translate(str.maketrans('', '', string.punctuation)))
            else:
                X_transformed = pd.Series(X).apply(lambda x: x.translate(str.maketrans('', '', string.punctuation)))
            return X_transformed

        def fit_transform(self, X, y=None):
            return self.fit(X, y).transform(X)


class TextPipeline:
    '''
    Main pipeline for processing raw data into a format that can visualized on a 3D scatter plot
    Pipeline consists of 2 main steps:
    1. Text processing pipeline: Remove punctuation and vectorize text data
    2. TF-IDF encoding
    Next k_means and tsne are being fitted on the processed data

    '''
    def __init__(self,n_clusters=8,max_features=100,perplexity=30):
        self.pipeline = Pipeline([])
        self.cluster = KMeans(n_clusters=n_clusters)
        self.punctuation_remover = RemovePunctuationTransformer()
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english', min_df=2)
        self.tsne_reduction = TSNE(n_components=3,perplexity=perplexity)

        self.text_processing_pipeline = Pipeline([
            ('remove_punctuation', self.punctuation_remover),
            ('vectorizer', self.vectorizer)
        ])

        self.is_fitted_text_processing_pipeline = False
        self.is_fitted_cluster = False
        self.is_fitted_tsne = False

    def fit_text_processing_pipeline(self,X):
        self.is_fitted_text_processing_pipeline = True
        self.text_processing_pipeline.fit(X)
        return self

    def fit_kmeans(self,X):
        self.cluster.fit(X)
        return self

    def fit_tsne(self,X):
        self.tsne_reduction.fit(X)
        return self

    def transform_text_processing_pipeline(self,X):
        if not self.is_fitted_text_processing_pipeline:
            raise ValueError("Pipeline not fitted")
        return self.text_processing_pipeline.transform(X)

    def transform_kmeans(self,X):
        if not self.is_fitted_cluster:
            raise ValueError("Cluster not fitted")
        return self.cluster.transform(X)

    def transform_tsne(self,X):
        if not self.is_fitted_tsne:
            raise ValueError("TSNE not fitted")
        return self.tsne_reduction.transform(X)

    def fit_transform_text_processing_pipeline(self,X):
        return self.text_processing_pipeline.fit_transform(X)

    def fit_transform_kmeans(self,X):
        return self.cluster.fit_transform(X)

    def fit_transform_tsne(self,X):
        return self.tsne_reduction.fit_transform(X)




