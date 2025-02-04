import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

# Page configuration must be first Streamlit command
st.set_page_config(
    page_title="Rapids Academy Stats",
    page_icon="⚽",
    layout="wide"
)

# Constants
COACH_PASSWORD = "rapids2024"

# Authentication function
def authenticate_coach():
    return st.sidebar.text_input("Coach Password", type="password") == COACH_PASSWORD

@st.cache_data
def get_position_config():
    return {
        "Goalkeeper": ["saves", "clean_sheets", "goals_conceded"],
        "Center Back": ["passes_to_fullback", "passes_into_red_zone", "tackles_won", "aerial_duels_won", "turnovers", "ball_recoveries"],
        "Fullback": ["red_zone_passes", "passes_behind_line", "defensive_1v1_won", "turnovers", "crosses", "assists"],
        "Defensive Midfielder/Pivot": ["ball_recoveries", "passes_completed", "turnovers", "creating_3_backline", "forward_passes_10plus"],
        "Attacking Midfielder": ["redzone_receptions", "passes_behind_line", "shots", "shots_on_target", "assists", "goals", "ball_recoveries"],
        "Wide Forward": ["receptions_behind_line", "paz_crosses", "assists", "goals", "ball_recoveries", "passes_behind_line"],
        "Center Forward": ["receptions_behind_line", "assists", "goals", "ball_recoveries", "successful_holdup_plays", "forced_errors"]
    }

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data(player_name):
    if not player_name:
        return None
    filename = f"player_data/{player_name.lower().replace(' ', '_')}.csv"
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return None

def get_all_players():
    if not os.path.exists('player_data'):
        return []
    return [f.replace('.csv', '').replace('_', ' ').title() 
            for f in os.listdir('player_data') 
            if f.endswith('.csv')]

def save_data(data, player_name):
    if not os.path.exists('player_data'):
        os.makedirs('player_data')
    filename = f"player_data/{player_name.lower().replace(' ', '_')}.csv"
    data.to_csv(filename, index=False)
    st.cache_data.clear()
    return filename

def create_stat_inputs(position):
    stats = {}
    for stat in get_position_config()[position]:
        display_name = stat.replace('_', ' ').title()
        stats[stat] = st.number_input(display_name, 0, 200, 0)
    return stats

def show_basic_stats(data, position):
    if data is None or data.empty:
        return
    
    matches = len(data)
    total_minutes = data['minutes_played'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Matches Played", matches)
    with col2:
        st.metric("Total Minutes", int(total_minutes))
    
    position_stats = get_position_config()[position]
    available_stats = [stat for stat in position_stats if stat in data.columns]
    
    if available_stats:
        stats = data[available_stats].sum()
        cols = st.columns(3)
        for i, (stat, value) in enumerate(stats.items()):
            cols[i % 3].metric(stat.replace('_', ' ').title(), int(value))

def show_performance_trend(data, stat):
    if data is None or data.empty:
        return
    
    data['date'] = pd.to_datetime(data['date'])
    fig = px.line(
        data.sort_values('date'),
        x='date',
        y=stat,
        title=f'{stat.replace("_", " ").title()} Over Time',
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

def coach_view():
    st.header("Coach View")
    
    # Get players and handle selection
    all_players = get_all_players()
    selected_players = st.multiselect("Select Players", all_players)
    
    if not selected_players:
        st.info("Please select players to view their statistics")
        return
    
    # View selector for better performance
    view_type = st.radio(
        "Select View",
        ["Basic Stats", "Performance Trends"],
        horizontal=True
    )
    
    # Show stats based on selection
    for player in selected_players:
        st.subheader(player)
        data = load_data(player)
        
        if data is None:
            st.warning(f"No data available for {player}")
            continue
            
        try:
            positions = list(get_position_config().keys())
            position = data.get('position', positions)
            if not position or not isinstance(position, (list, str)):
                position = positions[0]  # Set default to first position
            elif isinstance(position, list):
                position = position[0]
        except Exception as e:
            st.error(f"Error loading position data. Using default position.")
            position = list(get_position_config().keys())[0]

        if view_type == "Basic Stats":
            show_basic_stats(data, position)
            
            # Recent matches
            st.subheader("Recent Matches")
            recent = data.sort_values('date', ascending=False).head(3)
            st.dataframe(recent[['date', 'opponent', 'minutes_played']])
            
        else:  # Performance Trends
            position_stats = get_position_config()[position]
            stat = st.selectbox(
                "Select stat to view",
                position_stats,
                key=f"stat_select_{player}"
            )
            show_performance_trend(data, stat)

def player_view(player_name, position):
    # Initialize tabs
    add_tab, view_tab = st.tabs(["Add Match", "View Stats"])
    
    # Load data
    data = load_data(player_name)
    if data is None:
        data = pd.DataFrame(columns=['date', 'opponent', 'minutes_played', 'position'] + 
                          get_position_config()[position])
    
    # Add Match Tab
    with add_tab:
        with st.form("new_match_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                match_date = st.date_input("Match Date", datetime.today())
                opponent = st.text_input("Opponent Team")
                minutes = st.number_input("Minutes Played", 0, 120, 0)
            
            with col2:
                stats = create_stat_inputs(position)
            
            if st.form_submit_button("Save Match"):
                if not opponent or minutes == 0:
                    st.error("Please fill in all required fields")
                else:
                    new_match = {
                        'date': match_date.strftime('%Y-%m-%d'),
                        'opponent': opponent,
                        'minutes_played': minutes,
                        'position': position,
                        **stats
                    }
                    data = pd.concat([data, pd.DataFrame([new_match])], ignore_index=True)
                    save_data(data, player_name)
                    st.success("Match added successfully!")
                    st.rerun()
    
    # View Stats Tab
    with view_tab:
        if data.empty:
            st.info("No matches recorded yet. Add your first match in the Add Match tab!")
        else:
            show_basic_stats(data, position)
            
            # Show performance trends for selected stat
            st.subheader("Performance Trends")
            selected_stat = st.selectbox(
                "Select stat to view",
                get_position_config()[position]
            )
            if selected_stat:
                show_performance_trend(data, selected_stat)

def main():
    # Sidebar for navigation
    with st.sidebar:
        st.header("User Type")
        user_type = st.radio("Select User Type", ["Player", "Coach"], horizontal=True)
        
        if user_type == "Coach":
            is_authenticated = authenticate_coach()
        else:
            st.header("Player Information")
            player_name = st.text_input("Player Name")
            position = st.selectbox("Position", list(get_position_config().keys()))
    
    # Main area header
    st.title("Rapids Academy Player Stats")
    
    # Route to appropriate view
    if user_type == "Coach":
        if is_authenticated:
            coach_view()
        else:
            st.warning("Please authenticate to access coach view")
    else:
        if player_name:
            player_view(player_name, position)
        else:
            st.info("Please enter your name to view stats")

if __name__ == "__main__":
    main()