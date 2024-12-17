from flask import Flask, jsonify, render_template, request, redirect, url_for
import requests, json, os, dash, plotly, datetime
import plotly.express as px
import pandas as pd
from sklearn.datasets import load_iris
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output



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

    def unix_time_to_normal(self, unix_time):
        normal_time = datetime.datetime.fromtimestamp(unix_time)
        hours = normal_time.strftime('%H')
        return int(hours)

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
    def forecast(self, lon, lat):
        future_weather = self.request(lon, lat)
        #время сейчас
        now_time = self.unix_time_to_normal(future_weather['now'])

        forecast_list = []
        #прогноз на завтра([1] за это отвечает), в тоже время что и сейчас
        for day in range(4):
            # исправляем ошибку связанную с тем что в прогнозе может не быть некоторых часов или дней
            hours_per_day = len(future_weather['forecasts'][day]['hours'])
            if now_time >= hours_per_day and hours_per_day != 0: now_time = hours_per_day-1

            if hours_per_day == 0:
                forecast_list.append({
                'temperature': 0,
                'humidity': 0,
                'wind_speed': 0,
                'precipitation_probability': 0,
                })
            else:
                forecast_list.append({
                    'temperature': future_weather['forecasts'][day]['hours'][now_time]['temp'],
                    'humidity': future_weather['forecasts'][day]['hours'][now_time]['humidity'],
                    'wind_speed': future_weather['forecasts'][day]['hours'][now_time]['wind_speed'],
                    'precipitation_probability': future_weather['forecasts'][day]['hours'][now_time]['prec_prob'],
                })
        return forecast_list


API_KEY = '41db2fd8-c751-405c-b3d6-8e47db9ee099'

# Пример использования
api = WeatherAPI(API_KEY)

#-----------------------------------------------------Test---------------------------------------------------------------------------
print(api.current_weather(37.588817, 55.76876))
print(api.forecast(37.588817, 55.76876))

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
points = []

@app.route('/weather/<float:lat>/<float:lon>', methods=['GET'])
def get_current_weather(lat, lon):
    curren_weather_data = api.current_weather(lon, lat)

    return render_template('current_weather.html', temperature=curren_weather_data['temperature'],
                           humidity=curren_weather_data['humidity'],
                           wind_speed=curren_weather_data['wind_speed'],
                           precipitation_probability=curren_weather_data['precipitation_probability'])

@app.route('/', methods=['GET', 'POST'])
def index():
    global points
    if request.method == 'POST':
        # Получаем координаты из формы
        latitudes = request.form.getlist('lat[]')
        longitudes = request.form.getlist('lon[]')

        # Преобразуем координаты в нужный формат (например, в список кортежей)
        points = list(zip(latitudes, longitudes))
        print("Полученные точки:", points)
        return redirect(url_for('result'))
    return render_template('index.html')

@app.route('/result')
def result():
    global weather_data_for_dash  # Указываем, что будем использовать глобальную переменную
    global points
    # try:
    weather_data_for_dash = []
    weather_data = {'day0': [],
                    'day1': [],
                    'day2': [],
                    'day3': [],}
    for point in points:
        forecast = api.forecast(point[0], point[1])
        weather_data['day0'].append(forecast[0])
        weather_data['day1'].append(forecast[1])
        weather_data['day2'].append(forecast[2])
        weather_data['day3'].append(forecast[3])
        #weather_data это сипсок с точками каждая точка список погоды для дней
        # Создание DataFrame для графика
    for day in ('day0', 'day1', 'day2', 'day3'):
        weather_data_for_dash.append(pd.DataFrame({
            'Location': [f'Point {i + 1}' for i in range(len(weather_data[day]))],
            'Temperature': [info['temperature'] for info in weather_data[day]],
            'Humidity': [info['humidity'] for info in weather_data[day]],
            'Wind Speed': [info['wind_speed'] for info in weather_data[day]],
            'Precipitation Probability': [info['precipitation_probability'] for info in weather_data[day]]
        }))
    return render_template('current_weather_multiple.html', weather_data=weather_data['day0'], api=api)
    # except:
    #     return 'Ошибка: Вы ввели некорректные данные'


# ------------------------------------------------------Dash app-------------------------------------------------------
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dash/')

# Определяем доступные метрики и дни
metrics = ['Temperature', 'Humidity', 'Wind Speed', 'Precipitation Probability']
days = ['Day 0', 'Day 1', 'Day 2', 'Day 3']

dash_app.layout = html.Div([
    dcc.Input(id='dummy-input', style={'display': 'none'}, value=''),

    # Checklist для выбора метрик
    dcc.Checklist(
        id='metric-checklist',
        options=[{'label': metric, 'value': metric} for metric in metrics],
        value=metrics,  # По умолчанию все метрики выбраны
        inline=True
    ),

    # Slider для выбора количества дней
    dcc.Slider(
        id='day-slider',
        min=1,
        max=len(days),
        value=len(days),  # По умолчанию показываем все дни
        marks={i: f'Day {i - 1}' for i in range(1, len(days) + 1)},
        step=1
    ),

    html.Div(id='graphs')
])


@dash_app.callback(
    Output('graphs', 'children'),
    Input('dummy-input', 'value'),
    Input('metric-checklist', 'value'),
    Input('day-slider', 'value')
)
def update_graphs(_, selected_metrics, num_days):
    graphs = []

    # Ограничиваем количество дней до выбранного значения
    for metric in selected_metrics:
        combined_data = pd.DataFrame()

        for day_index in range(num_days):  # Используем только выбранное количество дней
            df = weather_data_for_dash[day_index]
            df['Day'] = f'Day {day_index}'  # Добавляем столбец с днем
            combined_data = pd.concat([combined_data, df], ignore_index=True)

        # Создаем график для текущей характеристики
        fig = px.bar(combined_data, x='Location', y=metric, color='Day',
                     title=f'{metric} for Selected Days', barmode='group')
        graphs.append(dcc.Graph(figure=fig))

    return graphs


if __name__ == '__main__':
    app.run(debug=True)
