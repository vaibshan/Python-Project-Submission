
from bs4 import BeautifulSoup
import pandas as pd
import random
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk 
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


# --------------------------------------------------------------------------------------------------------------------------------
# Step 1 - ChromeDriver
# --------------------------------------------------------------------------------------------------------------------------------

options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Tried doing scraping in headless mode but I think it doesn't support
options.add_argument("--window-position=-2400,-2400")  # Move the browser window off-screen || Used this instead of headless
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)  # Initializing the Chrome driver


# --------------------------------------------------------------------------------------------------------------------------------
# Step 2 - Global Variables to track the progress of scraping and UI updates
# --------------------------------------------------------------------------------------------------------------------------------

progress_var = None
progress_text_label = None  # Label to display the progress percentage
close_warning_label = None  # Label to show a warning not to close the window


# --------------------------------------------------------------------------------------------------------------------------------
# Step 3 - Function to scrape data from IMDB based on genres
# --------------------------------------------------------------------------------------------------------------------------------
 
def scrape_imdb(progress_callback, completion_callback):
    url = "https://www.imdb.com/search/title/?genres={genre}"  
    genres = ['action', 'comedy', 'drama', 'thriller']  
    movies = []  

    total_steps = len(genres) + 5  # Total steps to scrape (5 steps for loading more movies per genre)

    # Loop through each genre to scrape movie data
    for i, genre in enumerate(genres):
        try:
            driver.get(url.format(genre=genre))
            time.sleep(5)  # Wait for the page to load completely
        except Exception as e:
            print(f"Error loading page for genre {genre}: {e}")
            continue # Skip to next genre if page fails to load

        progress_callback(int(((i + 1) / len(genres)) * 100))  # Update progress after scraping each genre (10% per genre)

        # Click the '50 more' button 5 times to load more movies
        for _ in range(5):
            try:
                # Try finding and clicking the "50 more" button to load additional movies
                driver.find_element(By.XPATH, "//button[contains(., '50 more')]")
                load_more_button = driver.find_element(By.XPATH, "//button[contains(., '50 more')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)  # Scroll to the button
                time.sleep(1)
                driver.execute_script("arguments[0].click();", load_more_button)  # Click the button to load more
                time.sleep(3)
            except NoSuchElementException:
                print(f"All movies loaded for genre: {genre}")
                break  

        # Find all movie containers on the page
        movie_containers = driver.find_elements(By.CLASS_NAME, 'ipc-metadata-list-summary-item')
        time.sleep(2)  

        # Extract information from each movie container
        for container in movie_containers:
            # Get the title of the movie
            title = container.find_element(By.CLASS_NAME, 'ipc-title__text').text

            # Get the release year
            try:
                release_year = container.find_element(By.CLASS_NAME, 'sc-5bc66c50-6').text
            except NoSuchElementException:
                release_year = None  # If no release year is found, set it as None

            # Get the movie rating
            try:
                rating = container.find_element(By.CLASS_NAME, 'ipc-rating-star--rating').text
            except NoSuchElementException:
                rating = None  

            genre_text = genre 

            # Append the movie data to the list
            movies.append({
                "Title": title,
                "Genre": genre_text,
                "Release Year": release_year,
                "Rating": rating
            })

        # Update progress after scraping each genre (20% completion per genre)
        progress_callback(int(((i + 1) / len(genres)) * 100))

    # After scraping all genres, save the data to a CSV file
    if movies:
        pd.DataFrame(movies).to_csv("movies_1.csv", index=False)
        print("Scraping complete and data saved to movies_1.csv")
    else:
        print("No data scraped")

    # Final progress update to 100% after completion
    progress_callback(100)

    # Close the web driver (browser)
    driver.quit()

    # Call the completion callback to show the user input fields for filtering
    completion_callback()


# --------------------------------------------------------------------------------------------------------------------------------
# Step 4 - Load and clean the movie data from the CSV file
# --------------------------------------------------------------------------------------------------------------------------------

def load_movie_data():
    try:
        # Load movie data from the CSV file into a pandas DataFrame
        data = pd.read_csv("movies_1.csv")
        # Remove rows with missing values in 'Title' or 'Rating'
        data.dropna(subset=["Title", "Rating"], inplace=True)
        return data
    except Exception as e:
        print("Error loading data:", e)  
        return None


# --------------------------------------------------------------------------------------------------------------------------------
# Step 5 - Function to filter movies based on genre and minimum rating
# --------------------------------------------------------------------------------------------------------------------------------

def filter_movies(data, genre=None, min_rank=None):
    # Start with the full data and apply filters based on user inputs
    filtered = data
    if genre and genre != 'all':
        filtered = filtered[filtered['Genre'] == genre]  # Filter by selected genre
    if min_rank:
        filtered = filtered[filtered['Rating'] >= min_rank]  # Filter by minimum rating

    return filtered


# --------------------------------------------------------------------------------------------------------------------------------
# Step 6 - Function to suggest a random movie and top 15 movies based on rating
# --------------------------------------------------------------------------------------------------------------------------------

def suggest_random_and_top_movies(data, genre=None, min_rank=None):
    # Apply the filters for genre and rating
    filtered = filter_movies(data, genre, min_rank)

    # If no movies match the filter, return a message
    if filtered.empty:
        return "No movies found for the given criteria."

    # Get a random movie suggestion from the filtered list
    random_movie = filtered.sample(1).iloc[0].to_dict()

    # Get the top 15 movies by highest rating
    filtered['Rating'] = pd.to_numeric(filtered['Rating'], errors='coerce')  
    top_15_movies = filtered.sort_values(by='Rating', ascending=False).head(15).to_dict(orient='records')

    return random_movie, top_15_movies


# --------------------------------------------------------------------------------------------------------------------------------
# Step 7 - GUI setup to interact with the user
# --------------------------------------------------------------------------------------------------------------------------------

def create_gui():
    def on_suggest():
        genre = genre_var.get()  # Get selected genre from dropdown
        min_rank = rank_var.get()  # Get the minimum rating from entry field

        try:
            min_rank = float(min_rank) if min_rank else None
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Rating")
            return

        # Get the movie suggestions based on the user's criteria
        suggestion = suggest_random_and_top_movies(movie_data, genre, min_rank)

        if isinstance(suggestion, str):
            # Show a message if no movies match the criteria
            messagebox.showinfo("Suggestion", suggestion)
        else:
            random_movie, top_15_movies = suggestion

            # Display the random movie suggestion
            random_result = f"Random Movie/TV Show:\nTitle: {random_movie['Title']}\nGenre: {random_movie['Genre']}\nYear: {random_movie['Release Year']}\n" \
                            f"Rating: {random_movie['Rating']}\n"
            messagebox.showinfo("Random Movie/TV Show Suggestion", random_result)

            # Display the top 15 movies sorted by rating
            top_15_result = "Top Movies/TV Shows:\n\n"
            for idx, movie in enumerate(top_15_movies, start=1):
                top_15_result += f"{idx}. {movie['Title']} ({movie['Release Year']})\nRating: {movie['Rating']}\n\n"
            messagebox.showinfo("Top Movies/TV Shows", top_15_result)

    def update_progress(progress):
        # Update the progress bar value and percentage label
        progress_var['value'] = progress
        progress_text_label.config(text=f"{progress}%")
        root.update_idletasks()  

    # Create the main window for the GUI
    root = tk.Tk()
    root.title("Movie/TV Show Suggestion App")  # Window title
    root.geometry("400x350")  # Set the window size

    # Title label for progress bar
    progress_label = tk.Label(root, text="Scraping in progress", font=("Helvetica", 12))
    progress_label.pack(pady=10)

    # Progress Bar widget
    progress_var = ttk.Progressbar(root, orient='horizontal', length=200, mode='determinate', maximum=100)
    progress_var.pack(pady=20)

    # Progress percentage label
    progress_text_label = tk.Label(root, text="0%", font=("Helvetica", 10))
    progress_text_label.pack()

    # Warning message to not close the window during scraping
    close_warning_label = tk.Label(root, text="Do not close this window", font=("Helvetica", 10, 'italic'))
    close_warning_label.pack(pady=10)

    # Hide the user input fields initially (to show after scraping completes)
    genre_label = tk.Label(root, text="Choose genre")
    genre_label.pack_forget()
    genre_var = tk.StringVar(value="all") 
    genre_dropdown = tk.OptionMenu(root, genre_var, *['all', 'action', 'comedy', 'drama', 'thriller'])
    genre_dropdown.pack_forget()

    # Input field for minimum rating
    rank_label = tk.Label(root, text='Minimum Rating (1 - 9)')
    rank_label.pack_forget()
    rank_var = tk.StringVar()
    rank_entry = tk.Entry(root, textvariable=rank_var)
    rank_entry.pack_forget()

    # Button to trigger movie suggestion
    suggest_button = tk.Button(root, text="Suggest Movie/TV Show", command=on_suggest)
    suggest_button.pack_forget()

    # Start scraping in background after a small delay
    root.after(100, scrape_imdb, update_progress, lambda: show_input_fields(root, genre_label, genre_dropdown, rank_label, rank_entry, suggest_button))

    def show_input_fields(root, genre_label, genre_dropdown, rank_label, rank_entry, suggest_button):
        # Once scraping is complete, show the input fields to the user
        progress_label.pack_forget()
        progress_var.pack_forget()
        progress_text_label.pack_forget()
        close_warning_label.pack_forget()

        genre_label.pack()
        genre_dropdown.pack()
        rank_label.pack()
        rank_entry.pack()
        suggest_button.pack()

    root.mainloop()


# --------------------------------------------------------------------------------------------------------------------------------
# Step 8 - Running the App
# --------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    movie_data = load_movie_data()  # Load movie data from CSV

    if movie_data is not None:
        create_gui()  # Open the GUI for movie suggestions
    else:
        print("Failed to load movie data.")  # Print an error message if data loading fails
