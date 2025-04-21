import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
from utils.sentiment_analyzer import SentimentAnalyzer
from utils.db_manager import DBManager

def render_sentiment_analysis_tab():
    """Render the sentiment analysis tab in the admin portal"""
    st.subheader("Sentiment Analysis & Recommendations")
    
    # Initialize components
    db_manager = DBManager()
    
    # Initialize sentiment analyzer
    sentiment_analyzer = SentimentAnalyzer()
    
    # Add timeframe selector
    timeframe = st.radio(
        "Analysis Timeframe",
        ["Last 7 Days", "Last 30 Days", "All Time"],
        horizontal=True
    )
    
    # Add department filter
    departments = ["All Departments"] + list(set([
        conv.get("department", "Unknown") 
        for conv in db_manager.get_all_conversations(limit=1)
    ]))
    
    department = st.selectbox("Department Filter", departments)
    
    # Add run analysis button
    if st.button("Run Sentiment Analysis", type="primary"):
        with st.spinner("Analyzing conversations..."):
            # Get conversations based on timeframe
            if timeframe == "Last 7 Days":
                days = 7
                tf_param = "last_7_days"
            elif timeframe == "Last 30 Days":
                days = 30
                tf_param = "last_30_days"
            else:
                days = 1000
                tf_param = "all_time"
            
            # Get conversations
            conversations = db_manager.get_all_conversations(limit=5000)
            
            # Filter by timeframe
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_convos = [
                c for c in conversations 
                if datetime.strptime(c['date_time'].split()[0], "%Y-%m-%d") >= cutoff_date
            ]
            
            # Filter by department if needed
            if department != "All Departments":
                filtered_convos = [
                    c for c in filtered_convos
                    if c.get("department", "Unknown") == department
                ]
            
            # Check if we have conversations to analyze
            if not filtered_convos:
                st.warning(f"No conversations found for the selected timeframe and filters.")
                return
            
            # Show progress during analysis
            total_convos = len(filtered_convos)
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            # For performance reasons, limit analysis to 100 conversations 
            # or use cached results if available
            if total_convos > 100:
                filtered_convos = filtered_convos[:100]
                st.info(f"Analyzing 100 most recent conversations out of {total_convos} total.")
            
            # Check for cached results
            cache_key = f"sentiment_analysis_{timeframe}_{department}"
            
            if cache_key in st.session_state:
                # Use cached results
                st.success("Using cached analysis results.")
                analyzed_conversations = st.session_state[cache_key]["conversations"]
                report = st.session_state[cache_key]["report"]
                recommendations = st.session_state[cache_key]["recommendations"]
            else:
                # Perform sentiment analysis
                analyzed_conversations = []
                
                for i, convo in enumerate(filtered_convos):
                    # Update progress
                    progress = (i + 1) / len(filtered_convos)
                    progress_bar.progress(progress)
                    progress_text.text(f"Analyzing conversation {i+1} of {len(filtered_convos)}")
                    
                    # Skip if already analyzed
                    if "sentiment" in convo:
                        analyzed_conversations.append(convo)
                        continue
                    
                    # Analyze one conversation at a time
                    analysis = sentiment_analyzer.analyze_conversation(
                        convo["question"], 
                        convo["answer"]
                    )
                    
                    # Add analysis to conversation
                    convo_with_sentiment = convo.copy()
                    convo_with_sentiment.update(analysis)
                    analyzed_conversations.append(convo_with_sentiment)
                    
                    # Sleep briefly to avoid rate limiting
                    time.sleep(0.1)
                
                # Generate report
                report = sentiment_analyzer.generate_sentiment_report(
                    analyzed_conversations, 
                    timeframe=tf_param
                )
                
                # Generate recommendations
                recommendations = sentiment_analyzer.generate_recommendations(report)
                
                # Cache the results
                st.session_state[cache_key] = {
                    "conversations": analyzed_conversations,
                    "report": report,
                    "recommendations": recommendations
                }
            
            # Clear progress indicators
            progress_bar.empty()
            progress_text.empty()
            
            # Display the report
            sentiment_analyzer.render_streamlit_report(report, recommendations)
            
            # Add option to export the report
            st.subheader("Export Report")
            if st.button("Export to JSON"):
                # Create a timestamped filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sentiment_report_{timeframe.lower().replace(' ', '_')}_{timestamp}.json"
                filepath = os.path.join("data", "reports", filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Save report
                with open(filepath, "w") as f:
                    # Combine report and recommendations
                    export_data = {
                        "report": report,
                        "recommendations": recommendations,
                        "metadata": {
                            "generated_at": datetime.now().isoformat(),
                            "timeframe": timeframe,
                            "department": department,
                            "conversations_analyzed": len(analyzed_conversations)
                        }
                    }
                    json.dump(export_data, f, indent=2, default=str)
                
                # Provide download button
                with open(filepath, "rb") as f:
                    st.download_button(
                        label="Download Report",
                        data=f,
                        file_name=filename,
                        mime="application/json"
                    )
    else:
        # If not running analysis, show instructions
        st.info("""
        This analysis uses AI to evaluate employee conversations and generates insights for HR improvement.
        
        The analysis includes:
        - Overall sentiment metrics
        - Common employee concerns
        - Emotional tones detected
        - Urgent issues requiring attention
        - AI-generated recommendations for HR
        
        Click "Run Sentiment Analysis" to begin.
        """)
        
        # Show example visualization
        with st.expander("Preview Example Report"):
            st.image("https://via.placeholder.com/800x400?text=Sentiment+Analysis+Preview")
            st.caption("Example visualization - the actual report will be generated from your conversation data")