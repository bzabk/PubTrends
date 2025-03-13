import streamlit as st
from typing import Text


def main():


    with open("Static/style.css") as css:
        st.html(f"<style>{css.read()}</style>")

    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                width: 350px; 
                min-width: 350px; 
                max-width: 350px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container(key="app_title"):
        st.title("PubTrends: Data Insights for Enhanced Paper Relevance")

    with st.sidebar:
        st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
        st.file_uploader("Choose a file", type=["txt"], accept_multiple_files=False, label_visibility="collapsed")
        st.text("or choose examplary file")
        if st.button("Load examplary dataset", use_container_width=True):
            pass







if __name__ == "__main__":
    main()

