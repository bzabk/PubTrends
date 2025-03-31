from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

"""
Determine the optimal number of clusters for the KMeans algorithm on a toy dataset
using the inertia and silhouette methods.
Both methods indicate that the optimal number of clusters is between 8 and 10.
These functions are not used elsewhere in the project; they were executed separately
to establish a default value for the `n_clusters` parameter in Streamlit's number_input.
"""

def sillhoute_method(kmax: int, X):
    sil = []
    for i in range(2, kmax + 1):
        kmeans = KMeans(n_clusters=i)
        kmeans.fit(X)
        labels = kmeans.labels_
        sil.append(silhouette_score(X, labels, metric='euclidean'))
    plt.plot(range(2, kmax + 1), sil)
    plt.show()

def inertia_method(kmax: int, X):
    wcss = []
    for i in range(2, kmax + 1):
        kmeans = KMeans(n_clusters=i)
        kmeans.fit(X)
        wcss.append(kmeans.inertia_)
    plt.plot(range(2, kmax + 1), wcss)
    plt.show()




