from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

def sillhoute_method(kmax: int,X):
    sil=[]
    for i in range(1,kmax+1):
        kmeans = KMeans(n_clusters=i)
        kmeans.fit(X)
        labels = kmeans.labels_
        sil.append(silhouette_score(X, labels, metric = 'euclidean'))
    plt.plot(range(1,kmax+1),sil)

def inertia_method(kmax:int,X):
    wcss = []
    for i in range(1,kmax+1):
        kmeans = KMeans(n_clusters=i)
        kmeans.fit(X)
        labels = kmeans.labels_
        wcss.append(kmeans.inertia_)
    plt.plot(range(1,kmax+1),wcss)




