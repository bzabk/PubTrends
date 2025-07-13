from App.front_model import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.prepare_main_window()
    app.prepare_side_bar()
    app.prepare_tabs()


