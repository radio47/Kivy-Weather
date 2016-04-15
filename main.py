import kivy
kivy.require('1.9.1') # replace with your current kivy version !
from kivy.network.urlrequest import UrlRequest
import json
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (ObjectProperty, ListProperty, StringProperty, NumericProperty)
from kivy.uix.listview import ListItemButton
from kivy.factory import Factory
from kivy.storage.jsonstore import JsonStore
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
API_KEY="4ed6a7fcea9d4f73e046fdac47242b16"

def locations_args_converter(index, data_item):
    city, country = data_item
    return {'location': (city, country)}


class LocationButton(ListItemButton):
    location = ListProperty()


class AddLocationForm(ModalView):
    search_input = ObjectProperty()
    search_results = ObjectProperty()

    def search_location(self):
        if self.search_input.text is not '':
            search_template = "http://api.openweathermap.org/data/2.5/find?q={}&type=like&APPID="+API_KEY
            search_url = search_template.format(self.search_input.text)
            request = UrlRequest(search_url, self.found_location)
        else:
            self.search_input.text = 'Split'

    def found_location(self, request, data):
        data = json.loads(data.decode()) if not isinstance(data, dict) else data
        cities = [(d['name'], d['sys']['country']) for d in data['list']]
        self.search_results.item_strings = cities
        del self.search_results.adapter.data[:]
        self.search_results.adapter.data.extend(cities)
        self.search_results._trigger_reset_populate()


class CurrentWeather(BoxLayout):
    location = ListProperty(['New York', 'US'])
    conditions = StringProperty()
    conditions_image = StringProperty()
    temp = NumericProperty()
    temp_min = NumericProperty()
    temp_max = NumericProperty()

    def update_weather(self):
        config = WeatherApp.get_running_app().config
        temp_type = config.getdefault("General", "temp_type", "metric").lower()
        weather_template = "http://api.openweathermap.org/data/2.5/weather?q={},{}&units={}&APPID="+API_KEY
        weather_url = weather_template.format(self.location[0], self.location[1], temp_type)
        request = UrlRequest(weather_url, self.weather_retrieved)

    def weather_retrieved(self, request, data):
        data = json.loads(data.decode()) if not isinstance(data, dict) else data
        self.conditions = data['weather'][0]['description']
        self.conditions_image = "http://openweathermap.org/img/w/{}.png".format(
            data['weather'][0]['icon'])
        self.temp = data['main']['temp']
        self.temp_min = data['main']['temp_min']
        self.temp_max = data['main']['temp_max']


class Forecast(BoxLayout):
    location = ListProperty(['New York', 'US'])
    forecast_container = ObjectProperty()

    def update_weather(self):
        config = WeatherApp.get_running_app().config
        temp_type = config.getdefault("General", "temp_type", "metric").lower()
        weather_template = "http://api.openweathermap.org/data/2.5/forecast/daily?q={},{}&units={}&cnt=3&APPID="+API_KEY
        weather_url = weather_template.format(self.location[0], self.location[1], temp_type)
        request = UrlRequest(weather_url, self.weather_retrieved)

    def weather_retrieved(self, request, data):
        data = json.loads(data.decode()) if not isinstance(data, dict) else data
        self.forecast_container.clear_widgets()
        for day in data['list']:
            label = Factory.ForecastLabel()
            label.date = datetime.datetime.fromtimestamp(day['dt']).strftime("%a %b %d")

            label.conditions = day['weather'][0]['description']
            label.conditions_image = "http://openweathermap.org/img/w/{}.png".format(
                day['weather'][0]['icon'])
            label.temp_min = day['temp']['min']
            label.temp_max = day['temp']['max']
            self.forecast_container.add_widget(label)


class WeatherRoot(BoxLayout):
    carousel = ObjectProperty()
    current_weather = ObjectProperty()
    forecast = ObjectProperty()
    locations = ObjectProperty()
    add_location_form = ObjectProperty()

    # BEGIN INIT
    def __init__(self, **kwargs):
        super(WeatherRoot, self).__init__(**kwargs)
        self.store = JsonStore("weather_store.json")
        if self.store.exists('locations'):
            locations = self.store.get('locations')
            self.locations.locations_list.adapter.data.extend(locations['locations'])
            current_location = locations["current_location"]
            self.show_current_weather(current_location)
        else:
            Clock.schedule_once(lambda dt: self.show_add_location_form())
    # END INIT

    # BEGIN SHOW_CURRENT_WEATHER
    def show_current_weather(self, location):
        if location not in self.locations.locations_list.adapter.data:
            self.locations.locations_list.adapter.data.append(location)
            self.locations.locations_list._trigger_reset_populate()
            self.store.put("locations",
                locations=list(self.locations.locations_list.adapter.data),
                current_location=location)

        self.current_weather.location = location
        self.forecast.location = location
        self.current_weather.update_weather()
        self.forecast.update_weather()

        self.carousel.load_slide(self.current_weather)
        if self.add_location_form is not None:
            self.add_location_form.dismiss()
        # END SHOW_CURRENT_WEATHER

    def show_add_location_form(self):
        self.add_location_form = AddLocationForm()
        self.add_location_form.open()


class WeatherApp(App):
    def build_config(self, config):
        config.setdefaults('General', {'temp_type': "Metric"})

    def build_settings(self, settings):
        settings.add_json_panel("Weather Settings", self.config, data="""
            [
                {"type": "options",
                    "title": "Temperature System",
                    "section": "General",
                    "key": "temp_type",
                    "options": ["Metric", "Imperial"]
                }
            ]"""
            )

    def on_config_change(self, config, section, key, value):
        if config is self.config and key == "temp_type":
            try:
                self.root.current_weather.update_weather()
                self.root.forecast.update_weather()
            except AttributeError:
                pass

if __name__ == '__main__':
	WeatherApp().run()
