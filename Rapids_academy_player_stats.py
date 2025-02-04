import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
import plotly.express as px
import plotly.graph_objects as go

# Add after imports
COACH_PASSWORD = "rapids2024"  # In production, use proper security measures

def authenticate_coach():
    """Authenticate coach with password"""
    password = st.sidebar.text_input("Coach Password", type="password", key="coach_password_input")
    return password == COACH_PASSWORD

def get_all_players():
    """Get list of all players from player_data directory"""
    if not os.path.exists('player_data'):
        return []
    return [f.replace('.csv', '').replace('_', ' ').title() 
            for f in os.listdir('player_data') 
            if f.endswith('.csv')]

# Cache the position stats configuration
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

@st.cache_data
def load_data(player_name):
    if not player_name:
        return None
    filename = f"player_data/{player_name.lower().replace(' ', '_')}.csv"
    if os.path.exists(filename):
        # Ensure all required columns exist
        data = pd.read_csv(filename)
        default_columns = ['date', 'opponent', 'minutes_played']
        for position, stats in get_position_config().items():
            default_columns.extend(stats)
        # Add missing columns with default value 0
        for col in default_columns:
            if col not in data.columns:
                data[col] = 0
        return data
    return None

def save_data(data, player_name):
    if not os.path.exists('player_data'):
        os.makedirs('player_data')
    filename = f"player_data/{player_name.lower().replace(' ', '_')}.csv"
    data.to_csv(filename, index=False)
    return filename

def create_stat_inputs(position):
    """Create input fields based on position"""
    stats = {}
    for stat in get_position_config()[position]:
        # Convert snake_case to Title Case for display
        display_name = stat.replace('_', ' ').title()
        stats[stat] = st.number_input(display_name, 0, 200, 0)
    return stats

def show_stats_summary(data, position):
    """Display position-specific stats summary"""
    if data is None or data.empty:
        return

    # Get the configured stats for the position
    position_stats = get_position_config()[position]
    
    # Filter to only include stats that exist in the data
    available_stats = [stat for stat in position_stats if stat in data.columns]
    missing_stats = [stat for stat in position_stats if stat not in data.columns]
    
    # Calculate sums for available stats
    if available_stats:
        stats = data[available_stats].sum()
        
        # Display in columns
        cols = st.columns(3)
        for i, (stat, value) in enumerate(stats.items()):
            display_name = stat.replace('_', ' ').title()
            cols[i % 3].metric(display_name, int(value))
    
    # Show warning about missing stats if any
    if missing_stats:
        st.warning(f"Some stats are not available in existing data: {', '.join(missing_stats)}. These will be available for new matches.")

def plot_stat_trends(data, position):
    """Create trend plots for each relevant stat"""
    if data is None or data.empty:
        return
    
    # Convert date to datetime if it's not already
    data['date'] = pd.to_datetime(data['date'])
    
    # Sort by date
    data = data.sort_values('date')
    
    # Get configured stats for the position
    position_stats = get_position_config()[position]
    
    # Filter to only include stats that exist in the data and are numeric
    numeric_cols = data.select_dtypes(include=['int64', 'float64']).columns
    available_stats = [stat for stat in position_stats if stat in numeric_cols]
    missing_stats = [stat for stat in position_stats if stat not in data.columns]
    
    # Show warning about missing stats if any
    if missing_stats:
        st.warning(f"Some stats are not available in existing data: {', '.join(missing_stats)}. These will be available for new matches.")
    
    # Create tabs for different types of visualizations
    trend_tab, comparison_tab = st.tabs(["Stat Trends", "Match Comparison"])
    
    with trend_tab:
        # Create line plots for each stat
        for stat in available_stats:
            display_name = stat.replace('_', ' ').title()
            fig = px.line(data, x='date', y=stat, 
                         title=f'{display_name} Over Time',
                         markers=True)
            fig.update_layout(xaxis_title="Date",
                            yaxis_title=display_name)
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate and display trend
            if len(data) > 1:
                trend = data[stat].diff().mean()
                trend_direction = "↑" if trend > 0 else "↓" if trend < 0 else "→"
                st.caption(f"Trend: {trend_direction} ({abs(trend):.2f} per match)")
    
    with comparison_tab:
        # Create radar chart comparing last match to average
        if len(data) > 0:
            last_match = data.iloc[-1]
            # Only calculate means for numeric columns
            numeric_data = data.select_dtypes(include=['int64', 'float64'])
            avg_stats = numeric_data.mean()
            
            stats = [stat for stat in get_position_config()[position] 
                    if stat in numeric_data.columns]
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=[last_match[stat] for stat in stats],
                theta=[stat.replace('_', ' ').title() for stat in stats],
                fill='toself',
                name='Last Match'
            ))
            
            fig.add_trace(go.Scatterpolar(
                r=[avg_stats[stat] for stat in stats],
                theta=[stat.replace('_', ' ').title() for stat in stats],
                fill='toself',
                name='Season Average'
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, data[stats].max().max()])),
                showlegend=True,
                title="Last Match vs Season Average"
            )
            
            st.plotly_chart(fig, use_container_width=True)

def delete_match(data, index, player_name):
    """Delete a match from the dataset"""
    data = data.drop(index)
    save_data(data, player_name)
    st.cache_data.clear()
    return data

def show_team_overview(selected_players):
    """Display team-wide statistics and trends"""
    st.subheader("Team Overview")
    
    # Collect all player data
    all_player_data = []
    for player in selected_players:
        data = load_data(player)
        if data is not None:
            data['player_name'] = player
            all_player_data.append(data)
    
    if all_player_data:
        combined_data = pd.concat(all_player_data, ignore_index=True)
        
        # Display team metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Matches", len(combined_data))
        with col2:
            st.metric("Total Minutes", int(combined_data['minutes_played'].sum()))
        with col3:
            st.metric("Players Tracked", len(selected_players))
        
        # Show recent matches
        st.subheader("Recent Matches")
        recent = combined_data.sort_values('date', ascending=False).head(5)
        st.dataframe(recent[['date', 'player_name', 'opponent', 'minutes_played']])

def show_individual_stats(selected_players):
    """Display individual player statistics"""
    for player in selected_players:
        st.subheader(player)
        data = load_data(player)
        if data is not None:
            # Basic stats
            matches = len(data)
            total_minutes = data['minutes_played'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Matches Played", matches)
            with col2:
                st.metric("Total Minutes", int(total_minutes))
            
            # Show recent form
            st.write("Recent Matches")
            recent = data.sort_values('date', ascending=False).head(3)
            st.dataframe(recent[['date', 'opponent', 'minutes_played']])

def coach_view():
    """Dedicated coach view function"""
    st.header("Coach View")
    all_players = get_all_players()
    selected_players = st.multiselect("Select Players to View", all_players, key="coach_player_select")
    position_filter = st.multiselect("Filter by Position", 
                                   list(get_position_config().keys()), 
                                   key="coach_position_filter")
    
    if not selected_players:
        st.info("Please select players to view their statistics")
        return

    # Create tabs for different views
    overview_tab, individual_tab = st.tabs(["Team Overview", "Individual Stats"])
    
    with overview_tab:
        show_team_overview(selected_players)
    
    with individual_tab:
        show_individual_stats(selected_players)

def player_view(player_name, position):
    """Dedicated player view function"""
    data = load_data(player_name)
    if data is None:
        data = pd.DataFrame(columns=['date', 'opponent', 'minutes_played'] + 
                          get_position_config()[position])
    
    tab1, tab2, tab3 = st.tabs(["Add Match", "View Stats", "Manage Matches"])
    
    with tab1:
        add_match_view(data, player_name, position)
    
    with tab2:
        view_stats(data, position)
    
    with tab3:
        manage_matches(data, player_name, position)

def add_match_view(data, player_name, position):
    """Add new match data for a player"""
    st.subheader("Add New Match")
    
    # Create form for match data
    with st.form("new_match_form"):
        # Basic match info
        col1, col2 = st.columns(2)
        
        with col1:
            match_date = st.date_input(
                "Match Date",
                datetime.today(),
                key="match_date_input"
            )
            opponent = st.text_input(
                "Opponent Team",
                key="opponent_input"
            )
            minutes = st.number_input(
                "Minutes Played",
                0, 120, 0,
                key="minutes_input"
            )
        
        with col2:
            # Position-specific stats
            stats = create_stat_inputs(position)
        
        # Submit button
        submitted = st.form_submit_button("Save Match")
        
        if submitted:
            if not opponent:
                st.error("Please enter opponent team name")
                return
            
            if minutes == 0:
                st.error("Please enter minutes played")
                return
            
            # Create new match row
            new_match = {
                'date': match_date.strftime('%Y-%m-%d'),
                'opponent': opponent,
                'minutes_played': minutes
            }
            
            # Add stats to new match
            new_match.update(stats)
            
            # Append to existing data
            data = pd.concat([data, pd.DataFrame([new_match])], ignore_index=True)
            
            # Save updated data
            save_data(data, player_name)
            
            st.success("Match added successfully!")
            st.cache_data.clear()
            st.rerun()

def view_stats(data, position):
    """Display player stats and trends"""
    if data is None or data.empty:
        st.info("No match data available yet. Add your first match in the 'Add Match' tab!")
        return
        
    # Show overall stats summary
    st.subheader("Statistics Summary")
    show_stats_summary(data, position)
    
    # Show trend plots
    st.subheader("Performance Trends")
    plot_stat_trends(data, position)
    
    # Recent form
    st.subheader("Recent Matches")
    recent = data.sort_values('date', ascending=False).head(5)
    st.dataframe(recent[['date', 'opponent', 'minutes_played']])

def manage_matches(data, player_name, position):
    """Manage existing matches for a player"""
    st.subheader("Match History")
    
    if data is None or data.empty:
        st.info("No matches recorded yet.")
        return
    
    # Get position-specific stats
    position_stats = get_position_config()[position]
    
    # Sort matches by date (most recent first)
    sorted_data = data.sort_values('date', ascending=False)
    
    # Display each match with edit/delete options
    for idx, row in sorted_data.iterrows():
        with st.expander(f"**{row['date']}** vs {row['opponent']} ({row['minutes_played']} minutes)"):
            edit_col1, edit_col2 = st.columns(2)
            
            # Basic match info
            with edit_col1:
                edited_date = st.date_input(
                    "Match Date", 
                    pd.to_datetime(row['date']).date(), 
                    key=f"edit_date_{idx}"
                )
                edited_opponent = st.text_input(
                    "Opponent", 
                    row['opponent'], 
                    key=f"edit_opponent_{idx}"
                )
                edited_minutes = st.number_input(
                    "Minutes Played", 
                    0, 120, 
                    int(row['minutes_played']), 
                    key=f"edit_minutes_{idx}"
                )
            
            # Position-specific stats only
            with edit_col2:
                edited_stats = {}
                for stat in position_stats:
                    display_name = stat.replace('_', ' ').title()
                    edited_stats[stat] = st.number_input(
                        display_name,
                        0, 200,
                        int(row[stat]) if stat in row and pd.notnull(row[stat]) else 0,
                        key=f"{stat}_{idx}"
                    )
            
            # Actions
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🗑️ Delete", key=f"delete_{idx}", type="secondary"):
                    data = delete_match(data, idx, player_name)
                    st.success("Match deleted successfully!")
                    st.rerun()

def main():
    st.set_page_config(page_title="Rapids Academy Player Stats", layout="wide")
    
    # Sidebar - Authentication and Navigation only
    with st.sidebar:
        st.header("User Type")
        user_type = st.radio("Select User Type", ["Player", "Coach"], key="user_type_select")
        
        if user_type == "Coach":
            is_authenticated = authenticate_coach()
        else:
            st.header("Player Information")
            player_name = st.text_input("Player Name", key="player_name_input")
            position = st.selectbox("Position", 
                                  list(get_position_config().keys()), 
                                  key="player_position_select")
    
    # Main content area
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://upload.wikimedia.org/wikipedia/en/thumb/2/2b/Colorado_Rapids_logo.svg/800px-Colorado_Rapids_logo.svg.png", 
                width=100)
    with col2:
        st.title("Rapids Academy Player Stats")
    
    # Content based on user type
    if user_type == "Coach":
        if is_authenticated:
            coach_view()
        else:
            st.error("Please enter valid coach password")
    else:
        if player_name:
            player_view(player_name, position)
        else:
            st.info("👈 Please enter player name in the sidebar to get started!")

if __name__ == "__main__":
    main()