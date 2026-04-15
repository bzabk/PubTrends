from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SessionDefaults:
    pmid_df: Any = None
    success_flag: bool = False
    uploaded_file: Any = None
    current_labels: Any = None
    current_X: Any = None
    kmeans_processor: Any = None
    tfidf_processor: Any = None
    tsne_processor: Any = None
    api_key: str | None = None
    max_features: int = 10
    num_clusters: int = 8
    current_num_clusters: int | None = None
    remove_punctuation: Any = None


class SessionStateManager:
    def __init__(self, session):
        self._streamlit_state = session
        self._default_values = asdict(SessionDefaults())
        self._initialize()

    def _initialize(self):
        for key, value in self._default_values.items():
            if key not in self._streamlit_state:
                self._streamlit_state[key] = value

    def get(self, key):
        return self._streamlit_state[key]

    def set(self, key, value):
        self._streamlit_state[key] = value
