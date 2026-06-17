"""
app/app.py — HITL Gold-Certification Review (POC wireframe)
-----------------------------------------------------------
Frontend-first wireframe for the data-certification HITL app (design: app.md).

This POC runs LOCALLY with no Databricks / Spark / SQL warehouse — every read and
write goes through app/mock_data.py (an in-memory stand-in for the eventual
queries.py + connection.py). To run:

    pip install streamlit
    streamlit run app.py

When the backend is wired, restore the `databricks.sql` connection here and swap
mock_data.* calls for queries.* — the page code stays the same.
"""

import streamlit as st

from pages.certification_review import show_certification_review
from pages.asset_detail import show_asset_detail

# ------------------- Page Configuration -------------------
st.set_page_config(
    page_title="Data Certification Review",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded",
)

# Mock signed-in user. In production this comes from the Databricks Apps
# identity header (auth.current_user()); hardcoded here for the wireframe.
CURRENT_USER = "apeksha.patil@alamar.io"

# ------------------- Hide Default Streamlit Pages -------------------
st.markdown("""
    <style>
        /* Hide the default page list from Streamlit (we route via the radio) */
        [data-testid="stSidebarNav"] { display: none; }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 0rem;
            max-width: 100%;
        }
        [data-testid="stSidebar"] { background-color: #f0f2f6; }

        div[data-testid="stRadio"] > label {
            font-weight: 600;
            color: #1f1f1f;
            font-size: 14px;
        }
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }

        .main .block-container {
            max-width: 100%;
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>
""", unsafe_allow_html=True)


# ------------------- Main Function -------------------
def main():
    st.sidebar.title("📂 Navigation")
    st.sidebar.caption(f"Signed in as **{CURRENT_USER}**")

    page = st.sidebar.radio(
        "Go to:",
        [
            "Certification Review",
            "Asset Detail",
        ],
        label_visibility="visible",
    )

    st.sidebar.divider()
    st.sidebar.caption(
        "⚠️ wireframe — data is mocked in-memory (`mock_data.py`). "
        "No Databricks connection."
    )

    # Route to the selected page.
    if page == "Certification Review":
        show_certification_review(current_user=CURRENT_USER)
    elif page == "Asset Detail":
        show_asset_detail()


if __name__ == "__main__":
    main()
