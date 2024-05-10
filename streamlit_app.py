import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Function to fetch weather data and return DataFrames
def fetch_weather_data(latitude, longitude, start_date, end_date):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["precipitation", "rain"],
        "daily": ["precipitation_sum", "rain_sum"],
        "timezone": "America/New_York",
        "start_date": start_date,
        "end_date": end_date
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]  # Assuming only one location is returned

    hourly = response.Hourly()
    hourly_precipitation = hourly.Variables(0).ValuesAsNumpy()
    hourly_rain = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )
    }
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["rain"] = hourly_rain

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    daily = response.Daily()
    daily_precipitation_sum = daily.Variables(0).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(1).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        )
    }
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["rain_sum"] = daily_rain_sum

    daily_dataframe = pd.DataFrame(data=daily_data)

    return hourly_dataframe, daily_dataframe


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
        st.line_chart(hourly_data.set_index("date"))

        # Display daily data graph
        st.subheader("Daily Data")
        st.line_chart(daily_data.set_index("date"))

        # Download CSV files
        st.subheader("Download Data")
        st.write("Download Hourly Data CSV")
        st.download_button("Hourly Data CSV", hourly_data.to_csv(), "hourly_data.csv")

        st.write("Download Daily Data CSV")
        st.download_button("Daily Data CSV", daily_data.to_csv(), "daily_data.csv")


if __name__ == "__main__":
    main()
