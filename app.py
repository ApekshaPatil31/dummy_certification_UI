
import streamlit as st



# ------------------- Page Configuration -------------------
st.set_page_config(
    page_title="Data Certification Review", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# from pages.Dashboard_Overview import show_dashboard_overview
# from pages.Case_Level_View import show_case_level_view
# from pages.Validation_Agent_View import show_validation_agent_view
# from pages.Follow_Up_Agent_View import show_follow_up_agent_view
# from pages.HITL_Review import show_hitl_review

# ------------------- Hide Default Streamlit Pages -------------------
st.markdown("""
    <style>
        /* Hide the default page list from Streamlit */
        [data-testid="stSidebarNav"] {
            display: none;
        }
        
        /* Remove default padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 0rem;
            max-width: 100%;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #f0f2f6;
        }

        /* Radio button styling */
        div[data-testid="stRadio"] > label {
            font-weight: 600;
            color: #1f1f1f;
            font-size: 14px;
        }
        
        /* Remove anchor links from headings */
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
            display: none !important;
        }
        
        /* Ensure full width layout */
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
    
    page = st.sidebar.radio(
        "Go to:",
        [
            "Page 1", 
            "Page 2", 
            
        ],
        label_visibility="visible"
    )
    
    # # Route to the selected page
    # if page == "Dashboard Overview":
    #     show_dashboard_overview()
    # elif page == "Case Level View":
    #     show_case_level_view()
    # elif page == "Validation Agent View":
    #     show_validation_agent_view()
    # elif page == "Follow Up Agent View":
    #     show_follow_up_agent_view()
    # elif page == "HITL Review":
    #     show_hitl_review()

if __name__ == "__main__":
    main()
