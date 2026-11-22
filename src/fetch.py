import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")

if not API_KEY:
    raise ValueError("TMDB_API_KEY is not configured")


def fetch_movie(session, movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"

    response = session.get(
        url,
        params={"api_key": API_KEY},
        timeout=(3.05, 10)
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    return response.json()


def fetch_credits(session, movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"

    response = session.get(
        url,
        params={"api_key": API_KEY},
        timeout=(3.05, 10)
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    return response.json()
