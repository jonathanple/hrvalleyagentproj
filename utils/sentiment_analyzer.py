import os
from openai import OpenAI
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
import streamlit as st
import json

class SentimentAnalyzer:
    """Class for analyzing sentiment and extracting insights from HR conversations"""

    def __init__(self, openai_api_key=None):
        """Initialize with OpenAI API key"""
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    def analyze_conversation(self, question, answer):
        """Analyze a single conversation for sentiment and key topics"""

        analysis_prompt = f"""
        Please analyze this HR conversation between an employee and HR assistant:

        Employee: {question}

        HR Assistant: {answer}

        Provide a JSON response with the following fields:
        1. sentiment: The sentiment of the employee (positive, neutral, negative)
        2. sentiment_score: A score from -1.0 (very negative) to 1.0 (very positive)
        3. emotional_tone: The primary emotion detected (e.g., satisfied, confused, frustrated, grateful)
        4. main_concern: The primary concern or need expressed by the employee
        5. urgency: Rate how urgent the employee's request is (low, medium, high)
        6. key_phrases: List of up to 3 key phrases that best capture the employee's concerns or needs
        7. follow_up_needed: Boolean indicating if HR should follow up personally
        8. satisfaction_likely: Score from 0-10 indicating how likely the employee will be satisfied with the response

        Return ONLY valid JSON that can be parsed with Python's json.loads().
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an HR analytics assistant that analyzes conversations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content
            analysis = json.loads(content)
            return analysis
        except Exception as e:
            print(f"Error analyzing conversation: {e}")
            return {
                "sentiment": "neutral",
                "sentiment_score": 0,
                "emotional_tone": "unknown",
                "main_concern": "unknown",
                "urgency": "low",
                "key_phrases": [],
                "follow_up_needed": False,
                "satisfaction_likely": 5
            }

    def batch_analyze_conversations(self, conversations):
        """Analyze a batch of conversations and add sentiment data"""
        analyzed_conversations = []

        for convo in conversations:
            sentiment_data = self.analyze_conversation(convo['question'], convo['answer'])
            convo_with_sentiment = convo.copy()
            convo_with_sentiment.update(sentiment_data)
            analyzed_conversations.append(convo_with_sentiment)

        return analyzed_conversations

    def generate_sentiment_report(self, conversations, timeframe="last_30_days"):
        """Generate a comprehensive sentiment analysis report"""
        if timeframe == "last_30_days":
            cutoff_date = datetime.now() - timedelta(days=30)
        elif timeframe == "last_7_days":
            cutoff_date = datetime.now() - timedelta(days=7)
        else:
            cutoff_date = datetime.min

        filtered_convos = [
            c for c in conversations 
            if datetime.strptime(c['date_time'].split()[0], "%Y-%m-%d") >= cutoff_date
        ]

        sentiment_counts = Counter([c.get('sentiment', 'neutral') for c in filtered_convos])
        avg_sentiment_score = (
            sum([c.get('sentiment_score', 0) for c in filtered_convos]) / len(filtered_convos)
            if filtered_convos else 0
        )

        all_concerns = [c.get('main_concern', '') for c in filtered_convos]
        concern_counter = Counter([c for c in all_concerns if c != 'unknown'])
        top_concerns = concern_counter.most_common(5)

        tone_counter = Counter([c.get('emotional_tone', 'neutral') for c in filtered_convos])

        urgent_issues = [c for c in filtered_convos if c.get('urgency', 'low') == 'high']
        follow_up_needed = [c for c in filtered_convos if c.get('follow_up_needed', False)]

        return {
            "timeframe": timeframe,
            "conversations_analyzed": len(filtered_convos),
            "sentiment_distribution": dict(sentiment_counts),
            "average_sentiment_score": avg_sentiment_score,
            "top_concerns": top_concerns,
            "emotional_tones": dict(tone_counter),
            "urgent_issues_count": len(urgent_issues),
            "follow_up_needed_count": len(follow_up_needed),
            "urgent_issues": urgent_issues,
            "follow_up_needed": follow_up_needed,
            "raw_conversations": filtered_convos
        }

    def generate_recommendations(self, report):
        """Generate HR recommendations based on sentiment analysis"""

        recommendation_prompt = f"""
        Based on the following sentiment analysis report of HR conversations, provide strategic recommendations:

        Timeframe: {report['timeframe']}
        Conversations analyzed: {report['conversations_analyzed']}
        Sentiment distribution: {report['sentiment_distribution']}
        Average sentiment score: {report['average_sentiment_score']}
        Top concerns: {report['top_concerns']}
        Emotional tones: {report['emotional_tones']}
        Urgent issues count: {report['urgent_issues_count']}
        Follow-up needed count: {report['follow_up_needed_count']}

        Provide a JSON response with the following fields:
        1. key_insights: List of 3-5 most important insights from the data
        2. immediate_actions: List of 2-3 immediate actions HR should take
        3. policy_suggestions: List of 2-3 potential policy improvements
        4. communication_tips: List of 2-3 ways to improve HR communications
        5. training_needs: List of 1-2 training opportunities for HR staff
        6. employee_satisfaction_factors: The top issues affecting employee satisfaction
        7. success_metrics: How HR should measure improvement

        Return ONLY valid JSON that can be parsed with Python's json.loads().
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an HR analytics expert that provides strategic recommendations."},
                    {"role": "user", "content": recommendation_prompt}
                ],
                temperature=0.5
            )

            content = response.choices[0].message.content
            recommendations = json.loads(content)
            return recommendations
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return {
                "key_insights": ["Unable to generate insights due to an error"],
                "immediate_actions": ["Review the data manually"],
                "policy_suggestions": ["N/A"],
                "communication_tips": ["N/A"],
                "training_needs": ["N/A"],
                "employee_satisfaction_factors": ["Unknown"],
                "success_metrics": ["N/A"]
            }

    def plot_sentiment_distribution(self, report):
        """Generate a plot for sentiment distribution"""
        sentiment_data = report['sentiment_distribution']
        df = pd.DataFrame({'Sentiment': list(sentiment_data.keys()), 'Count': list(sentiment_data.values())})

        fig = px.pie(
            df,
            values='Count',
            names='Sentiment',
            title='Employee Sentiment Distribution',
            color='Sentiment',
            color_discrete_map={
                'positive': '#4CAF50',
                'neutral': '#2196F3',
                'negative': '#F44336'
            },
            hole=0.4
        )
        fig.update_traces(textinfo='percent+label')
        return fig

    def plot_top_concerns(self, report):
        """Generate a plot for top concerns"""
        concerns = report['top_concerns']
        if not concerns:
            fig = go.Figure()
            fig.update_layout(title="No Top Concerns Data Available", xaxis={"visible": False}, yaxis={"visible": False})
            return fig

        df = pd.DataFrame(concerns, columns=['Concern', 'Count'])
        fig = px.bar(
            df,
            y='Concern',
            x='Count',
            title='Top Employee Concerns',
            orientation='h',
            color='Count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        return fig

    def plot_sentiment_trend(self, conversations, days=30):
        """Plot sentiment trend over time"""
        df = pd.DataFrame(conversations)
        df['date'] = pd.to_datetime(df['date_time']).dt.date
        cutoff_date = datetime.now().date() - timedelta(days=days)
        df = df[df['date'] >= cutoff_date]
        daily_sentiment = df.groupby('date')['sentiment_score'].mean().reset_index()

        fig = px.line(
            daily_sentiment,
            x='date',
            y='sentiment_score',
            title=f'Employee Sentiment Trend (Last {days} Days)',
            labels={'sentiment_score': 'Average Sentiment Score', 'date': 'Date'}
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral", annotation_position="bottom right")
        fig.update_layout(xaxis_title="Date", yaxis_title="Sentiment Score (-1 to +1)", yaxis=dict(range=[-1, 1]))
        return fig

    def render_streamlit_report(self, report, recommendations):
        """Render the sentiment analysis report in Streamlit"""
        st.header("HR Conversation Sentiment Analysis")

        st.subheader("Overview")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Conversations", report['conversations_analyzed'])
        with col2:
            score = report['average_sentiment_score']
            st.metric("Avg. Sentiment", f"{score:.2f}", delta=None if abs(score) < 0.1 else f"{score:.2f}")
        with col3:
            urgent_pct = (report['urgent_issues_count'] / report['conversations_analyzed']) * 100 if report['conversations_analyzed'] > 0 else 0
            st.metric("Urgent Issues", f"{report['urgent_issues_count']} ({urgent_pct:.1f}%)")
        with col4:
            follow_up_pct = (report['follow_up_needed_count'] / report['conversations_analyzed']) * 100 if report['conversations_analyzed'] > 0 else 0
            st.metric("Need Follow-up", f"{report['follow_up_needed_count']} ({follow_up_pct:.1f}%)")

        st.subheader("Sentiment Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(self.plot_sentiment_distribution(report), use_container_width=True)
        with col2:
            st.plotly_chart(self.plot_top_concerns(report), use_container_width=True)

        st.subheader("Sentiment Trend")
        st.plotly_chart(self.plot_sentiment_trend(report['raw_conversations']), use_container_width=True)

        st.subheader("AI-Generated Recommendations")
        st.markdown("### Key Insights")
        for i, insight in enumerate(recommendations['key_insights']):
            st.markdown(f"**{i+1}.** {insight}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Immediate Actions")
            for i, action in enumerate(recommendations['immediate_actions']):
                st.markdown(f"**{i+1}.** {action}")
            st.markdown("### Communication Tips")
            for i, tip in enumerate(recommendations['communication_tips']):
                st.markdown(f"**{i+1}.** {tip}")
        with col2:
            st.markdown("### Policy Suggestions")
            for i, policy in enumerate(recommendations['policy_suggestions']):
                st.markdown(f"**{i+1}.** {policy}")
            st.markdown("### Training Needs")
            for i, training in enumerate(recommendations['training_needs']):
                st.markdown(f"**{i+1}.** {training}")

        st.markdown("### Employee Satisfaction Factors")
        st.write(recommendations['employee_satisfaction_factors'])

        st.markdown("### Recommended Success Metrics")
        for i, metric in enumerate(recommendations['success_metrics']):
            st.markdown(f"**{i+1}.** {metric}")

        if report['urgent_issues']:
            st.subheader("Urgent Issues Requiring Attention")
            urgent_df = pd.DataFrame([
                {
                    "Date": c['date_time'],
                    "Employee": c['employee_name'],
                    "Department": c.get('department', 'Unknown'),
                    "Concern": c['main_concern'],
                    "Question": c['question'][:100] + "..." if len(c['question']) > 100 else c['question']
                }
                for c in report['urgent_issues']
            ])
            st.dataframe(urgent_df, use_container_width=True)
