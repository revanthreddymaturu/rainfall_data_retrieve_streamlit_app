import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def calculate_daily_averaged_wind_direction(hourly_directions):
    # Convert degrees to radians for trigonometric functions
    radians = np.deg2rad(hourly_directions)
    
    # Calculate the u and v components
    u_components = np.cos(radians)
    v_components = np.sin(radians)
    
    # Calculate the mean of the components
    mean_u = np.mean(u_components)
    mean_v = np.mean(v_components)
    
    # Calculate the averaged wind direction in radians
    avg_direction_rad = np.arctan2(mean_v, mean_u)
    
    # Convert the averaged direction back to degrees
    avg_direction_deg = np.rad2deg(avg_direction_rad)
    
    # Normalize the direction to be within [0, 360) degrees
    avg_direction_deg = avg_direction_deg % 360
    
    return avg_direction_deg


# Function to fetch weather data and return DataFrames
def fetch_weather_data(latitude, longitude, start_date, end_date):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["precipitation", "rain","wind_speed_10m", "wind_direction_10m"],
        "daily": ["precipitation_sum", "rain_sum"],
        "timezone": "America/New_York",
        "start_date": start_date,
        "end_date": end_date
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]  # Assuming only one location is returned

    hourly = response.Hourly()
    

    hourly_dataframe =pd.DataFrame({
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "precipitation": hourly.Variables(0).ValuesAsNumpy(),
        "rain": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(3).ValuesAsNumpy()
    })

    # Group by date to calculate daily aggregates
    hourly_dataframe['date_only'] = hourly_dataframe['date'].dt.floor('d')  # Normalize date to days for grouping
    daily_aggregates = hourly_dataframe.groupby('date_only').agg({
        'precipitation': 'sum',
        'rain': 'sum',
        'wind_speed_10m': 'mean',
        'wind_direction_10m': calculate_daily_averaged_wind_direction
    }).reset_index()
    daily_aggregates.columns = ['date', 'precipitation_sum', 'rain_sum', 'average_wind_speed', 'average_wind_direction']

    return hourly_dataframe, daily_aggregates


# Streamlit app
def main():
    st.title("Rainfall Data")

    # User input
    latitude = st.number_input("Enter Latitude", value=38.9282)
    longitude = st.number_input("Enter Longitude", value=-76.9158)
    start_date = st.date_input("Enter Start Date", value=pd.Timestamp.today())
    end_date = st.date_input("Enter End Date", value=pd.Timestamp.today())

    if st.button("Request Data"):
        # Fetch weather data
        hourly_data, daily_data = fetch_weather_data(latitude, longitude, start_date.strftime("%Y-%m-%d"),
                                                      end_date.strftime("%Y-%m-%d"))

        # Display hourly data graph
        st.subheader("Hourly Data")
        st.line_chart(hourly_data.set_index("date")[['precipitation', 'rain', 'wind_speed_10m']])

        # Display daily data graph
        st.subheader("Daily Data")
        st.line_chart(daily_data.set_index("date")[['precipitation_sum', 'rain_sum', 'average_wind_speed', 'average_wind_direction']])

        # Download CSV files
        st.subheader("Download Data")
        st.write("Download Hourly Data CSV")
        st.download_button("Hourly Data CSV", hourly_data.to_csv(), "hourly_data.csv")

        st.write("Download Daily Data CSV")
        st.download_button("Daily Data CSV", daily_data.to_csv(), "daily_data.csv")


if __name__ == "__main__":
    main()
