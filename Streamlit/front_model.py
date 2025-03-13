import streamlit as st

class MainApp:


    def __init__(self):
        self.load_examplary_data_set = False
        if "uploaded_file" not in st.session_state:
            st.session_state.uploaded_file = None

    def prepare_side_bar(self):
        with st.sidebar:
            st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
            st.session_state.uploaded_file = st.file_uploader("Choose a file", type=["txt"], accept_multiple_files=False, label_visibility="collapsed")
            if st.button("Analyse list of PMIDs", use_container_width=True):
                pass
            st.text("or choose prepared dataset")
            if st.button("Load examplary dataset", use_container_width=True):
                self.handle_load_examplary_data_set()

    def handle_load_examplary_data_set(self):
        self.load_examplary_data_set = True
        st.session_state.uploaded_file = None

    def prepare_main_window(self):
        with st.container(key="app_title"):
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")


    def prepare_tabs(self):
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])
        with tab_visualization:
            pass
        with tab_info:
            pass

    def load_styles(self):

        with open("Static/style.css") as css:
            st.markdown(f"<style>{css.read()}</style>",unsafe_allow_html=True)

if __name__ == "__main__":
    app = MainApp()
    app.load_styles()
    app.prepare_main_window()
    app.prepare_side_bar()
    app.prepare_tabs()

