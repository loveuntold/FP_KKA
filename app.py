from flask import Flask, render_template, request, render_template_string
import requests
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
            # Validasi jika lokasi dalam batas Surabaya
            if -7.4672 <= latitude <= -7.1297 and 112.6107 <= longitude <= 112.8296:
                places[name] = (latitude, longitude)
    return places

# Fungsi untuk mendapatkan rute dan jarak menggunakan OSRM
def get_osrm_route(start_coords, end_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson"
    response = requests.get(url)
    if response.status_code == 200:
        route_data = response.json()
        if route_data.get('routes'):
            # Mendapatkan jarak dan koordinat rute
            distance_meters = route_data['routes'][0]['distance']
            route_coords = route_data['routes'][0]['geometry']['coordinates']
            return route_coords, distance_meters
        else:
            return None, None
    else:
        return None, None

# Memuat lokasi dari file CSV
places = load_places_from_csv('locations.csv')

# Memastikan titik awal dan akhir adalah Gateway Pusat
pusat = "Gateway Pusat"
places_to_display = {key: places[key] for key in places if key != pusat}

@app.route('/')
def index():
    filtered_places = {key: value for key, value in sorted(places.items()) if -7.4672 <= value[0] <= -7.1297 and 112.6107 <= value[1] <= 112.8296}
    return render_template('fp.html', places=filtered_places)

# Menghitung rute optimal menggunakan Simulated Annealing
@app.route('/get_route', methods=['POST'])
def get_route():
    num_places = int(request.form['num_places'])
    selected_places = [request.form[f'place_{i}'] for i in range(1, num_places + 1)]

    # Validasi lokasi agar tetap dalam batas koordinat Surabaya
    for place in selected_places:
        lat, lon = places[place]
        if not (-7.4672 <= lat <= -7.1297 and 112.6107 <= lon <= 112.8296):
            return f"Error: Location {place} is outside Surabaya boundaries."

    # Menambahkan titik awal dan akhir
    selected_places.insert(0, pusat)
    selected_places.append(pusat)
    
    # Mendapatkan koordinat untuk setiap lokasi
    selected_coords = [places[place] for place in selected_places]

    # Cache jarak antar lokasi untuk mengurangi permintaan ke OSRM
    distance_cache = {}

    def get_cached_distance(place1, place2):
        if (place1, place2) in distance_cache:
            return distance_cache[(place1, place2)]
        elif (place2, place1) in distance_cache:
            return distance_cache[(place2, place1)]
        else:
            _, dist = get_osrm_route(places[place1], places[place2])
            distance_cache[(place1, place2)] = dist
            return dist

    def total_distance(route):
        dist = 0
        for i in range(len(route) - 1):
            segment_distance = get_cached_distance(route[i], route[i + 1])
            if segment_distance is None:
                return float('inf') 
            dist += segment_distance
        return dist

    # Inisialisasi rute awal dan jarak terbaik
    current_route = selected_places
    best_route = current_route[:]
    best_distance = total_distance(best_route)

    # Iterasi Simulated Annealing
    for _ in range(1000):  # Jumlah iterasi
        # Membalik sebagian rute untuk mencoba kombinasi baru
        new_route = current_route[:]
        i, j = sorted(random.sample(range(1, len(current_route) - 1), 2))
        new_route[i:j+1] = reversed(new_route[i:j+1])

        new_distance = total_distance(new_route)
        if new_distance < best_distance:  # Jika rute baru lebih baik, simpan sebagai solusi terbaik
            best_route = new_route[:]
            best_distance = new_distance

    # Membuat peta rute optimal
    optimal_coords = [places[place] for place in best_route]
    route_geometry = []
    for i in range(len(optimal_coords) - 1):
        segment_coords, _ = get_osrm_route(optimal_coords[i], optimal_coords[i + 1])
        if segment_coords:
            route_geometry.extend(segment_coords)

    # Membuat peta interaktif menggunakan Folium
    m = folium.Map(location=places[pusat], zoom_start=13)

    for place in best_route:
        folium.Marker(
            places[place],
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color: yellow; 
                    padding: 0px 3px; 
                    display: inline;         
                    font-size: 8pt; 
                    font-weight: bold; 
                    color: black; 
                    border-radius: 3px;">{place}</div>
            """),
            popup=place,
        ).add_to(m)
        folium.Marker(places[place], popup=place).add_to(m)


    folium.PolyLine([(lat, lon) for lon, lat in route_geometry], color="blue", weight=2.5, opacity=1).add_to(m)

    # Konversi objek peta ke HTML
    map_html = m._repr_html_()

    # Render halaman hasil
    return render_template(
        "optimal_route.html",
        best_route=best_route,
        best_distance=round(best_distance, 2),
        map_html=map_html
    )

if __name__ == '__main__':
    app.run(debug=True)
