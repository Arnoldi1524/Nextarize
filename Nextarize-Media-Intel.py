import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import json

st.set_page_config(layout="wide", page_title="Interactive Media Intelligence Dashboard")

# --- Helper Functions (Python equivalents of React JS functions) ---

def clean_data(df):
    """
    Cleans and normalizes the raw DataFrame.
    - Converts 'Date' column to datetime objects.
    - Fills missing 'Engagements' with 0.
    - Normalizes column names (lowercase, replace spaces with underscores).
    """
    cleaned_df = df.copy()

    # Normalize column names
    cleaned_df.columns = [col.strip().lower().replace(' ', '_') for col in cleaned_df.columns]

    # Convert 'date' column to datetime
    if 'date' in cleaned_df.columns:
        # Attempt to parse various date formats
        cleaned_df['date'] = pd.to_datetime(cleaned_df['date'], errors='coerce')
        cleaned_df = cleaned_df.dropna(subset=['date']) # Drop rows with invalid dates

    # Fill missing 'engagements' with 0
    if 'engagements' in cleaned_df.columns:
        cleaned_df['engagements'] = pd.to_numeric(cleaned_df['engagements'], errors='coerce').fillna(0)
    else:
        st.warning("The uploaded CSV does not contain an 'Engagements' column. Some charts and analyses may be affected.")

    # Sort data by date
    cleaned_df = cleaned_df.sort_values(by='date').reset_index(drop=True)

    return cleaned_df

def generate_insights(data, chart_type):
    """
    Generates insights for each chart type.
    """
    if data.empty:
        return ["No data available to generate insights for this chart."]

    insights = []
    # Helper function to format text with quotes and bold the content
    format_quote_and_bold = lambda text: f"“<strong>{text}</strong>”"

    if chart_type == 'sentiment':
        sentiment_counts = data['sentiment'].value_counts(normalize=True).to_dict()
        total_sentiments = data['sentiment'].count()
        sorted_sentiments = sorted(sentiment_counts.items(), key=lambda item: item[1], reverse=True)

        if sorted_sentiments:
            dominant_sentiment, dominant_percent = sorted_sentiments[0]
            insights.append(f"The dominant sentiment is {format_quote_and_bold(dominant_sentiment)}, accounting for {format_quote_and_bold(f'{dominant_percent * 100:.1f}%')} of all posts.")
        if len(sorted_sentiments) > 1:
            insights.append(f"There's a significant presence of {format_quote_and_bold(sorted_sentiments[1][0])} sentiment, indicating a diverse range of public opinion.")
        
        positive_count = data['sentiment'].value_counts().get('Positive', 0)
        negative_count = data['sentiment'].value_counts().get('Negative', 0)
        if negative_count > 0 and positive_count > 0:
            ratio = positive_count / negative_count
            insights.append(f"The ratio of Positive to Negative sentiment is approximately {format_quote_and_bold(f'{ratio:.2f}:1')}, showing the relative prevalence of positive mentions.")
        elif total_sentiments > 0:
             insights.append('Sentiment distribution is largely neutral or mixed, without clear dominance of positive or negative trends.')


    elif chart_type == 'engagement_trend':
        if 'date' not in data.columns or 'engagements' not in data.columns:
            insights.append("Date or Engagements column missing for trend analysis.")
            return insights

        engagements_by_date = data.groupby(data['date'].dt.date)['engagements'].sum().sort_index()

        if not engagements_by_date.empty:
            peak_engagement_date = engagements_by_date.idxmax().strftime('%Y-%m-%d')
            peak_engagement_value = engagements_by_date.max()
            lowest_engagement_date = engagements_by_date.idxmin().strftime('%Y-%m-%d')
            lowest_engagement_value = engagements_by_date.min()

            insights.append(f"The peak engagement occurred on {format_quote_and_bold(peak_engagement_date)} with {format_quote_and_bold(f'{peak_engagement_value:,.0f}')} engagements.")
            insights.append(f"The lowest engagement was observed on {format_quote_and_bold(lowest_engagement_date)} with {format_quote_and_bold(f'{lowest_engagement_value:,.0f}')} engagements.")

            if len(engagements_by_date) > 1:
                first_engagement = engagements_by_date.iloc[0]
                last_engagement = engagements_by_date.iloc[-1]
                if last_engagement > first_engagement * 1.1:
                    insights.append('There is an overall “<strong>increasing trend</strong>” in engagements over the period, suggesting growing audience interaction.')
                elif last_engagement < first_engagement * 0.9:
                    insights.append('There is an overall “<strong>decreasing trend</strong>” in engagements over the period, suggesting declining audience interaction.')
                else:
                    insights.append('Engagements have remained relatively “<strong>stable</strong>” over the period, with minor fluctuations.')
        else:
            insights.append('Insufficient data points to determine a clear engagement trend over time.')


    elif chart_type == 'platform_engagements':
        if 'platform' not in data.columns or 'engagements' not in data.columns:
            insights.append("Platform or Engagements column missing for platform analysis.")
            return insights

        platform_engagements = data.groupby('platform')['engagements'].sum().sort_values(ascending=False)

        if not platform_engagements.empty:
            insights.append(f"{format_quote_and_bold(platform_engagements.index[0])} is the leading platform, generating {format_quote_and_bold(f'{platform_engagements.iloc[0]:,.0f}')} engagements, highlighting its effectiveness.")
            if len(platform_engagements) > 1:
                diff = platform_engagements.iloc[0] - platform_engagements.iloc[1]
                insights.append(f"There is a significant gap of {format_quote_and_bold(f'{diff:,.0f}')} engagements between the top two platforms, indicating a dominant player.")
            if len(platform_engagements) > 2:
                insights.append(f"Platforms like {format_quote_and_bold(platform_engagements.index[-1])} show lower engagement, suggesting areas for strategic re-evaluation.")
        else:
            insights.append('Data suggests limited platform diversity, with engagement concentrated on a few platforms.')


    elif chart_type == 'media_type':
        if 'media_type' not in data.columns:
            insights.append("Media Type column missing for media type analysis.")
            return insights

        media_type_counts = data['media_type'].value_counts(normalize=True)
        total_media = data['media_type'].count()
        sorted_media_types = sorted(media_type_counts.items(), key=lambda item: item[1], reverse=True)

        if sorted_media_types:
            insights.append(f"{format_quote_and_bold(sorted_media_types[0][0])} is the most frequently used media type, comprising {format_quote_and_bold(f'{sorted_media_types[0][1] * 100:.1f}%')} of content.")
        if len(sorted_media_types) > 1:
            insights.append(f"The second most common media type is {format_quote_and_bold(sorted_media_types[1][0])}, suggesting a diversified content strategy.")
        if total_media > 0:
            distinct_media_types = len(media_type_counts)
            insights.append(f"There are {format_quote_and_bold(distinct_media_types)} distinct media types used, indicating a broad approach to content creation.")
        else:
            insights.append('No media type data available to generate specific insights.')


    elif chart_type == 'top_locations':
        if 'location' not in data.columns or 'engagements' not in data.columns:
            insights.append("Location or Engagements column missing for top locations analysis.")
            return insights

        location_engagements = data.groupby('location')['engagements'].sum().sort_values(ascending=False)
        top_5_locations = location_engagements.head(5)
        total_engagements = data['engagements'].sum()

        if not top_5_locations.empty:
            insights.append(f"{format_quote_and_bold(top_5_locations.index[0])} is the top location, contributing {format_quote_and_bold(f'{top_5_locations.iloc[0]:,.0f}')} engagements.")
            top_5_total_engagements = top_5_locations.sum()
            if total_engagements > 0:
                insights.append(f"The top 5 locations combined account for {format_quote_and_bold(f'{top_5_total_engagements / total_engagements * 100:.1f}%')} of total engagements.")
            if len(top_5_locations) > 1:
                insights.append(f"Other notable locations like {format_quote_and_bold(top_5_locations.index[1])} and {format_quote_and_bold(top_5_locations.index[min(2, len(top_5_locations)-1)])} also show strong engagement, indicating diverse audience geographical distribution.")
        else:
            insights.append('Limited location data available, making it difficult to identify strong geographical trends.')

    return insights

def generate_summary(data):
    """Generates a summary based on the filtered data."""
    if data.empty:
        return "No data available to generate a summary. Please upload a CSV file and ensure your filters return data."

    format_quote_and_bold = lambda text: f"“<strong>{text}</strong>”"
    summary_text = "<p class='text-gray-700 leading-relaxed mb-4'>Based on the current filtered data, here's a concise overview of the media intelligence trends:</p><ul class='list-disc list-inside text-gray-700'>"

    # Sentiment Summary
    if 'sentiment' in data.columns:
        sentiment_counts = data['sentiment'].value_counts()
        total_sentiments = sentiment_counts.sum()
        sorted_sentiments = sorted(sentiment_counts.items(), key=lambda item: item[1], reverse=True)
        if sorted_sentiments:
            summary_text += f"<li>The predominant sentiment observed is {format_quote_and_bold(sorted_sentiments[0][0])}, comprising {format_quote_and_bold(f'{(sorted_sentiments[0][1] / total_sentiments * 100):.1f}%')} of all mentions."
            if len(sorted_sentiments) > 1:
                summary_text += f" Significant portions are also attributed to {format_quote_and_bold(sorted_sentiments[1][0])} sentiment.</li>"
            else:
                summary_text += ".</li>"
    else:
        summary_text += "<li>Sentiment data is not available.</li>"

    # Engagement Trend Summary
    if 'date' in data.columns and 'engagements' in data.columns:
        engagements_by_date = data.groupby(data['date'].dt.date)['engagements'].sum().sort_index()
        if len(engagements_by_date) > 1:
            first_engagement = engagements_by_date.iloc[0]
            last_engagement = engagements_by_date.iloc[-1]
            trend = "stable"
            if last_engagement > first_engagement * 1.1:
                trend = "increasing"
            elif last_engagement < first_engagement * 0.9:
                trend = "decreasing"
            summary_text += f"<li>Overall, engagements show an {format_quote_and_bold(f'{trend} trend')} across the selected period.</li>"
        elif len(engagements_by_date) == 1:
            summary_text += f"<li>On the single recorded date, {format_quote_and_bold(engagements_by_date.index[0].strftime('%Y-%m-%d'))}, there were {format_quote_and_bold(f'{engagements_by_date.iloc[0]:,.0f}')} engagements.</li>"
        else:
            summary_text += f"<li>Engagement trend could not be determined due to insufficient date data.</li>"
    else:
        summary_text += "<li>Date or Engagements data is not available for trend analysis.</li>"

    # Platform Summary
    if 'platform' in data.columns and 'engagements' in data.columns:
        platform_engagements = data.groupby('platform')['engagements'].sum().sort_values(ascending=False)
        if not platform_engagements.empty:
            summary_text += f"<li>The primary platform for engagement is {format_quote_and_bold(platform_engagements.index[0])}, contributing significantly to total interactions."
            if len(platform_engagements) > 1:
                summary_text += f" Other notable platforms include {format_quote_and_bold(platform_engagements.index[1])}.</li>"
            else:
                summary_text += ".</li>"
    else:
        summary_text += "<li>Platform or Engagements data is not available for platform analysis.</li>"

    # Media Type Summary
    if 'media_type' in data.columns:
        media_type_counts = data['media_type'].value_counts(normalize=True)
        total_media = media_type_counts.sum()
        sorted_media_types = sorted(media_type_counts.items(), key=lambda item: item[1], reverse=True)
        if sorted_media_types:
            summary_text += f"<li>The most prevalent media type used is {format_quote_and_bold(sorted_media_types[0][0])} ({format_quote_and_bold(f'{(sorted_media_types[0][1] * 100):.1f}%')} of content).</li>"
    else:
        summary_text += "<li>Media Type data is not available.</li>"

    # Location Summary
    if 'location' in data.columns and 'engagements' in data.columns:
        location_engagements = data.groupby('location')['engagements'].sum().sort_values(ascending=False)
        top_3_locations = location_engagements.head(3)
        if not top_3_locations.empty:
            summary_text += f"<li>Geographically, {format_quote_and_bold(top_3_locations.index[0])} is the top-performing location in terms of engagement."
            if len(top_3_locations) > 1:
                other_locations = " and ".join([format_quote_and_bold(loc) for loc in top_3_locations.index[1:]])
                summary_text += f" Other key regions include {other_locations}.</li>"
            else:
                summary_text += ".</li>"
    else:
        summary_text += "<li>Location or Engagements data is not available for location analysis.</li>"

    summary_text += "</ul>"
    return summary_text

def generate_recommendations(data):
    """Generates recommendations based on the filtered data."""
    if data.empty:
        return "No data available to generate recommendations. Please upload a CSV file and ensure your filters return data."

    format_quote_and_bold = lambda text: f"“<strong>{text}</strong>”"
    recommendations_text = "<p class='text-gray-700 leading-relaxed mb-4'>Based on these insights, here are some strategic recommendations to consider:</p><ul class='list-disc list-inside text-gray-700'>"

    # Sentiment-based recommendations
    if 'sentiment' in data.columns:
        sentiment_counts = data['sentiment'].value_counts()
        total_sentiments = sentiment_counts.sum()
        positive_percentage = sentiment_counts.get('Positive', 0) / total_sentiments if total_sentiments > 0 else 0
        negative_percentage = sentiment_counts.get('Negative', 0) / total_sentiments if total_sentiments > 0 else 0

        if negative_percentage > 0.3 and positive_percentage < 0.5:
            recommendations_text += "<li>Consider implementing a proactive sentiment management strategy to address negative feedback and improve brand perception. This could involve direct engagement with critical posts or refining messaging.</li>"
        elif positive_percentage > 0.7:
            recommendations_text += "<li>Leverage the strong positive sentiment by identifying top-performing positive content and replicating its success. Encourage more user-generated content and testimonials.</li>"
        else:
            recommendations_text += "<li>Maintain consistent content quality to sustain current sentiment levels. Consider A/B testing different messaging to shift neutral sentiment towards positive.</li>"
    else:
        recommendations_text += "<li>Cannot provide sentiment-based recommendations due to missing sentiment data.</li>"

    # Engagement Trend recommendations
    if 'date' in data.columns and 'engagements' in data.columns:
        engagements_by_date = data.groupby(data['date'].dt.date)['engagements'].sum().sort_index()
        if len(engagements_by_date) > 1:
            first_engagement = engagements_by_date.iloc[0]
            last_engagement = engagements_by_date.iloc[-1]
            if last_engagement < first_engagement * 0.9:
                recommendations_text += "<li>Investigate the reasons behind the decreasing engagement trend. This might involve re-evaluating content formats, posting frequency, or audience targeting.</li>"
            elif last_engagement > first_engagement * 1.1:
                recommendations_text += "<li>Continue to analyze factors contributing to the increasing engagement to scale successful strategies. Explore new channels or content types that align with this growth.</li>"
        else:
            recommendations_text += "<li>Engagement trend data is insufficient for detailed recommendations.</li>"
    else:
        recommendations_text += "<li>Cannot provide engagement trend recommendations due to missing date or engagements data.</li>"

    # Platform-based recommendations
    if 'platform' in data.columns and 'engagements' in data.columns:
        platform_engagements = data.groupby('platform')['engagements'].sum().sort_values(ascending=False)
        if len(platform_engagements) > 1 and (platform_engagements.iloc[0] / (platform_engagements.iloc[1] if platform_engagements.iloc[1] > 0 else 1)) > 2:
            recommendations_text += f"<li>While {format_quote_and_bold(platform_engagements.index[0])} is performing exceptionally, consider diversifying efforts to other platforms like {format_quote_and_bold(platform_engagements.index[1])} to expand reach and reduce reliance on a single channel.</li>"
        elif not platform_engagements.empty:
            recommendations_text += "<li>Optimize content strategy for each platform based on its unique audience and engagement patterns to maximize impact.</li>"
    else:
        recommendations_text += "<li>Cannot provide platform-based recommendations due to missing platform or engagements data.</li>"

    # Media Type recommendations
    if 'media_type' in data.columns:
        media_type_counts = data['media_type'].value_counts(normalize=True)
        total_media = media_type_counts.sum()
        sorted_media_types = sorted(media_type_counts.items(), key=lambda item: item[1], reverse=True)
        if len(sorted_media_types) > 1 and (sorted_media_types[0][1]) > 0.7:
            recommendations_text += f"<li>Explore diversifying content formats beyond predominantly {format_quote_and_bold(sorted_media_types[0][0])} to cater to varied audience preferences and prevent content fatigue.</li>"
        elif not media_type_counts.empty:
            recommendations_text += "<li>Analyze which media types resonate most with your audience to optimize content creation.</li>"
    else:
        recommendations_text += "<li>Cannot provide media type recommendations due to missing media type data.</li>"

    # Location recommendations
    if 'location' in data.columns and 'engagements' in data.columns:
        location_engagements = data.groupby('location')['engagements'].sum().sort_values(ascending=False)
        total_engagements_all = data['engagements'].sum()
        if not location_engagements.empty and (location_engagements.iloc[0] / total_engagements_all) > 0.5:
            recommendations_text += f"<li>Develop location-specific campaigns or content for {format_quote_and_bold(location_engagements.index[0])} to capitalize on its high engagement. Also, investigate untapped potential in other high-engagement regions identified.</li>"
        elif not location_engagements.empty:
            recommendations_text += "<li>Analyze demographic and cultural nuances of top-performing locations to tailor content more effectively.</li>"
    else:
        recommendations_text += "<li>Cannot provide location-based recommendations due to missing location or engagements data.</li>"

    recommendations_text += "</ul>"
    return recommendations_text

# --- Streamlit UI Layout ---

st.markdown(
    """
    <style>
    .reportview-container .main {
        background: linear-gradient(to bottom right, #E0F7FA, #E1F5FE, #BBDEFB);
        font-family: 'Inter', sans-serif;
    }
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 0.5rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stTextInput>div>div>input {
        border-radius: 0.5rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stButton>button {
        border-radius: 9999px; /* Full rounded */
        font-weight: 700; /* bold */
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
    }
    .stCheckbox span {
        font-size: 1rem;
    }
    .stDateInput input {
        border-radius: 0.5rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stFileUploader {
        border-radius: 0.5rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        padding: 1.5rem;
        background-color: white;
    }
    section.main .block-container{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); text-align: center; margin-bottom: 32px;">
        <h1 style="font-size: 3rem; font-weight: 700; color: #1F2937; letter-spacing: -0.025em; margin-bottom: 0;">Interactive Media Intelligence Dashboard</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Session State Initialization ---
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None
if 'summary_text' not in st.session_state:
    st.session_state.summary_text = ""
if 'recommendations_text' not in st.session_state:
    st.session_state.recommendations_text = ""
if 'ai_generated_summary' not in st.session_state:
    st.session_state.ai_generated_summary = ""
if 'ai_generated_recommendations' not in st.session_state:
    st.session_state.ai_generated_recommendations = ""
if 'ai_error' not in st.session_state:
    st.session_state.ai_error = None
if 'openrouter_api_key' not in st.session_state:
    st.session_state.openrouter_api_key = ''
if 'selected_openrouter_model' not in st.session_state:
    st.session_state.selected_openrouter_model = 'gemini-2.0-flash'

# --- 1. Upload CSV Section ---
st.markdown(
    """
    <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
        <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">1. Upload Your CSV Data</h2>
        <p style="color: #4B5563; margin-bottom: 24px;">
            Please upload a CSV file with the following columns: <code>Date</code>, <code>Platform</code>, <code>Sentiment</code>, <code>Location</code>, <code>Engagements</code>, <code>Media Type</code>, <code>Influencer Brand</code>, <code>Post Type</code>.
        </p>
    """,
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader("", type="csv", label_visibility="collapsed")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.cleaned_data = clean_data(df)
        st.success("CSV file uploaded and processed successfully!")
        
        # Reset analysis when new file is uploaded
        st.session_state.summary_text = ""
        st.session_state.recommendations_text = ""
        st.session_state.ai_generated_summary = ""
        st.session_state.ai_generated_recommendations = ""
        st.session_state.ai_error = None

    except Exception as e:
        st.error(f"Error processing file: {e}. Please ensure it's a valid CSV with expected columns.")
        st.session_state.cleaned_data = None
st.markdown("</div>", unsafe_allow_html=True)


# --- 2. Data Cleaning Note ---
st.markdown(
    """
    <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
        <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">2. Data Cleaning Applied</h2>
        <p style="color: #4B5563;">
            The following cleaning steps are automatically applied upon upload:
        </p>
        <ul style="list-style-type: disc; margin-left: 20px; color: #4B5563; margin-top: 8px;">
            <li>Dates are converted to datetime objects.</li>
            <li>Missing 'Engagements' values are filled with <code>0</code>.</li>
            <li>Column names are normalized for consistency (e.g., 'Media Type' becomes 'media_type').</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)


# --- Data Filtering Section ---
if st.session_state.cleaned_data is not None and not st.session_state.cleaned_data.empty:
    st.markdown(
        """
        <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
            <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">Data Filters</h2>
        """,
        unsafe_allow_html=True
    )
    
    unique_platforms = ['All'] + sorted(st.session_state.cleaned_data['platform'].dropna().unique().tolist()) if 'platform' in st.session_state.cleaned_data.columns else ['All']
    unique_sentiments = ['All'] + sorted(st.session_state.cleaned_data['sentiment'].dropna().unique().tolist()) if 'sentiment' in st.session_state.cleaned_data.columns else ['All']
    unique_media_types = ['All'] + sorted(st.session_state.cleaned_data['media_type'].dropna().unique().tolist()) if 'media_type' in st.session_state.cleaned_data.columns else ['All']
    unique_locations = ['All'] + sorted(st.session_state.cleaned_data['location'].dropna().unique().tolist()) if 'location' in st.session_state.cleaned_data.columns else ['All']

    if 'date' in st.session_state.cleaned_data.columns and not st.session_state.cleaned_data['date'].empty:
        min_date_data = st.session_state.cleaned_data['date'].min().date()
        max_date_data = st.session_state.cleaned_data['date'].max().date()
    else:
        min_date_data = datetime(2020, 1, 1).date()
        max_date_data = datetime.now().date()

    col1, col2, col3 = st.columns(3)
    with col1:
        platform_filter = st.selectbox("Platform", unique_platforms)
        sentiment_filter = st.selectbox("Sentiment", unique_sentiments)
    with col2:
        media_type_filter = st.selectbox("Media Type", unique_media_types)
        location_filter = st.selectbox("Location", unique_locations)
    with col3:
        start_date_filter = st.date_input("Start Date", value=min_date_data, min_value=min_date_data, max_value=max_date_data)
        end_date_filter = st.date_input("End Date", value=max_date_data, min_value=min_date_data, max_value=max_date_data)

    filtered_data = st.session_state.cleaned_data.copy()

    if platform_filter != 'All':
        filtered_data = filtered_data[filtered_data['platform'] == platform_filter]
    if sentiment_filter != 'All':
        filtered_data = filtered_data[filtered_data['sentiment'] == sentiment_filter]
    if media_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['media_type'] == media_type_filter]
    if location_filter != 'All':
        filtered_data = filtered_data[filtered_data['location'] == location_filter]

    # Date filtering
    if 'date' in filtered_data.columns:
        filtered_data = filtered_data[
            (filtered_data['date'].dt.date >= start_date_filter) &
            (filtered_data['date'].dt.date <= end_date_filter)
        ]

    if st.button("Clear Filters", key="clear_filters_btn", help="Resets all filters to default 'All' or min/max date values"):
        # This will trigger a rerun and effectively clear filters due to default values on next run
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 3. Interactive Charts & 4. Top Insights ---
    st.markdown(
        """
        <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
            <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">3. Interactive Charts & 4. Top Insights</h2>
        """,
        unsafe_allow_html=True
    )
    if filtered_data.empty:
        st.warning("No data matches current filters. Please adjust your filter selections or clear them to see charts.")
    else:
        # Chart 1: Sentiment Breakdown (Pie Chart)
        st.markdown(
            """
            <div style="background-color:white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); margin-bottom: 40px;">
                <h3 style="font-size: 1.5rem; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Sentiment Breakdown</h3>
            """,
            unsafe_allow_html=True
        )
        if 'sentiment' in filtered_data.columns:
            sentiment_counts = filtered_data['sentiment'].value_counts()
            fig_sentiment = px.pie(
                names=sentiment_counts.index,
                values=sentiment_counts.values,
                title='Sentiment Breakdown',
                hole=0.4,
                color_discrete_map={'Positive':'#22C55E', 'Negative':'#EF4444', 'Neutral':'#6B7280'}
            )
            fig_sentiment.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_sentiment, use_container_width=True)
            st.markdown(f"<h4 style='font-size: 1.25rem; font-weight: 500; color: #4B5563; margin-top: 16px; margin-bottom: 8px;'>Top 3 Insights:</h4>", unsafe_allow_html=True)
            for insight in generate_insights(filtered_data, 'sentiment'):
                st.markdown(f"<li style='margin-bottom: 4px; color: #4B5563;'>{insight}</li>", unsafe_allow_html=True)
        else:
            st.info("Sentiment column not found in data for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)


        # Chart 2: Engagement Trend over Time (Line Chart)
        st.markdown(
            """
            <div style="background-color:white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); margin-bottom: 40px;">
                <h3 style="font-size: 1.5rem; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Engagement Trend Over Time</h3>
            """,
            unsafe_allow_html=True
        )
        if 'date' in filtered_data.columns and 'engagements' in filtered_data.columns:
            engagement_trend_data = filtered_data.groupby(filtered_data['date'].dt.date)['engagements'].sum().reset_index()
            engagement_trend_data.columns = ['Date', 'Total Engagements']
            fig_engagement_trend = px.line(
                engagement_trend_data,
                x='Date',
                y='Total Engagements',
                title='Engagement Trend Over Time',
                line_shape='linear'
            )
            fig_engagement_trend.update_traces(line_color='#3B82F6', marker_color='#3B82F6')
            st.plotly_chart(fig_engagement_trend, use_container_width=True)
            st.markdown(f"<h4 style='font-size: 1.25rem; font-weight: 500; color: #4B5563; margin-top: 16px; margin-bottom: 8px;'>Top 3 Insights:</h4>", unsafe_allow_html=True)
            for insight in generate_insights(filtered_data, 'engagement_trend'):
                st.markdown(f"<li style='margin-bottom: 4px; color: #4B5563;'>{insight}</li>", unsafe_allow_html=True)
        else:
            st.info("Date or Engagements column not found in data for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Chart 3: Platform Engagements (Bar Chart)
        st.markdown(
            """
            <div style="background-color:white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); margin-bottom: 40px;">
                <h3 style="font-size: 1.5rem; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Engagements by Platform</h3>
            """,
            unsafe_allow_html=True
        )
        if 'platform' in filtered_data.columns and 'engagements' in filtered_data.columns:
            platform_engagements_data = filtered_data.groupby('platform')['engagements'].sum().reset_index()
            platform_engagements_data = platform_engagements_data.sort_values(by='engagements', ascending=False)
            fig_platform_engagements = px.bar(
                platform_engagements_data,
                x='platform',
                y='engagements',
                title='Engagements by Platform',
                color_discrete_sequence=['#0EA5E9']
            )
            st.plotly_chart(fig_platform_engagements, use_container_width=True)
            st.markdown(f"<h4 style='font-size: 1.25rem; font-weight: 500; color: #4B5563; margin-top: 16px; margin-bottom: 8px;'>Top 3 Insights:</h4>", unsafe_allow_html=True)
            for insight in generate_insights(filtered_data, 'platform_engagements'):
                st.markdown(f"<li style='margin-bottom: 4px; color: #4B5563;'>{insight}</li>", unsafe_allow_html=True)
        else:
            st.info("Platform or Engagements column not found in data for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Chart 4: Media Type Mix (Pie Chart)
        st.markdown(
            """
            <div style="background-color:white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); margin-bottom: 40px;">
                <h3 style="font-size: 1.5rem; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Media Type Mix</h3>
            """,
            unsafe_allow_html=True
        )
        if 'media_type' in filtered_data.columns:
            media_type_counts = filtered_data['media_type'].value_counts()
            fig_media_type = px.pie(
                names=media_type_counts.index,
                values=media_type_counts.values,
                title='Media Type Mix',
                color_discrete_sequence=['#F97316', '#A855F7', '#10B981', '#F59E0B', '#6B21A8', '#EF4444', '#3B82F6', '#22C55E']
            )
            fig_media_type.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_media_type, use_container_width=True)
            st.markdown(f"<h4 style='font-size: 1.25rem; font-weight: 500; color: #4B5563; margin-top: 16px; margin-bottom: 8px;'>Top 3 Insights:</h4>", unsafe_allow_html=True)
            for insight in generate_insights(filtered_data, 'media_type'):
                st.markdown(f"<li style='margin-bottom: 4px; color: #4B5563;'>{insight}</li>", unsafe_allow_html=True)
        else:
            st.info("Media Type column not found in data for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Chart 5: Top 5 Locations by Engagement (Bar Chart)
        st.markdown(
            """
            <div style="background-color:white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); margin-bottom: 40px;">
                <h3 style="font-size: 1.5rem; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Top 5 Locations by Engagement</h3>
            """,
            unsafe_allow_html=True
        )
        if 'location' in filtered_data.columns and 'engagements' in filtered_data.columns:
            location_engagements_data = filtered_data.groupby('location')['engagements'].sum().reset_index()
            location_engagements_data = location_engagements_data.sort_values(by='engagements', ascending=False).head(5)
            fig_top_locations = px.bar(
                location_engagements_data,
                x='location',
                y='engagements',
                title='Top 5 Locations by Engagement',
                color_discrete_sequence=['#EC4899']
            )
            st.plotly_chart(fig_top_locations, use_container_width=True)
            st.markdown(f"<h4 style='font-size: 1.25rem; font-weight: 500; color: #4B5563; margin-top: 16px; margin-bottom: 8px;'>Top 3 Insights:</h4>", unsafe_allow_html=True)
            for insight in generate_insights(filtered_data, 'top_locations'):
                st.markdown(f"<li style='margin-bottom: 4px; color: #4B5563;'>{insight}</li>", unsafe_allow_html=True)
        else:
            st.info("Location or Engagements column not found in data for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


    # --- Analysis Generation Section ---
    st.markdown(
        """
        <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
            <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">5. Generate Executive Summary & Recommendations</h2>
            <p style="color: #4B5563; margin-bottom: 24px;">Choose how you'd like to generate your analysis:</p>
        """,
        unsafe_allow_html=True
    )
    
    col_ai_buttons = st.columns(2)
    with col_ai_buttons[0]:
        if st.button("Generate Analysis (Our Model)", key="generate_our_analysis_btn"):
            st.session_state.ai_generated_summary = "" # Clear AI results
            st.session_state.ai_generated_recommendations = ""
            st.session_state.ai_error = None
            st.session_state.summary_text = generate_summary(filtered_data)
            st.session_state.recommendations_text = generate_recommendations(filtered_data)
            st.rerun() # Rerun to display generated text

    with col_ai_buttons[1]:
        if st.button("Generate Analysis (OpenRouter AI)", key="generate_openrouter_ai_btn", disabled=False): # Add AI model input
            # Check if API key is provided
            if not st.session_state.openrouter_api_key:
                st.session_state.ai_error = "Please enter your OpenRouter API Key."
                st.rerun()

            st.session_state.ai_error = None
            st.session_state.ai_generated_summary = ""
            st.session_state.ai_generated_recommendations = ""
            st.session_state.summary_text = "" # Clear our model results
            st.session_state.recommendations_text = ""

            with st.spinner("Generating AI Analysis..."):
                try:
                    # Prepare data for AI prompt
                    total_engagements = filtered_data['engagements'].sum() if 'engagements' in filtered_data.columns else 0
                    num_posts = len(filtered_data)

                    sentiment_distribution = {}
                    if 'sentiment' in filtered_data.columns:
                        sentiment_counts = filtered_data['sentiment'].value_counts()
                        total_s = sentiment_counts.sum()
                        if total_s > 0:
                            for s, count in sentiment_counts.items():
                                sentiment_distribution[s] = f'{ (count / total_s * 100):.1f}% ({count} posts)'
                    formatted_sentiments = ", ".join([f"{s}: {val}" for s, val in sentiment_distribution.items()]) if sentiment_distribution else 'N/A'

                    platforms = filtered_data['platform'].dropna().unique().tolist() if 'platform' in filtered_data.columns else []
                    media_types = filtered_data['media_type'].dropna().unique().tolist() if 'media_type' in filtered_data.columns else []
                    locations = filtered_data['location'].dropna().unique().tolist() if 'location' in filtered_data.columns else []

                    prompt = f"""Analyze the following media intelligence data points and provide a concise executive summary and actionable recommendations for future strategies.

Data points:
- Total Engagements: {total_engagements:,.0f}
- Number of Posts: {num_posts}
- Sentiment Distribution: {formatted_sentiments}
- Platforms involved: {', '.join(platforms) or 'N/A'}
- Media Types used: {', '.join(media_types) or 'N/A'}
- Locations represented: {', '.join(locations) or 'N/A'}

Provide the summary as a paragraph and the recommendations as a bulleted list. The recommendations should be practical and focused on optimizing media strategies based on the provided data.
"""
                    # OpenRouter API call
                    headers = {
                        "Authorization": f"Bearer {st.session_state.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "X-Title": "Streamlit Media Intelligence Dashboard" # Optional, for OpenRouter analytics
                    }
                    data_payload = {
                        "model": st.session_state.selected_openrouter_model,
                        "messages": [{"role": "user", "content": prompt}]
                    }

                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        data=json.dumps(data_payload)
                    )

                    response.raise_for_status() # Raise an exception for HTTP errors
                    ai_result = response.json()

                    if ai_result and ai_result['choices'] and ai_result['choices'][0]['message']['content']:
                        ai_response_text = ai_result['choices'][0]['message']['content']
                        
                        # Attempt to parse summary and recommendations
                        lines = [line.strip() for line in ai_response_text.split('\n') if line.strip()]
                        current_section = ''
                        summary_parts = []
                        recommendations_parts = []

                        for line in lines:
                            if "summary" in line.lower() and not current_section: # only if section is not set
                                current_section = 'summary'
                                if not line.lower().startswith("summary"): # If it's not just "Summary:", keep the line
                                    summary_parts.append(line)
                            elif "recommendations" in line.lower() and current_section != 'recommendations': # only if section is not set
                                current_section = 'recommendations'
                                if not line.lower().startswith("recommendations"): # If it's not just "Recommendations:", keep the line
                                    recommendations_parts.append(line)
                            elif current_section == 'summary':
                                summary_parts.append(line)
                            elif current_section == 'recommendations':
                                recommendations_parts.append(line.replace(/^- /, '')) # Remove bullet if present


                        # If parsing didn't find clear sections, just use the whole text
                        if not summary_parts and not recommendations_parts:
                            st.session_state.ai_generated_summary = "<p class='text-gray-700 leading-relaxed mb-4'>Could not parse distinct summary/recommendations. Here's the full AI response:</p>"
                            st.session_state.ai_generated_recommendations = f"<p class='text-gray-700 leading-relaxed mb-4'>{ai_response_text}</p>"
                        else:
                            st.session_state.ai_generated_summary = f"<p class='text-gray-700 leading-relaxed mb-4'>{' '.join(summary_parts)}</p>"
                            st.session_state.ai_generated_recommendations = f"<ul class='list-disc list-inside text-gray-700'>{''.join([f'<li class="mb-1">{rec}</li>' for rec in recommendations_parts])}</ul>"

                    else:
                        st.session_state.ai_error = "AI response was empty or malformed."

                except requests.exceptions.RequestException as req_err:
                    st.session_state.ai_error = f"Network or API request error: {req_err}. Please check your internet connection and API key."
                except json.JSONDecodeError:
                    st.session_state.ai_error = "Failed to parse AI response. Invalid JSON received."
                except Exception as e:
                    st.session_state.ai_error = f"An unexpected error occurred: {e}. Please check your API key and model selection."
            st.rerun() # Rerun to display generated text

    st.markdown(
        """
        <div style="margin-top: 32px; padding: 16px; background-color: #F8F8F8; border-radius: 8px; border: 1px solid #E0E0E0;">
            <h3 style="font-size: 1.25rem; font-weight: 600; color: #374151; margin-bottom: 16px;">OpenRouter AI Configuration</h3>
            </div>
        """,
        unsafe_allow_html=True
    )
    st.session_state.openrouter_api_key = st.text_input("OpenRouter API Key", type="password", help="Your API key from openrouter.ai (starts with sk-)", value=st.session_state.openrouter_api_key)
    st.markdown("<p style='color: #6B7280; font-size: 0.75rem; margin-top: -8px; margin-bottom: 16px;'>Your API key is used for secure access to OpenRouter models.</p>", unsafe_allow_html=True)
    
    open_router_models = [
        'google/gemini-pro', # A good general purpose model
        'openai/gpt-3.5-turbo',
        'openai/gpt-4o',
        'anthropic/claude-3-opus',
        'mistralai/mistral-7b-instruct',
        'google/gemini-1.5-flash-pro',
        'google/gemini-1.5-pro-latest',
        'mistralai/mixtral-8x7b-instruct',
        'perplexity/llama-3-sonar-large-32k-online'
    ]
    st.session_state.selected_openrouter_model = st.selectbox("Select AI Model", open_router_models, index=open_router_models.index(st.session_state.selected_openrouter_model))
    
    if st.session_state.ai_error:
        st.error(st.session_state.ai_error)
    
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Display Generated Summary and Recommendations ---
    if st.session_state.summary_text:
        st.markdown(
            f"""
            <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
                <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">6. Data Summary (Our Model)</h2>
                {st.session_state.summary_text}
            </div>
            """,
            unsafe_allow_html=True
        )

    if st.session_state.recommendations_text:
        st.markdown(
            f"""
            <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
                <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">7. Key Recommendations (Our Model)</h2>
                {st.session_state.recommendations_text}
            </div>
            """,
            unsafe_allow_html=True
        )

    if st.session_state.ai_generated_summary:
        st.markdown(
            f"""
            <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
                <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">6. Data Summary (OpenRouter AI)</h2>
                {st.session_state.ai_generated_summary}
            </div>
            """,
            unsafe_allow_html=True
        )

    if st.session_state.ai_generated_recommendations:
        st.markdown(
            f"""
            <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); margin-bottom: 32px;">
                <h2 style="font-size: 1.875rem; font-weight: 600; color: #374151; margin-bottom: 16px;">7. Key Recommendations (OpenRouter AI)</h2>
                {st.session_state.ai_generated_recommendations}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # --- PDF Download Button at the bottom ---
    st.markdown(
        """
        <div style="background-color:white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); text-align: center; margin-top: 32px;">
        """,
        unsafe_allow_html=True
    )
    st.warning("Note: Direct PDF download of the rendered UI is not directly supported in Streamlit. You would typically generate a report on the server-side for download.")
    # You can add a button here to trigger a custom PDF generation logic if implemented
    # if st.button("Download Report (PDF) - Feature Not Implemented Yet"):
    #     st.write("This feature would generate a server-side PDF report.")
    st.markdown("</div>", unsafe_allow_html=True)
