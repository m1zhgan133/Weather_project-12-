from flask import Flask, jsonify, render_template, request, redirect, url_for
import requests, json, os, dash, plotly
import plotly.express as px
import pandas as pd
from sklearn.datasets import load_iris
import dash_bootstrap_components as dbc
from dash import dcc, html



class WeatherAPI:
    api_url = 'https://api.weather.yandex.ru/v2/forecast' # ссылка на API

    def __init__(self, api_key):
        self.api_key = api_key


    # Отправляет запрос на API и возвращает ответ в формате JSON
    def request(self, lon, lat):
        headers = {
            'X-Yandex-Weather-Key': self.api_key
            }

        response = requests.get(f'https://api.weather.yandex.ru/v2/forecast?lat={lat}&lon={lon}', headers = headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Произошла ошибка: {response.status_code}, {response.text}")



    def check_bad_weather(self, data):
        if data['temperature'] < -10 or data['temperature'] > 30:  return 'Bad weather'
        if data['wind_speed'] > 15:                                return 'Bad weather'
        if data['precipitation_probability'] > 70:                 return 'Bad weather'
        if data['humidity'] < 5 or data['humidity'] > 95:          return 'Bad weather'
        return 'Good weather'

    def current_weather(self, lon, lat):
        # Получает текущую температуру по координатам
        weather_data = self.request(lon, lat)

        # Извлечение ключевых параметров
        temperature = weather_data['fact']['temp']  # Температура в градусах Цельсия
        humidity = weather_data['fact']['humidity']  # Влажность в процентах
        wind_speed = weather_data['fact']['wind_speed']  # Скорость ветра
        precipitation_probability = weather_data['fact'].get('precipitation_probability', 0)  # Вероятность дождя

        return {
        'temperature': temperature,
        'humidity': humidity,
        'wind_speed': wind_speed,
        'precipitation_probability': precipitation_probability
    }


    # Получает температуру через 24 часа
    def forecast_24h(self, lon, lat):
        #время сейчас
        now_time = int(self.request(lon, lat)['now_dt'].split(':')[0][-2:]) + 3

        #прогноз на завтра([1] за это отвечает), в тоже время что и сейчас
        return self.request(lon, lat)['forecasts'][1]['hours'][now_time]['temp']



API_KEY = '41db2fd8-c751-405c-b3d6-8e47db9ee099'

# Пример использования
api = WeatherAPI(API_KEY)

#-----------------------------------------------------Test---------------------------------------------------------------------------
print(api.current_weather(37.588817, 55.76876))
#print(api.forecast_24h(37.588817, 55.76876))

tests = [
{'temperature': 40,  #!!!! из-за этого плохая погода
     'humidity': 50,
     'wind_speed': 9,
     'precipitation_probability': 1},
{'temperature': 1,
    'humidity': 1,  #!!!! из-за этого плохая погода
    'wind_speed': 1,
    'precipitation_probability': 1},
{'temperature': 10,
    'humidity': 20,
    'wind_speed': 20, #!!!! из-за этого плохая погода
    'precipitation_probability': 30},
{'temperature': -5,
    'humidity': 40,
    'wind_speed': 5,
    'precipitation_probability': 80},  #!!!! из-за этого плохая погода
{'temperature': 10,# все хорошо
    'humidity': 20,
    'wind_speed': 5,
    'precipitation_probability': 30},
]

for test in tests:
    print(api.check_bad_weather(test))
#-----------------------------------------------------Flask---------------------------------------------------------------------------

app = Flask(__name__)
weather_data_for_dash = None

@app.route('/weather/<float:lat>/<float:lon>', methods=['GET'])
def get_current_weather(lat, lon):
    curren_weather_data = api.current_weather(lon, lat)

    return render_template('current_weather.html', temperature=curren_weather_data['temperature'],
                           humidity=curren_weather_data['humidity'],
                           wind_speed=curren_weather_data['wind_speed'],
                           precipitation_probability=curren_weather_data['precipitation_probability'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        lat1 = request.form['lat1']
        lon1 = request.form['lon1']
        lat2 = request.form['lat2']
        lon2 = request.form['lon2']
        return redirect(url_for('result', lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2))
    return render_template('index.html')

@app.route('/result')
def result():
    global weather_data_for_dash  # Указываем, что будем использовать глобальную переменную
    try:
        point1_inform = api.current_weather(request.args.get('lon1'), request.args.get('lat1'))
        point2_inform = api.current_weather(request.args.get('lon2'), request.args.get('lat2'))

        # Создание DataFrame для графика
        weather_data_for_dash = pd.DataFrame({
            'Location': ['Point 1', 'Point 2'],
            'Temperature': [point1_inform['temperature'], point2_inform['temperature']],
            'Humidity': [point1_inform['humidity'], point2_inform['humidity']],
            'Wind Speed': [point1_inform['wind_speed'], point2_inform['wind_speed']],
            'Precipitation Probability': [point1_inform['precipitation_probability'], point2_inform['precipitation_probability']]
        })

        return render_template('current_weather_2_points.html',
                               good_weather1=api.check_bad_weather(point1_inform),
                               temperature1=point1_inform['temperature'],
                               humidity1=point1_inform['humidity'],
                               wind_speed1=point1_inform['wind_speed'],
                               precipitation_probability1=point1_inform['precipitation_probability'],

                               good_weather2=api.check_bad_weather(point2_inform),
                               temperature2=point2_inform['temperature'],
                               humidity2=point2_inform['humidity'],
                               wind_speed2=point2_inform['wind_speed'],
                               precipitation_probability2=point2_inform['precipitation_probability']
                               )
    except:
        return 'Ошибка: Вы ввели некорректные данные'

# Dash app
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dash/')

@dash_app.callback(
    dash.dependencies.Output('weather-graph', 'figure'),
    [dash.dependencies.Input('location-dropdown', 'value')]
)
def update_graph(selected_location):
    # Получаем данные из глобальной переменной
    df = weather_data_for_dash

    # Создание графика
    fig = px.bar(df, x='Location', y=['Temperature', 'Humidity', 'Wind Speed', 'Precipitation Probability'],
                 title='Weather Data for Two Points', barmode='group')
    return fig

dash_app.layout = html.Div([
    dcc.Dropdown(
        id='location-dropdown',
        options=[
            {'label': 'Point 1', 'value': 'Point 1'},  # Используем метки для выбора
            {'label': 'Point 2', 'value': 'Point 2'},
        ],
        value='Point 1'  # Устанавливаем значение по умолчанию
    ),
    dcc.Graph(id='weather-graph')
])




if __name__ == '__main__':
    app.run(debug=True)
