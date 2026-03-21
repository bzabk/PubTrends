class MessageService:
    def __init__(self, error_placeholder, progress_bar_placeholder):
        self.error_placeholder = error_placeholder
        self.progress_bar_placeholder = progress_bar_placeholder

    def error(self, message):
        self.error_placeholder.error(message)

    def success(self, message):
        self.error_placeholder.empty()
        self.error_placeholder.success(message)

