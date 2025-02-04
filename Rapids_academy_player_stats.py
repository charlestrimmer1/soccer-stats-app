import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
import json

# Page configuration
st.set_page_config(
    page_title="Rapids Academy Stats",
    page_icon="⚽",
    layout="wide"
)

# Constants
COACH_PASSWORD = "rapids2024"
TEAMS = ["U15", "U16", "U18"]

# File paths
CONFIG_DIR = "config"
POSITION_CONFIG_FILE = os.path.join(CONFIG_DIR, "position_config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

def save_position_config(config):
    with open(POSITION_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_position_config():
    if os.path.exists(POSITION_CONFIG_FILE):
        with open(POSITION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return get_default_position_config()

def get_default_position_config():
    return {
        "Goalkeeper": ["saves", "clean_sheets", "goals_conceded"],
        "Center Back": ["passes_to_fullback", "passes_into_red_zone", "tackles_won"],
        "Fullback": ["red_zone_passes", "passes_behind_line", "defensive_1v1_won"],
        "Defensive Midfielder": ["ball_recoveries", "passes_completed", "turnovers"],
        "Attacking Midfielder": ["redzone_receptions", "passes_behind_line", "shots"],
        "Wide Forward": ["receptions_behind_line", "paz_crosses", "assists"],
        "Center Forward": ["receptions_behind_line", "assists", "goals"]
    }

def manage_stats_categories():
    st.header("Manage Stats Categories")
    
    position_config = load_position_config()
    
    # Add new position
    col1, col2 = st.columns([2, 1])
    with col1:
        new_position = st.text_input("Add New Position")
    with col2:
        if st.button("Add Position") and new_position:
            if new_position not in position_config:
                position_config[new_position] = []
                save_position_config(position_config)
                st.success(f"Added position: {new_position}")
                st.rerun()
    
    # Manage existing positions
    for position in position_config:
        st.subheader(position)
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            new_stat = st.text_input(f"Add stat for {position}", key=f"stat_{position}")
        with col2:
            if st.button("Add Stat", key=f"add_{position}") and new_stat:
                if new_stat not in position_config[position]:
                    position_config[position].append(new_stat)
                    save_position_config(position_config)
                    st.success(f"Added {new_stat} to {position}")
                    st.rerun()
        with col3:
            if st.button("Remove Position", key=f"remove_{position}"):
                del position_config[position]
                save_position_config(position_config)
                st.success(f"Removed position: {position}")
                st.rerun()
        
        # Show existing stats with remove buttons
        if position_config[position]:
            stats_to_remove = st.multiselect(
                "Select stats to remove",
                position_config[position],
                key=f"remove_stats_{position}"
            )
            if st.button("Remove Selected Stats", key=f"remove_stats_btn_{position}"):
                position_config[position] = [stat for stat in position_config[position] 
                                          if stat not in stats_to_remove]
                save_position_config(position_config)
                st.success("Removed selected stats")
                st.rerun()

@st.cache_data(ttl=300)
def load_data(player_name, team):
    if not player_name or not team:
        return None
    filename = f"player_data/{team}/{player_name.lower().replace(' ', '_')}.csv"
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return None

def get_all_players(team=None):
    players = []
    if team:
        team_dir = f"player_data/{team}"
        if os.path.exists(team_dir):
            players = [f.replace('.csv', '').replace('_', ' ').title() 
                      for f in os.listdir(team_dir) 
                      if f.endswith('.csv')]
    return players

def save_data(data, player_name, team):
    team_dir = f"player_data/{team}"
    if not os.path.exists(team_dir):
        os.makedirs(team_dir)
    filename = f"{team_dir}/{player_name.lower().replace(' ', '_')}.csv"
    data.to_csv(filename, index=False)
    st.cache_data.clear()
    return filename

def coach_view():
    st.header("Coach View")
    
    # Add tab for managing stats categories
    tabs = ["View Stats", "Manage Categories"]
    selected_tab = st.radio("Select View", tabs, horizontal=True)
    
    if selected_tab == "Manage Categories":
        manage_stats_categories()
        return
    
    # Team selection
    selected_team = st.selectbox("Select Team", TEAMS)
    
    # Get players and handle selection
    all_players = get_all_players(selected_team)
    selected_players = st.multiselect("Select Players", all_players)
    
    if not selected_players:
        st.info("Please select players to view their statistics")
        return
    
    # Rest of the coach view functionality...
    # (Previous coach_view code remains the same, just update data loading to include team)

def player_view():
    # Team selection
    selected_team = st.selectbox("Select Team", TEAMS)
    
    col1, col2 = st.columns(2)
    with col1:
        player_name = st.text_input("Player Name")
    with col2:
        position = st.selectbox("Position", list(load_position_config().keys()))
    
    if player_name and position:
        player_view_content(player_name, position, selected_team)
    else:
        st.info("Please enter your name and select your position to view stats")

def main():
    # Sidebar for navigation
    with st.sidebar:
        st.header("User Type")
        user_type = st.radio("Select User Type", ["Player", "Coach"], horizontal=True)
        
        if user_type == "Coach":
            is_authenticated = authenticate_coach()
    
    # Main area header with logo
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://upload.wikimedia.org/wikipedia/en/thumb/2/2b/Colorado_Rapids_logo.svg/800px-Colorado_Rapids_logo.svg.png", 
                width=100)
    with col2:
        st.title("Rapids Academy Player Stats")
    
    # Route to appropriate view
    if user_type == "Coach":
        if is_authenticated:
            coach_view()
        else:
            st.warning("Please authenticate to access coach view")
    else:
        player_view()

if __name__ == "__main__":
    main()