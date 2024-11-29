from flask import Flask, render_template, request
import folium
import csv
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("fp.html")  # Serve the HTML form page

@app.route("/map")
def display_map():
    # Generate the Surabaya map
    surabaya_map = folium.Map(location=[-7.2575, 112.7521], zoom_start=13)

    # Define the path to the CSV file
    csv_file_path = os.path.join(os.getcwd(), 'locations.csv')

    # Check if the CSV file exists
    if os.path.exists(csv_file_path):
        # Open the CSV file and read locations
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # For each row, get the latitude, longitude, and name
                name = row['name']
                latitude = float(row['latitude'])
                longitude = float(row['longitude'])

                # Add a marker for each location in the CSV
                folium.Marker(
                    location=[latitude, longitude],
                    popup=name,
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(surabaya_map)

    else:
        print(f"CSV file '{csv_file_path}' not found.")

    # Return the map as HTML
    return surabaya_map._repr_html_()  # Serve the map directly as HTML

if __name__ == "__main__":
    app.run(debug=True)
