import streamlit as st
from datetime import datetime


def init_theme():
    """Initialize theme settings in session state."""
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"


def get_theme_mode():
    """Get current theme mode."""
    return st.session_state.get("theme_mode", "light")


def toggle_theme():
    """Toggle between light and dark mode."""
    st.session_state.theme_mode = "dark" if get_theme_mode() == "light" else "light"


def get_color_palette():
    """Return color palette based on current theme."""
    if get_theme_mode() == "dark":
        return {
            "primary": "#C9A84C",
            "background": "#0F1117",
            "secondary_bg": "#161B22",
            "text": "#F0F2F8",
            "text_secondary": "#8B949E",
            "border": "#30363D",
            "sidebar_bg": "#0D1117",
            "sidebar_text": "#F0F2F8",
            # Accent colors
            "blue": "#64B5F6",
            "red": "#FF6B6B",
            "amber": "#FFD54F",
            "teal": "#4DD0E1",
            "green": "#81C784",
            "orange": "#FFB74D",
            "purple": "#BA68C8",
            "navy": "#5C7CFA",
            "pink": "#FF6B9D",
        }
    else:
        return {
            "primary": "#C9A84C",
            "background": "#F8F9FA",
            "secondary_bg": "#EEF0F4",
            "text": "#1A1F36",
            "text_secondary": "#6B7280",
            "border": "#E0E4EE",
            "sidebar_bg": "#1A1F36",
            "sidebar_text": "#F0F2F8",
            # Accent colors
            "blue": "#2E5BBA",
            "red": "#E84040",
            "amber": "#C9A84C",
            "teal": "#2DBECD",
            "green": "#2DBE6C",
            "orange": "#E8873A",
            "purple": "#7B61FF",
            "navy": "#1A1F36",
            "pink": "#E84080",
        }


def inject_global_css():
    """Inject global CSS styling for the app."""
    colors = get_color_palette()
    
    css = f"""
    <style>
    /* Root styling */
    html, body {{
        background-color: {colors['background']};
        color: {colors['text']};
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {colors['sidebar_bg']} 0%, #2E3A5C 100%);
    }}
    [data-testid="stSidebar"] * {{
        color: {colors['sidebar_text']} !important;
    }}
    
    /* Main content background */
    [data-testid="stAppViewContainer"] {{
        background-color: {colors['background']};
    }}
    
    /* Page headers */
    h1 {{ 
        border-inline-start: 4px solid {colors['primary']};
        padding-inline-start: 12px;
        font-weight: 700;
        color: {colors['text']};
    }}
    h2 {{
        border-inline-start: 3px solid {colors['primary']};
        padding-inline-start: 10px;
        color: {colors['text']};
    }}
    h3 {{
        color: {colors['text']};
    }}
    
    /* Metric cards */
    [data-testid="stMetric"] {{
        background: {colors['secondary_bg']};
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-block-start: 3px solid {colors['primary']};
    }}
    
    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 8px 20px;
    }}
    
    /* Primary button */
    .stButton > button[kind="primary"] {{
        background-color: {colors['primary']} !important;
        color: white !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: #B39850 !important;
    }}
    
    /* Expander styling */
    [data-testid="stExpander"] {{
        border: 1px solid {colors['border']};
        border-radius: 8px;
        margin-block-end: 8px;
    }}
    
    /* Alert/message styling */
    [data-testid="stAlert"] {{
        border-radius: 8px;
        background-color: {colors['secondary_bg']};
        border: 1px solid {colors['border']};
    }}
    
    /* Input fields */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select,
    [data-testid="stTextArea"] textarea {{
        border-radius: 6px;
        border: 1px solid {colors['border']};
        background-color: {colors['background']};
        color: {colors['text']};
    }}
    
    /* Dataframe/table styling */
    [data-testid="stDataFrame"] {{
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid {colors['border']};
    }}
    
    /* Tabs */
    [role="tablist"] {{
        border-block-end: 2px solid {colors['border']};
    }}
    
    /* Text styling */
    p, span, label {{
        color: {colors['text']};
    }}
    
    /* Divider */
    hr {{
        border-color: {colors['border']};
    }}
    
    /* Links */
    a {{
        color: {colors['primary']};
    }}
    
    /* Success/info/warning/error colors */
    .stSuccess {{
        background-color: rgba(45, 190, 108, 0.1);
        border-color: {colors['green']};
    }}
    
    .stInfo {{
        background-color: rgba(77, 208, 225, 0.1);
        border-color: {colors['teal']};
    }}
    
    .stWarning {{
        background-color: rgba(232, 147, 58, 0.1);
        border-color: {colors['orange']};
    }}
    
    .stError {{
        background-color: rgba(232, 64, 64, 0.1);
        border-color: {colors['red']};
    }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def inject_page_accent(accent_color, accent_name):
    """Inject page-specific accent color styling."""
    colors = get_color_palette()
    
    css = f"""
    <style>
    /* Page accent color */
    h1 {{
        border-inline-start-color: {accent_color};
    }}
    h2 {{
        border-inline-start-color: {accent_color};
    }}
    
    [data-testid="stMetric"] {{
        border-block-start-color: {accent_color};
    }}
    
    .stButton > button[kind="primary"] {{
        background-color: {accent_color} !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        opacity: 0.85;
    }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def get_sidebar_time():
    """Get formatted current date and time."""
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    return f"{date_str} • {time_str}"


def get_greeting():
    """Get time-based greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"
