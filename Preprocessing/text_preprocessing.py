import string
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE


class RemovePunctuationTransformer(BaseEstimator, TransformerMixin):

    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        X_transformed = X.apply(lambda x: x.translate(str.maketrans('', '', string.punctuation)))
        return X_transformed

    def fit_transform(self, X, y=None):
        return self.fit(X, y).transform(X)


class TextPipeline:

    def __init__(self,n_clusters=8,max_features=100):
        self.pipeline = Pipeline()
        self.cluster = KMeans(n_clusters=n_clusters)
        self.punctuation_remover = RemovePunctuationTransformer()
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english', min_df=2)
        self.tsne_reduction = TSNE(n_components=3)

        self.text_pipeline = Pipeline([
            ('remove_punctuation', self.punctuation_remover),
            ('vectorizer', self.vectorizer)
        ])
        self.text_cluster_pipeline = Pipeline([
            ('text_pipeline', self.text_pipeline),
            ('cluster', self.cluster)
        ])
        self.tsne_pipeline = Pipeline([
            ('dimensionality_reduction',self.text_pipeline),
            ('tsne', self.tsne_reduction)
        ])

        self.is_fitted_text_pipeline = False
        self.is_fitted_text_cluster_pipeline = False
        self.is_fitted_tsne_pipeline = False

    def fit_text_pipeline(self,X):
        self.is_fitted_text_pipeline = True
        self.text_pipeline.fit(X)
        return self
    def fit_text_cluster_pipeline(self,X):
        self.is_fitted_text_cluster_pipeline = True
        self.text_cluster_pipeline.fit(X)
        return self
    def fit_tsne_pipeline(self,X):
        self.is_fitted_tsne_pipeline = True
        self.tsne_pipeline.fit(X)
        return self

    def transform_text_pipeline(self,X):
        if not self.is_fitted_text_pipeline:
            raise ValueError("Pipeline not fitted")
        return self.text_pipeline.transform(X)

    def transform_text_cluster_pipeline(self,X):
        if not self.is_fitted_text_cluster_pipeline:
            raise ValueError("Pipeline not fitted")
        return self.text_cluster_pipeline.transform(X)

    def transform_tsne_pipeline(self,X):
        if not self.is_fitted_tsne_pipeline:
            raise ValueError("Pipeline not fitted")
        return self.tsne_pipeline.transform(X)

    def fit_transform_text_pipeline(self,X):
        return self.fit_text_pipeline(X).transform_text_pipeline(X)

    def fit_transform_text_cluster_pipeline(self,X):
        return self.fit_text_cluster_pipeline(X).transform_text_cluster_pipeline(X)

    def fit_transform_tsne_pipeline(self,X):
        return self.fit_tsne_pipeline(X).transform_tsne_pipeline(X)




