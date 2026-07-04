import logging

from src.app.main_app import MainApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    app = MainApp()
    app.run()
