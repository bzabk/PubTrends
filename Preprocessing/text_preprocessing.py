import string
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.cluster import DBSCAN
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

    def __init__(self):
        self.pipeline = Pipeline()
        self.cluster = DBSCAN(eps=0.5, min_samples=10)
        self.punctuation_remover = RemovePunctuationTransformer()
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english', min_df=2)
        self.tsne = TSNE(n_components=3)

        self.pipeline = Pipeline([
            ('remove_punctuation', self.punctuation_remover),
            ('vectorizer', self.vectorizer),
            ('clusterting',self.cluster),
            ('dimensionality_reduction', self.tsne)
        ])

        self.is_fitted = False

    def fit(self, X, y=None):
        self.pipeline.fit(X)
        self.is_fitted = True

    def transform(self, X):
        if self.is_fitted == False:
            raise ValueError("Pipeline not fitted")
        return self.pipeline.transform(X)

    def get_cluster_labels(self):
        if not self.is_fitted:
            raise ValueError("Pipeline not fitted")
        return self.cluster.labels_




