import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import tkinter as tk
from tkinter import messagebox
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException


# Setting up Chrome options for headless mode
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode to avoid opening the browser window
options.add_argument("--disable-gpu")  # Disable GPU acceleration for smoother headless mode
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options) # Initialize the Chrome driver


# Step 1 - Creating a function to scrape the required data from IMDB
def scrape_imdb():
    url = "https://www.imdb.com/search/title/?genres={genre}"
    genres = ['action', 'comedy', 'drama', 'thriller']
    movies = [] # Empty list to store movie data
    
    # Loop through each genre to scrape movie data
    for genre in genres:
        driver.get(url.format(genre=genre))
        time.sleep(2) # Wait for the page to fully load
        
        # Loading more movies by clicking on the '50 more' button on the IMDB page. For our example, we have taken 5 clicks into consideration
        for _ in range(5):
            try:
                # Wait for the "50 more" button to load and become clickable
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., '50 more')]"))
                )
                load_more_button = WebDriverWait(driver,10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., '50 more')]"))
                )
                
                # Scroll the screen to the bottom to bring the "50 more button in view"
                # After multiple failed attempts of clicking the 50 more buttons using selenium, used the following method to overcome the issue
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(3)
                
            except NoSuchElementException:
                print("All the movies loaded for genre:", genre)
                break
        
        # Find all movie containers on the page using Inspect on the web page
        movie_containers = driver.find_elements(By.CLASS_NAME, 'ipc-metadata-list-summary-item')
        for container in movie_containers:
            # Fetch title
            title = container.find_element(By.CLASS_NAME, 'ipc-title__text').text
            
            # Fetch Release Year
            try:
                release_year = container.find_element(By.CLASS_NAME, 'sc-5bc66c50-6').text
            except NoSuchElementException:
                release_year = None
            
            # Fetch Rating
            try:
                rating = container.find_element(By.CLASS_NAME, 'ipc-rating-star--rating').text
            except NoSuchElementException:
                rating = None
            
            genre_text = genre
            
            
            # Append movies to the empty list
            movies.append({
                "Title": title,
                "Genre": genre_text,
                "Release Year": release_year,
                "Rating": rating
            })
    
    # Save data to csv
    if movies:
        pd.DataFrame(movies).to_csv("movies.csv", index = False)
        print("Scraping complete and data saved to movies.csv")
    else:
        print("No data scraped")
    
    
    # Close the driver
    driver.quit()


# Step 2 - Run the scrape function if you do not have the movies dataset already created in csv
# if __name__ == "__main__":
#     scrape_imdb()
                

# Step 3 - Load and Clean data from csv
def load_movie_data():
    try:
        # Load data from the CSV file into a pandas DataFrame
        data = pd.read_csv("movies.csv")
        data.dropna(subset=["Title", "Rating"],inplace = True) # Removing null rows for title and rating.
        return data
    except Exception as e:
        # Print error message if the file can't be loaded
        print("Error loading data:", {e})
        return None


# Step 4 - Filter Movies Based on genre input from user
def filter_movies(data, genre = None, min_rank=None):
    # Start with the full data and apply filters based on genre and rating
    filtered = data
    if genre:
        filtered = filtered[filtered['Genre'] == genre]  # Filter by selected genre
    if min_rank:
        filtered = filtered[filtered['Rating'] >= min_rank] # Filter by rating threshold
    
    return filtered


# Step 5 - Get a random movie suggestion and Top 15 movies of that genre
def suggest_random_and_top_movies(data, genre=None, min_rank = None):
    # First, apply the genre and rating filters
    filtered = filter_movies(data, genre, min_rank)
    
    # If no movies match the filter, return a message saying no movies were found
    if filtered.empty:
        return "No movies found for the given criteria."
        
    # Get a random movie suggestion
    random_movie = filtered.sample(1).iloc[0].to_dict()
    
    # Get top 15 movies by ratings
    filtered['Rating'] = pd.to_numeric(filtered['Rating'], errors='coerce')
    top_15_movies = filtered.sort_values(by='Rating', ascending=False).head(15).to_dict(orient='records')
    
    return random_movie, top_15_movies


# Step 6 - GUI setup
def create_gui(data):
    def on_suggest():
        # Get the genre and minimum rating input from the user
        genre = genre_var.get()
        min_rank = rank_var.get()
        
        try:
            min_rank = float(min_rank) if min_rank else None
        except ValueError:
            # Show an error message if the input is not a valid number
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Rating")
            return
        
        suggestion = suggest_random_and_top_movies(data, genre, min_rank)
        
        if isinstance(suggestion, str):
            messagebox.showinfo("Suggestion", suggestion)
        else:
            random_movie, top_15_movies = suggestion
            
            # Display random movie suggestion
            random_result = f"Random Movie/TV Show:\nTitle: {random_movie['Title']}\nGenre: {random_movie['Genre']}\nYear: {random_movie['Release Year']}\n" \
                            f"Rating: {random_movie['Rating']}\n"
            messagebox.showinfo("Random Movie/TV Show Suggestion", random_result)
            
            # Display top movies
            top_15_result = "Top Movies/TV Shows:\n\n"
            for idx, movie in enumerate(top_15_movies, start=1):
                top_15_result += f"{idx}. {movie['Title']} ({movie['Release Year']})\nRating: {movie['Rating']}\n\n"
            messagebox.showinfo("Top Movies/TV Shows", top_15_result)
    
    # GUI Window setup
    root = tk.Tk()
    root.title("Movie/TV Show Suggestion App") # Window title
    root.geometry("300x200") # Window size
    
    # Dropdown menu for genre selection
    tk.Label(root, text="Choose genre").grid(row=0, column=0)
    genre_var = tk.StringVar(value="all") # Default value is 'all'
    genre_dropdown = tk.OptionMenu(root, genre_var, *['all', 'action', 'comedy', 'drama', 'thriller'])
    genre_dropdown.grid(row=0, column=1)
    
    # Input field for minimum rating
    tk.Label(root, text='Minimum Rating').grid(row=1, column=0)
    rank_var = tk.StringVar()
    tk.Entry(root, textvariable=rank_var).grid(row=1, column=1)
    
    # Button to trigger movie suggestion
    tk.Button(root, text="Suggest Movie/TV Show", command=on_suggest).grid(row=3, columnspan=2)
    
    root.mainloop()


# Step 7 - Running the App
if __name__ == "__main__":
    movie_data = load_movie_data() # Load movie data from CSV
    if movie_data is not None:
        create_gui(movie_data) # Start the GUI if data is available
    else:
        print("Failed to load movie data.")
    