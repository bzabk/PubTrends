import pytest
import pandas as pd
import numpy as np
from src.Preprocessing.text_preprocessing import (
    TextProcessor,
    ProcessorFactory,
    TSNEProcessor,
    KMeansProcessor,
    TFIDFProcessor,
)


class TestTextProcessor:
    @pytest.fixture
    def processor(self):
        return TextProcessor()

    @pytest.fixture
    def sample_data(self):
        data = {
            "Title": ["Test Title 1", "Test Title 2"],
            "Summary": ["Summary 1", "Summary 2"],
            "Organism": ["Human", "Mouse"],
            "Experiment_type": ["Expression profiling", "ChIP-seq"],
            "Overall_design": ["Design 1", "Design 2"],
        }
        return pd.DataFrame(data)

    def test_process_returns_dataframe(self, processor, sample_data):
        result = processor.process(sample_data.copy())
        assert isinstance(result, pd.DataFrame)

    def test_remove_punctuation(self, processor):
        text = "Hello, World! This is a test."
        result = processor._remove_punctuation(text)
        assert "," not in result
        assert "!" not in result
        assert result == "Hello World This is a test"

    def test_standardize_experiment_type_sorting(self, processor):
        text1 = "Expression profiling; ChIP-seq"
        text2 = "ChIP-seq; Expression profiling"
        assert processor._standardize_experiment_type(text1) == processor._standardize_experiment_type(text2)

    def test_standardize_experiment_type_removes_other(self, processor):
        text = "Expression profiling; Other"
        result = processor._standardize_experiment_type(text)
        assert "Other" not in result
        text = "Expression profiling; Other"
        result = processor._standardize_experiment_type(text)
        assert "Other" not in result


class TestProcessorFactory:
    def test_get_text_processor(self):
        processor = ProcessorFactory.get_processor("remove_punctuation")
        assert isinstance(processor, TextProcessor)

    def test_get_tsne_processor(self):
        processor = ProcessorFactory.get_processor("tsne", perplexity=30)
        assert isinstance(processor, TSNEProcessor)

    def test_get_unknown_processor_returns_none(self):
        processor = ProcessorFactory.get_processor("unknown")
        assert processor is None


class TestTSNEProcessor:
    def test_tsne_initialization_default(self):
        processor = TSNEProcessor()
        assert processor.tsne_reduction.perplexity == 30
        assert processor.tsne_reduction.n_components == 3


class TestKMeansProcessor:
    def test_kmeans_initialization_default(self):
        processor = KMeansProcessor()
        assert processor.cluster.n_clusters == 8


class TestTFIDFProcessor:
    def test_tfidf_initialization_default(self):
        processor = TFIDFProcessor()
        assert processor.vectorizer.max_features == 100

    def test_tfidf_process_returns_array(self):
        processor = TFIDFProcessor()
        texts = ["hello world", "hello python"]
        result = processor.process(texts)
        assert isinstance(result, np.ndarray)
