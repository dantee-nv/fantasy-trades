import streamlit as st
import tradebot

st.title("Fantasy Football Trade Bot")

username = st.text_input("Enter your Sleeper Username")
league_id = st.text_input("Enter your League ID")
min_net_gain = st.number_input("Minimum Net ADP Gain")

if st.button("Get Trade Suggestions"):
    if not username or not league_id:
        st.error("Please enter both Sleeper Username and League ID.")
    else:
        with st.spinner("Fetching data and calculating trades..."):
            rosters_text, trades_text = tradebot.run_trade_suggestions(username, league_id, min_net_gain)

        cols = st.columns(2)
        cols[0].header("Team Rosters with ADP")
        cols[0].text_area("", value=rosters_text, height=400)

        cols[1].header("Trade Suggestions")
        cols[1].text_area("", value=trades_text, height=400)
