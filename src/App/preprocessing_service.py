from src.App.front_model_utils import (
    reset_select_boxes,
    validate_user_preprocessing_parameters,
    preprocess_raw_text,
)


class PreprocessingService:
    PERPLEXITY_MIN = 30

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def process_loaded_toy_dataset(self) -> None:
        validate_user_preprocessing_parameters(PreprocessingService.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        self.session_manager.set("success_flag", True)

    def process_loaded_user_dataset(self) -> None:
        self.session_manager.set("current_num_clusters", self.session_manager.get("num_clusters"))
        validate_user_preprocessing_parameters(PreprocessingService.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        self.session_manager.set("success_flag", True)
