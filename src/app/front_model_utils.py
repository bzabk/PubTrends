import streamlit as st



def validate_chosen_file(uploaded_file, min_len_pmid_list) -> list[str] | None:
    """
    Function checks whether the uploaded file is in the correct format and extracts PMIDs from it.
    In case user uploaded less than 10 correct PMIDs, an error message is displayed.
    If txt file contains less than 10 PMIDs, the error message is displayed.

    :param uploaded_file: The file uploaded by the user.

    :return list[int]: A list of unique PMIDs extracted from the file.
    """
    if uploaded_file is None:
        raise PmidTxtFileIsNoneException
    file_content = uploaded_file.read().decode("utf-8")
    list_of_pmids = []
    pmids = file_content.split("\n")
    for line in pmids:
        line = line.replace(" ", "").strip()
        if line.isdigit():
            list_of_pmids.append(str(line))
    list_of_pmids = list(set(list_of_pmids))
    if len(list_of_pmids) < min_len_pmid_list:
        raise NotEnoughPmidsInTxtFileException
    return list_of_pmids


def reset_select_boxes() -> None:
    """
    After loading a new dataset and setting a new 3D plot,
    reset the previous selections in the select boxes.
    """
    st.session_state["Pmid"] = "<select>"
    st.session_state["Organism"] = "<select>"
    st.session_state["Experiment_type"] = "<select>"


def hex_to_rgba(hex_color, alpha) -> str:
    """
    Converting hex color format to rgb
    """
    import matplotlib.colors as mcolors

    rgba = mcolors.to_rgba(hex_color, alpha)
    return f"rgb({int(rgba[0] * 255)}, {int(rgba[1] * 255)}, {int(rgba[2] * 255)})"


def create_hover_text(is_selected: int) -> list[str]:
    hover_text_selected = [
        (
            f"<b>{row['Title']}</b><br>GSE Code: {row['GSE_code']}<br>"
            f"PMID: {row['Pmid']}<br>Organism: {row['Organism']}<br>"
            f"Experiment_type: {row['Experiment_type']}"
        )
        for _, row in st.session_state.pmid_df[st.session_state.pmid_df["is_selected"] == is_selected].iterrows()
    ]
    return hover_text_selected


def set_colors_and_opacity() -> None:
    """
    Function assigns color and opacity to each label from the KMeans algorithm.
    To easly distingush points that satisfied filter conditions, points that were not selected
    """
    import numpy as np
    import plotly.express as px

    unique_labels = np.arange(0, st.session_state.current_num_clusters, 1).astype(str)
    colors = px.colors.qualitative.Alphabet
    color_palette = colors[: len(unique_labels)]
    # mapping from unique_labels to color
    map_dict = dict(zip(unique_labels, color_palette, strict=False))
    # assigning color to each point based on its label
    list_of_colors = [map_dict[label] for label in st.session_state.current_labels]
    idx = 0
    color_palette_final = []
    # looping through all points in dataframe and
    # setting opacity based on whether they were selected by user or not
    for idx, col in enumerate(list_of_colors):
        if st.session_state.pmid_df["is_selected"].iloc[idx] == (idx + 1):
            color_palette_final.append(hex_to_rgba(col, alpha=1))
        else:
            color_palette_final.append(hex_to_rgba(col, alpha=0.2))
    st.session_state.pmid_df["colors"] = color_palette_final


def create_trace(is_selected: int, opacity: float, hover_text: list[str]):
    import plotly.graph_objects as go

    return go.Scatter3d(
        x=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 0],
        y=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 1],
        z=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 2],
        mode="markers",
        marker={
            "color": st.session_state.pmid_df["colors"][st.session_state.pmid_df["is_selected"] == is_selected],
            "size": 8,
            "opacity": opacity,
        },
        hovertext=hover_text,
        hoverinfo="text",
    )


def load_3d_plot(plot_width, plot_height):
    """
    Main function responsible for displaying interactive 3D plot visualizing
    layout of the data points in 3D space.

    :return go.Figure: prepared 3D plot ready to display
    """
    import plotly.graph_objects as go

    # setting list of colors for each point in the dataframe
    set_colors_and_opacity()
    # creating hover text for these points that were selected by user
    hover_text_selected = create_hover_text(is_selected=1)
    hover_text_not_selected = create_hover_text(is_selected=0)
    # set of selected points with opacity 1
    trace1 = create_trace(is_selected=1, opacity=1, hover_text=hover_text_selected)
    trace2 = create_trace(is_selected=0, opacity=0.08, hover_text=hover_text_not_selected)

    fig = go.Figure()
    fig.add_trace(trace1)
    fig.add_trace(trace2)

    fig.update_layout(
        scene={"xaxis_title": "X", "yaxis_title": "Y", "zaxis_title": "Z"},
        width=plot_width,
        height=plot_height,
        showlegend=False,
    )
    return fig


def validate_user_preprocessing_parameters(perplexity) -> None:
    """
    This method checks whether the `max_features` and `num_clusters` parameters are set in the session state.
    If not, it assigns default values.
    The `perplexity` parameter must be set manually. If its value is higher than the number of data points
    in the DataFrame, t-SNE will raise an error.
    If the user provides an incorrect value for num_features or num_clusters, the last valid parameters will be used instead.
    """
    from src.preprocessing.text_preprocessing import ProcessorFactory

    if st.session_state.max_features is None:
        st.session_state.max_features = 10
    if st.session_state.num_clusters is None:
        st.session_state.num_clusters = 8
    n_samples = len(st.session_state.pmid_df)
    perplexity = min(perplexity, n_samples - 1)

    st.session_state.current_num_clusters = st.session_state.num_clusters
    st.session_state.tsne_processor = ProcessorFactory.get_processor("tsne", perplexity=perplexity)
    st.session_state.kmeans_processor = ProcessorFactory.get_processor(
        "kmeans", n_clusters=st.session_state.num_clusters
    )
    st.session_state.tfidf_processor = ProcessorFactory.get_processor(
        "tfidf", max_features=st.session_state.max_features
    )


def preprocess_raw_text() -> None:
    """
    Main function for processing raw text from a DataFrame into 3D points.
    Steps:
    1) Handle and remove semi-duplicated 'Experiment_type' entries.
    2) Concatenate all relevant columns.
    3) Set the 'is_selected' column to 1 by default (ensuring no points have lower opacity).
    4) Apply TF-IDF to the concatenated text.
    5) Reduce dimensionality to 3D.
    6) Fit the KMeans algorithm and store the resulting labels in st.session_state.
    """
    if st.session_state.get("remove_punctuation") is None:
        from src.preprocessing.text_preprocessing import ProcessorFactory

        st.session_state.remove_punctuation = ProcessorFactory.get_processor("text_processor")

    st.session_state.pmid_df = st.session_state.remove_punctuation.process(st.session_state.pmid_df)
    st.session_state.current_X = st.session_state.tfidf_processor.process(st.session_state.pmid_df["Text"])
    st.session_state.current_X = st.session_state.tsne_processor.process(st.session_state.current_X)
    st.session_state.kmeans_processor.process(st.session_state.current_X)
    st.session_state.current_labels = st.session_state.kmeans_processor.cluster.labels_.astype(str)
