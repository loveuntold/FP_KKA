from flask import Flask, render_template, request, render_template_string
import osmnx as ox
import networkx as nx
import folium
import csv
import random
import math

app = Flask(__name__)

# Fungsi untuk membaca lokasi dari file CSV
def load_places_from_csv(filepath):
    places = {}
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['name']
            latitude = float(row['latitude'])
            longitude = float(row['longitude'])
            places[name] = (latitude, longitude)
    return places

# Fungsi untuk menghitung jarak Euclidean antara dua titik
def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# Fungsi Simulated Annealing untuk TSP
def simulated_annealing(places, selected_places, start_location, max_iter=10000, initial_temp=100, cooling_rate=0.995):
    locations = [start_location] + selected_places + [start_location]

    # Fungsi untuk menghitung total jarak rute
    def total_distance(route):
        dist = 0
        for i in range(len(route) - 1):
            dist += euclidean_distance(places[route[i]], places[route[i + 1]])
        return dist

    current_route = locations
    current_distance = total_distance(current_route)
    best_route = current_route
    best_distance = current_distance
    temperature = initial_temp

    for _ in range(max_iter):
        # Pilih dua titik acak untuk pertukaran
        new_route = current_route[:]
        i, j = sorted(random.sample(range(1, len(locations) - 1), 2))
        new_route[i:j+1] = reversed(new_route[i:j+1])

        new_distance = total_distance(new_route)

        # Terima solusi baru dengan probabilitas tertentu
        if new_distance < current_distance or random.random() < math.exp((current_distance - new_distance) / temperature):
            current_route = new_route
            current_distance = new_distance

        # Update solusi terbaik
        if new_distance < best_distance:
            best_route = new_route
            best_distance = new_distance

        # Cooling
        temperature *= cooling_rate

    return best_route

# Memuat tempat dari CSV
places = load_places_from_csv('locations.csv')

# Memastikan Bandara Juanda adalah titik awal dan akhir
pusat = "Gateway Pusat"
places_to_display = {key: places[key] for key in places if key != pusat}

@app.route('/')
def index():
    return render_template('fp.html', places=places_to_display)

@app.route('/get_route', methods=['POST'])
def get_route():
    # Mendapatkan jumlah titik yang dipilih pengguna
    num_places = int(request.form['num_places'])
    selected_places = [request.form[f'place_{i}'] for i in range(1, num_places + 1)]

    # Memastikan Bandara Juanda selalu menjadi titik awal dan akhir
    selected_places.insert(0, pusat)
    selected_places.append(pusat)

    # Menghitung rute optimal menggunakan Simulated Annealing
    optimal_route = simulated_annealing(places, selected_places[1:-1], pusat)

    # Menampilkan rute dalam format string
    route_str = " -> ".join(optimal_route)

    # Membuat peta rute
    route_coords = [places[place] for place in optimal_route]
    map_center = places[pusat]
    m = folium.Map(location=map_center, zoom_start=13)

    # Menambahkan marker untuk setiap lokasi
    for place, coord in places.items():
        folium.Marker(coord, popup=place).add_to(m)

    # Menambahkan polyline untuk rute
    folium.PolyLine(route_coords, color="blue", weight=2.5, opacity=1).add_to(m)

    # Konversi objek Folium map menjadi HTML string
    map_html = m._repr_html_()

    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Optimal Delivery Route</title>
        </head>
        <body>
            <h2>Optimal Route for Delivery</h2>
            <p>Optimal route: {{ route_str }}</p>
            {{ map_html|safe }}
        </body>
        </html>
    """, route_str=route_str, map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)
