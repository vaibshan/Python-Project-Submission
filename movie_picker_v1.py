import threading
from tkinter import *
from tkinter import messagebox, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random

# --------------------------------------------------------------------------------------------------------------------------------
# Step 1 - Setup ChromeDriver
# --------------------------------------------------------------------------------------------------------------------------------

options = webdriver.ChromeOptions()
options.add_argument("--window-position=-2400,-2400")  # Move the browser window off-screen
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --------------------------------------------------------------------------------------------------------------------------------
# Step 2 - Global Variables to track the progress of scraping and UI updates
# --------------------------------------------------------------------------------------------------------------------------------

progress_var = None
progress_text_label = None  # Label to display the progress percentage
close_warning_label = None  # Label to show a warning not to close the window

# --------------------------------------------------------------------------------------------------------------------------------
# Step 3 - Function to scrape IMDB data with a progress bar callback
# --------------------------------------------------------------------------------------------------------------------------------

def scrape_imdb(progress_callback, completion_callback):
    url = "https://www.imdb.com/search/title/?genres={genre}"  
    genres = ['action', 'comedy', 'drama', 'thriller']  
    movies = []  

    total_steps = len(genres) * 5  # For simplicity, assume 5 steps per genre (to load more movies)

    # Loop through each genre to scrape movie data
    for i, genre in enumerate(genres):
        try:
            driver.get(url.format(genre=genre))
            time.sleep(5)  # Wait for the page to load completely
        except Exception as e:
            print(f"Error loading page for genre {genre}: {e}")
            continue 

        progress_callback(int(((i + 1) / len(genres)) * 100))  # Update progress

        # Click the '50 more' button 5 times to load more movies
        # Change the range if you want to scrape more or less movies per genre
        for _ in range(5): 
            try:
                load_more_button = driver.find_element(By.XPATH, "//button[contains(., '50 more')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(3)
            except:
                break  # Exit if there are no more movies to load

        movie_containers = driver.find_elements(By.CLASS_NAME, 'ipc-metadata-list-summary-item')
        time.sleep(2)  # Wait for the page to refresh

        # Extract movie data
        for container in movie_containers:
            title = container.find_element(By.CLASS_NAME, 'ipc-title__text').text
            try:
                release_year = container.find_element(By.CLASS_NAME, 'sc-6ade9358-7').text
            except:
                release_year = None
            try:
                rating = container.find_element(By.CLASS_NAME, 'ipc-rating-star--rating').text
            except:
                rating = None

            movies.append({
                "Title": title,
                "Genre": genre,
                "Release Year": release_year,
                "Rating": rating
            })

        progress_callback(int(((i + 1) / len(genres)) * 100))  # Update progress after each genre

    # Save the movie data to a CSV file
    if movies:
        pd.DataFrame(movies).to_csv("movies_1.csv", index=False)
        print("Scraping complete and data saved to movies_1.csv")
    else:
        print("No data scraped")

    driver.quit()  # Close the browser
    progress_callback(100)  # Final progress update
    completion_callback()  # Call the completion callback to display the input fields

# --------------------------------------------------------------------------------------------------------------------------------
# Step 4 - Function to update progress on the GUI
# --------------------------------------------------------------------------------------------------------------------------------

def update_progress(progress):
    # This function is called from the background thread to update the progress bar in the GUI
    progress_var['value'] = progress
    progress_text_label.config(text=f"{progress}%")
    root.update_idletasks()  # Ensure the GUI updates

# --------------------------------------------------------------------------------------------------------------------------------
# Step 5 - Function to display input fields after scraping is done
# --------------------------------------------------------------------------------------------------------------------------------

def show_input_fields():
    # Hide the progress bar, the progress text, and the warning label, then show the genre/rating selection fields
    progress_label.pack_forget()
    progress_var.pack_forget()
    progress_text_label.pack_forget()

    # Hide the warning label only if it was created
    if close_warning_label:
        close_warning_label.pack_forget()

    genre_label.pack()
    genre_dropdown.pack()
    rank_label.pack()
    rank_entry.pack()
    suggest_button.pack()

# --------------------------------------------------------------------------------------------------------------------------------
# Step 6 - Function to handle movie suggestions based on user input
# --------------------------------------------------------------------------------------------------------------------------------

def on_suggest():
    genre = genre_var.get()
    min_rank = rank_var.get()
    
    # Handle invalid input
    try:
        min_rank = float(min_rank) if min_rank else None
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter valid numbers for Rating")
        return

    movie_data = pd.read_csv("movies_1.csv")  # Load the movie data

    filtered = movie_data
    if genre != "all":
        filtered = filtered[filtered["Genre"] == genre]
    if min_rank:
        filtered = filtered[filtered["Rating"] >= min_rank]

    if filtered.empty:
        messagebox.showinfo("No Movies", "No movies found for the given criteria.")
    else:
        # Random suggestion from the filtered data
        random_movie = filtered.sample(1).iloc[0]  # Get a random movie
        random_result = f"Random Movie/TV Show:\n" \
                        f"Title: {random_movie['Title']}\n" \
                        f"Genre: {random_movie['Genre']}\n" \
                        f"Year: {random_movie['Release Year']}\n" \
                        f"Rating: {random_movie['Rating']}\n"
        messagebox.showinfo("Random Movie/TV Show Suggestion", random_result)

        # List of top 15 movies by rating
        top_15_movies = filtered.sort_values(by="Rating", ascending=False).head(15)
        top_15_result = "Top Movies/TV Shows:\n\n"
        for idx, movie in enumerate(top_15_movies.itertuples(), start=1):
            top_15_result += f"{idx}. {movie.Title} ({movie._3})\nRating: {movie.Rating}\n\n"
        
        messagebox.showinfo("Top Movies/TV Shows", top_15_result)

# --------------------------------------------------------------------------------------------------------------------------------
# Step 7 - Create the GUI for scraping
# --------------------------------------------------------------------------------------------------------------------------------

def create_gui():
    global root, progress_var, progress_text_label, genre_var, rank_var, progress_label, genre_label, genre_dropdown, rank_label, rank_entry, suggest_button, close_warning_label
    root = Tk()
    root.title("Movie Scraper")

    # Set the window size
    root.geometry("600x400")  # Set the window size (width x height)

    # Progress bar UI
    progress_label = Label(root, text="Scraping in progress", font=("Helvetica", 14))
    progress_label.pack(pady=10)

    progress_var = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", maximum=100)
    progress_var.pack(pady=20)

    progress_text_label = Label(root, text="0%", font=("Helvetica", 12))
    progress_text_label.pack()

    # User warning label
    close_warning_label = Label(root, text="Do not close this window", font=("Helvetica", 12, 'italic'))
    close_warning_label.pack(pady=10)

    # Genre and rating selection fields
    genre_label = Label(root, text="Choose genre", font=("Helvetica", 12))
    genre_label.pack_forget()
    genre_var = StringVar(value="all")  # Default to 'all' genres
    genre_dropdown = OptionMenu(root, genre_var, 'all', 'action', 'comedy', 'drama', 'thriller')
    genre_dropdown.config(font=("Helvetica", 12))
    genre_dropdown.pack_forget()

    rank_label = Label(root, text="Minimum Rating (1-9)", font=("Helvetica", 12))
    rank_label.pack_forget()
    rank_var = StringVar()
    rank_entry = Entry(root, textvariable=rank_var, font=("Helvetica", 12))
    rank_entry.pack_forget()

    suggest_button = Button(root, text="Suggest Movie/TV Show", command=on_suggest, font=("Helvetica", 12))
    suggest_button.pack_forget()

    # Start scraping in a background thread
    threading.Thread(target=lambda: scrape_imdb(update_progress, show_input_fields), daemon=True).start()

    root.mainloop()

# --------------------------------------------------------------------------------------------------------------------------------
# Step 8 - Running the App
# --------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    create_gui()  # Initialize the GUI and start the app
