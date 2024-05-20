import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Constants
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Function to calculate daily averaged wind direction
def calculate_daily_averaged_wind_direction(hourly_directions):
    radians = np.deg2rad(hourly_directions)
    u_components = np.cos(radians)
    v_components = np.sin(radians)
    mean_u = np.mean(u_components)
    mean_v = np.mean(v_components)
    avg_direction_rad = np.arctan2(mean_v, mean_u)
    avg_direction_deg = np.rad2deg(avg_direction_rad)
    return avg_direction_deg % 360

# Function to fetch weather data and return DataFrames
def fetch_weather_data(latitude, longitude, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "precipitation,rain,wind_speed_10m,wind_direction_10m",
        "daily": "precipitation_sum,rain_sum",
        "timezone": "America/New_York"
    }
    response = requests.get(API_BASE_URL, params=params).json()

    # Parse hourly data
    hourly_data = pd.DataFrame({
        "date": pd.to_datetime(response['hourly']['time']),
        "hourly_precipitation": response['hourly']['precipitation'],
        "hourly_rain": response['hourly']['rain'],
        "wind_speed_10m": response['hourly']['wind_speed_10m'],
        "wind_direction_10m": response['hourly']['wind_direction_10m']
    })

    # Group by date to calculate daily aggregates for wind
    hourly_data['date_only'] = hourly_data['date'].dt.floor('d')
    daily_wind_aggregates = hourly_data.groupby('date_only').agg({
        'wind_speed_10m': 'mean',
        'wind_direction_10m': calculate_daily_averaged_wind_direction
    }).reset_index()

    # Parse daily data
    daily_data = pd.DataFrame({
        "date": pd.to_datetime(response['daily']['time']),
        "precipitation_sum": response['daily']['precipitation_sum'],
        "rain_sum": response['daily']['rain_sum']
    })

    # Combine data
    daily_data = daily_data.merge(daily_wind_aggregates, left_on='date', right_on='date_only', how='left')
    daily_data.drop(columns='date_only', inplace=True)
    daily_data.rename(columns={'wind_speed_10m': 'average_wind_speed', 'wind_direction_10m': 'average_wind_direction'}, inplace=True)

    return hourly_data, daily_data

# Streamlit app main function
def main():
    st.title("Weather Data Analysis")

    # User input
    latitude = st.number_input("Enter Latitude", value=38.9282)
    longitude = st.number_input("Enter Longitude", value=-76.9158)
    start_date = st.date_input("Enter Start Date", value=datetime.today())
    end_date = st.date_input("Enter End Date", value=datetime.today())

    if st.button("Request Data"):
        try:
            # Fetch weather data
            hourly_data, daily_data = fetch_weather_data(latitude, longitude, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

            # Display hourly data graph
            st.subheader("Hourly Data")
            st.line_chart(hourly_data.set_index("date")[['hourly_precipitation', 'hourly_rain', 'wind_speed_10m']])

            # Display daily data graph
            st.subheader("Daily Data")
            st.line_chart(daily_data.set_index("date")[['precipitation_sum', 'rain_sum', 'average_wind_speed', 'average_wind_direction']])

            # Download CSV files
            st.subheader("Download Data")
            st.download_button("Download Hourly Data CSV", hourly_data.to_csv(index=False), "hourly_data.csv")
            st.download_button("Download Daily Data CSV", daily_data.to_csv(index=False), "daily_data.csv")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
