"""
Este modulo contiene funciones para facilitar el trabajo con la api de bing maps

@author: Juan Pablo Ortiz Rubio
@version: 1.0.1

"""

try:
    import urllib.parse
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    import json
except ImportError:
    import simplejson as json

import json
from abc import ABCMeta, abstractmethod
from pathlib import Path

from geopy.distance import geodesic
from geopy.geocoders import Bing, Nominatim
from googletrans import Translator
from IPython.display import Image


def _tuple_LatLng_to_string(latlng):
    """ Se verifica que el parámetro latlng sea una tupla de dos elementos
        y que sean valores válidos. Si no es así, se lanza una excepción.
        Si es correcto, se devuelve una cadena con el formato 'lat, lng'.

    Args:
        latlng (lat, lang): Tupla con dos elementos, que corresponden a la
            latitud y longitud.

    Raises:
        ValueError: Si la latitud o longitud no son válidas.

    Returns:
        String: Cadena con el formato 'lat, lng'
    """
    lat = latlng[0]
    lng = latlng[1]

    if lat > 90 or lat < -90:
        raise ValueError('Latitud inválida')
    elif lng > 180 or lng < -180:
        raise ValueError('Longitud inválida')
    else:
        return str(lat) + ',' + str(lng)

def _json_from_url(url):
    """ Se obtiene una cadena JSON a partir de la respuesta de una URL.

    Args:
        url (String): URL de la que se obtendrá la respuesta.

    Returns:
        JSON: Cadena JSON obtenida de la respuesta de la URL.
    """
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request)

    r = response.read().decode(encoding="utf-8")
    return json.loads(r)

def _posicion_a_string_url(ubicacion):
    """ Convierte cualquer tipo de ubicación a una string.

    Args:
        posicion ((lat, lang) o String): Ubicación a convertir. 

    Returns:
        String: Ubicación en formato String
    """
    # Si la posición es una tupla, es una latitud y longitud
    if type(ubicacion) is tuple or type(ubicacion) is list:
        return _tuple_LatLng_to_string(ubicacion)
    # Si la posición es una cadena, es una dirección
    if type(ubicacion) is str:
        encodedDest = ubicacion  # urllib.parse.quote(posicion, safe='')
        return encodedDest

class MapService(metaclass=ABCMeta):
    @abstractmethod
    def _rest_localizacion(self, ubicacion, **kwargs):
        pass

    @abstractmethod
    def _rest_ruta(self, inicio, final, via=[], **kwargs):
        pass

    @abstractmethod
    def _rest_localizacion_imagen(self, ubicacion, width=500, height=500, zoomLevel=16,  **kwargs):
        pass

    @abstractmethod
    def _rest_ruta_imagen(self, inicio, final, via=[], width=500, height=500, **kwargs):
        pass


class OpenService(MapService):
    ################################################################################
    ################################ CONSTRUCTOR ###################################
    ################################################################################

    def __init__(self, api_open_key, api_bingmaps_key=None, version=1):
        """Instanciar un objeto OpenService con la clave de la API de OpenStreet.
        Si es necesario sacar algun servicio de ruta o imagen ingresar el api_bingmaps_key
        Lugares para obtener api:
        Recomendado : https://developer.mapquest.com/
        https://www.openstreetmap.org/

        Args:
            api_key (String): Clave de la API de OpenStreet.
        """
        # Inicialización de los datos y objetos
        # configure api
        self.geolocator = Nominatim(user_agent=api_open_key)
        self._api_key = api_bingmaps_key
        self._version = version

        # Inicialización de las constantes
        URL_BASE = 'http://dev.virtualearth.net/REST/v' + str(version) + '/'
        self._url_rutas = URL_BASE + 'Routes/Driving'
        self._url_rutas_imagen = URL_BASE + 'Imagery/Map/Road/Routes/Driving'
        self._url_localizacion = URL_BASE + 'Locations'
        self._url_localizacion_imagen = URL_BASE + 'Imagery/Map/Road'

    ################################################################################
    ############################### SERVICIOS REST #################################
    ################################################################################
    def _rest_localizacion(self, ubicacion, **kwargs):
        """ Búsqueda de localización de OpenStreet.

        Args:
            ubicacion ((lat, lang) o String): Latitud y longitud o Dirección de la ubicación dada.
            **kwargs: Los posibles kwargs.

        Returns:
            JSON: JSON con la respuesta del servicio REST de Localización de OpenStreet.
        """

        # Si se ingresa una longitud y latitud.
        if type(ubicacion) is tuple or type(ubicacion) is list:
            res = self.geolocator.reverse(ubicacion)

        elif type(ubicacion) is str:
            res = self.geolocator.geocode(ubicacion)

        if res is None:
            # Si no hay respuesta intentar con los servicios de BingMaps

            # Se agrega la clave de la API Bing Maps
            kwargs.update({'key': self._api_key})

            url = self._url_localizacion

            # Si se ingresa una longitud y latitud.
            if type(ubicacion) is tuple or type(ubicacion) is list:
                # Ejemplo de llamada:
                # http://dev.virtualearth.net/REST/v1/Locations?query=Bogot%C3%A1%2C+Colombia%2C+Carrear+111c+%2381-30&key=AiHmbkSxeJrOk9uYeGh6Rue2DCZeAe3Ozk2zwmct5b-GvXxvqpbP-UqAWqqQb47J

                url += '?'

                # Se agregan en los parámetros el query de la búsqueda
                kwargs.update({'query': ubicacion})

            elif type(ubicacion) is str:
                # Ejemplo de llamada:
                # https://dev.virtualearth.net/REST/v1/Locations/4.695128,-74.086825?&key=AiHmbkSxeJrOk9uYeGh6Rue2DCZeAe3Ozk2zwmct5b-GvXxvqpbP-UqAWqqQb47J

                # Se agrega el valor obligatorio a enviar
                url += '/' + urllib.parse.quote(ubicacion) + '?'

            # Se agrega a la consulta todos los parámetros kwargs
            url += urlencode(kwargs)

            # Se hace la consulta al servicio REST
            data = _json_from_url(url)

            # Se devuelve el resultado de la consulta en formato JSON (MAP)
            return data['resourceSets'][0]['resources'][0]
            
        else:
            proc = '{"point": {"coordinates": [' + str(res.latitude) + ', ' + str(
                res.longitude) + ']}, "address": {"formattedAddress": "' + res.address + '"} }'

            return json.loads(proc)

    def _rest_ruta(self, inicio, final, via=[], **kwargs):
        """ Búsqueda de rutas de Bing Maps.
            Diccionario de parámetros requeridos: {'wayPoint.1': 'inicio', 'wayPoint.2': 'final'}
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            inicio ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación inicial.
            final ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación final.
            via (list<('lat, lng')> o list<String>, optional): Lista de tuplas con las latitudes y longitudes 
                o Direcciones de las ubicaciones intermedias. Defaults to [].
            **kwargs: Los posibles kwargs incluyen: 'wayPoint.2+n', 'heading', 'optimize', 'avoid', 
                'distanceBeforeFirstTurn', 'heading', 'optimize', 'routeAttributes', 
                'routePathOutput', 'maxSolutions', 'tolerances', 'distanceUnit', 'dateTime', 
                'timeType', 'mfaxSolutions', 'travelMode'.
        Returns:
            JSON: JSON con la respuesta del servicio REST de Rutas de Bing Maps.
        """
        # Se guardan en una lista las direcciones de inicio y fin y las paradas intermedias en la consulta
        paradas = []
        paradas.append(_posicion_a_string_url(inicio))
        if len(via) > 0:
            paradas = paradas + \
                [_posicion_a_string_url(latlng) for latlng in via]
        paradas.append(_posicion_a_string_url(final))

        # Se guarda el número de paradas totales (contando inicio y fin)
        numero_paradas = len(paradas)

        # Se transforma las direcciones y paradas en datos validos para la consulta al servicio REST
        viajes = {}
        for n, wp in zip(range(1, numero_paradas + 1), paradas):
            if n == 1 or n == numero_paradas:
                viajes['wayPoint.' + str(n)] = wp
            else:
                viajes['viaWayPoint.' + str(n)] = wp

        # Se agrega a los parámetros kwargs las ubicaciones
        kwargs.update(viajes)

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se crea y se agregan a la consulta todos los parámetros extra
        url = self._url_rutas + '?'
        url += urlencode(kwargs)

        # Se hace la consulta al servicio REST
        data = _json_from_url(url)

        # Se devuelve el resultado de la consulta en formato JSON (MAP)
        return data['resourceSets'][0]['resources'][0]

    def _rest_localizacion_imagen(self, ubicacion, width=500, height=500, zoomLevel=16,  **kwargs):
        """ Obtener una imagen de la ubicación de una dirección.
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/imagery/get-a-static-map?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            ubicacion ((lat, lang) o String): Latitud y longitud o Dirección de la ubicación dada.
            width (int, optional): Ancho de la imagen. Defaults to 500.
            height (int, optional): Alto de la imagen. Defaults to 500.
            zoomLevel (int, optional): Nivel de zoom. Defaults to 16.
            **kwargs: Los posibles kwargs están descritos en el link de arriba.

        Returns:
            Image: Imagen de la ubicación.
        """

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se agregan los parámetros a la consulta REST
        kwargs.update({'zoomLevel': zoomLevel})
        kwargs.update({'dpi': "Large"})
        kwargs.update({'mapSize': str(width) + ',' + str(height)})

        url = self._url_localizacion_imagen

        # Si se ingresa una longitud y latitud.
        if type(ubicacion) is tuple or type(ubicacion) is list:
            # Se agrega el valor obligatorio a enviar
            url += '/' + _tuple_LatLng_to_string(ubicacion) + '?'

            # Para poder agregar un pin en la ubicación
            kwargs.update(
                {'pushpin': _tuple_LatLng_to_string(ubicacion) + ';66'})

        elif type(ubicacion) is str:
            # Se agrega el valor obligatorio a enviar
            url += '/' + ubicacion + '?'

        # Se agrega a la consulta todos los parámetros kwargs
        url += urlencode(kwargs)

        # Se organiza el directorio para guardar la imagen de la ubicación
        path = Path("images")
        path.mkdir(parents=True, exist_ok=True)
        filename = 'images/localizacion(' + \
            _posicion_a_string_url(ubicacion) + ').png'

        # Se hace la consulta al servicio REST y se guarda la imagen
        urllib.request.urlretrieve(url, filename)
        return Image(filename=filename)

    def _rest_ruta_imagen(self, inicio, final, via=[], width=500, height=500, **kwargs):
        """ Búsqueda de rutas de Bing Maps.
            Diccionario de parámetros requeridos: {'wayPoint.1': 'inicio', 'wayPoint.2': 'final'}
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            inicio ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación inicial.
            final ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación final.
            via (list<('lat, lng')> o list<String>, optional): Lista de tuplas con las latitudes y longitudes 
                o Direcciones de las ubicaciones intermedias. Defaults to [].
            width (int, optional): Ancho de la imagen. Defaults to 500.
            height (int, optional): Alto de la imagen. Defaults to 500.
            **kwargs: Los posibles kwargs incluyen: 'wayPoint.2+n', 'heading', 'optimize', 'avoid', 
                'distanceBeforeFirstTurn', 'heading', 'optimize', 'routeAttributes', 
                'routePathOutput', 'maxSolutions', 'tolerances', 'distanceUnit', 'dateTime', 
                'timeType', 'mfaxSolutions', 'travelMode'.
        Returns:
            JSON: JSON con la respuesta del servicio REST de Rutas de Bing Maps.
        """
        # Se guardan en una lista las direcciones de inicio y fin y las paradas intermedias en la consulta
        paradas = []
        paradas.append(_posicion_a_string_url(inicio))
        if len(via) > 0:
            paradas = paradas + \
                [_posicion_a_string_url(latlng) for latlng in via]
        paradas.append(_posicion_a_string_url(final))

        # Se guarda el número de paradas totales (contando inicio y fin)
        numero_paradas = len(paradas)

        # Se transforma las direcciones y paradas en datos validos para la consulta al servicio REST
        viajes = {}
        for n, wp in zip(range(1, numero_paradas + 1), paradas):
            if n == 1 or n == numero_paradas:
                viajes['wayPoint.' + str(n)] = wp
            else:
                viajes['viaWayPoint.' + str(n)] = wp

        # Se agrega a los parámetros kwargs las ubicaciones
        kwargs.update(viajes)

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se agregan los parámetros de la imagen
        kwargs.update({'mapSize': str(width) + ',' + str(height)})
        kwargs.update({'dpi': "Large"})

        # Se crea y se agregan a la consulta todos los parámetros extra
        url = self._url_rutas_imagen + '?'
        url += urlencode(kwargs)

        # Se organiza el directorio para guardar la imagen de la ubicación
        path = Path("images")
        path.mkdir(parents=True, exist_ok=True)
        filename = 'images/Ruta(' + _posicion_a_string_url(inicio) + \
            ')(' + _posicion_a_string_url(final) + ').png'

        # Se hace la consulta al servicio REST y se guarda la imagen
        urllib.request.urlretrieve(url, filename)
        return Image(filename=filename)


class BingService(MapService):

    ################################################################################
    ################################ CONSTRUCTOR ###################################
    ################################################################################

    def __init__(self, api_bingmaps_key, version=1):
        """Instanciar un objeto BingService con la clave de la API de Bing Maps.
            Es recomendado que se utilice el OpenService para mejora de precisión.
        Args:
            api_key (String): Clave de la API de Bing Maps.
            version (int, optional): Versión. Defaults to 1.
        """

        # Inicialización de los datos y objetos
        self._api_key = api_bingmaps_key
        self._version = version

        # Inicialización de las constantes
        URL_BASE = 'http://dev.virtualearth.net/REST/v' + str(version) + '/'
        self._url_rutas = URL_BASE + 'Routes/Driving'
        self._url_rutas_imagen = URL_BASE + 'Imagery/Map/Road/Routes/Driving'
        self._url_localizacion = URL_BASE + 'Locations'
        self._url_localizacion_imagen = URL_BASE + 'Imagery/Map/Road'

    ################################################################################
    ############################### SERVICIOS REST #################################
    ################################################################################

    def _rest_localizacion(self, ubicacion, **kwargs):
        """ Búsqueda de localización de Bing Maps.
            Diccionario de parámetros requeridos: {'query': 'search'} o {'point': 'lat,lng'}
            Consulte 
            https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/find-a-location-by-point
            https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/find-a-location-by-query
            para más información de las descripciones.

        Args:
            ubicacion ((lat, lang) o String): Latitud y longitud o Dirección de la ubicación dada.
            **kwargs: Los posibles kwargs están descritos en el link de arriba.

        Returns:
            JSON: JSON con la respuesta del servicio REST de Localización de Bing Maps.
        """
        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        url = self._url_localizacion

        # Si se ingresa una longitud y latitud.
        if type(ubicacion) is tuple or type(ubicacion) is list:
            # Ejemplo de llamada:
            # http://dev.virtualearth.net/REST/v1/Locations?query=Bogot%C3%A1%2C+Colombia%2C+Carrear+111c+%2381-30&key=AiHmbkSxeJrOk9uYeGh6Rue2DCZeAe3Ozk2zwmct5b-GvXxvqpbP-UqAWqqQb47J

            url += '?'

            # Se agregan en los parámetros el query de la búsqueda
            kwargs.update({'query': ubicacion})

        elif type(ubicacion) is str:
            # Ejemplo de llamada:
            # https://dev.virtualearth.net/REST/v1/Locations/4.695128,-74.086825?&key=AiHmbkSxeJrOk9uYeGh6Rue2DCZeAe3Ozk2zwmct5b-GvXxvqpbP-UqAWqqQb47J

            # Se agrega el valor obligatorio a enviar
            url += '/' + urllib.parse.quote(ubicacion) + '?'

        # Se agrega a la consulta todos los parámetros kwargs
        url += urlencode(kwargs)

        # Se hace la consulta al servicio REST
        data = _json_from_url(url)

        # Se devuelve el resultado de la consulta en formato JSON (MAP)
        return data['resourceSets'][0]['resources'][0]

    def _rest_ruta(self, inicio, final, via=[], **kwargs):
        """ Búsqueda de rutas de Bing Maps.
            Diccionario de parámetros requeridos: {'wayPoint.1': 'inicio', 'wayPoint.2': 'final'}
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            inicio ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación inicial.
            final ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación final.
            via (list<('lat, lng')> o list<String>, optional): Lista de tuplas con las latitudes y longitudes 
                o Direcciones de las ubicaciones intermedias. Defaults to [].
            **kwargs: Los posibles kwargs incluyen: 'wayPoint.2+n', 'heading', 'optimize', 'avoid', 
                'distanceBeforeFirstTurn', 'heading', 'optimize', 'routeAttributes', 
                'routePathOutput', 'maxSolutions', 'tolerances', 'distanceUnit', 'dateTime', 
                'timeType', 'mfaxSolutions', 'travelMode'.
        Returns:
            JSON: JSON con la respuesta del servicio REST de Rutas de Bing Maps.
        """
        # Se guardan en una lista las direcciones de inicio y fin y las paradas intermedias en la consulta
        paradas = []
        paradas.append(_posicion_a_string_url(inicio))
        if len(via) > 0:
            paradas = paradas + \
                [_posicion_a_string_url(latlng) for latlng in via]
        paradas.append(_posicion_a_string_url(final))

        # Se guarda el número de paradas totales (contando inicio y fin)
        numero_paradas = len(paradas)

        # Se transforma las direcciones y paradas en datos validos para la consulta al servicio REST
        viajes = {}
        for n, wp in zip(range(1, numero_paradas + 1), paradas):
            if n == 1 or n == numero_paradas:
                viajes['wayPoint.' + str(n)] = wp
            else:
                viajes['viaWayPoint.' + str(n)] = wp

        # Se agrega a los parámetros kwargs las ubicaciones
        kwargs.update(viajes)

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se crea y se agregan a la consulta todos los parámetros extra
        url = self._url_rutas + '?'
        url += urlencode(kwargs)

        # Se hace la consulta al servicio REST
        data = _json_from_url(url)

        # Se devuelve el resultado de la consulta en formato JSON (MAP)
        return data['resourceSets'][0]['resources'][0]

    def _rest_localizacion_imagen(self, ubicacion, width=500, height=500, zoomLevel=16,  **kwargs):
        """ Obtener una imagen de la ubicación de una dirección.
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/imagery/get-a-static-map?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            ubicacion ((lat, lang) o String): Latitud y longitud o Dirección de la ubicación dada.
            width (int, optional): Ancho de la imagen. Defaults to 500.
            height (int, optional): Alto de la imagen. Defaults to 500.
            zoomLevel (int, optional): Nivel de zoom. Defaults to 16.
            **kwargs: Los posibles kwargs están descritos en el link de arriba.

        Returns:
            Image: Imagen de la ubicación.
        """

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se agregan los parámetros a la consulta REST
        kwargs.update({'zoomLevel': zoomLevel})
        kwargs.update({'dpi': "Large"})
        kwargs.update({'mapSize': str(width) + ',' + str(height)})

        url = self._url_localizacion_imagen

        # Si se ingresa una longitud y latitud.
        if type(ubicacion) is tuple or type(ubicacion) is list:
            # Se agrega el valor obligatorio a enviar
            url += '/' + _tuple_LatLng_to_string(ubicacion) + '?'

            # Para poder agregar un pin en la ubicación
            kwargs.update(
                {'pushpin': _tuple_LatLng_to_string(ubicacion) + ';66'})

        elif type(ubicacion) is str:
            # Se agrega el valor obligatorio a enviar
            url += '/' + ubicacion + '?'

        # Se agrega a la consulta todos los parámetros kwargs
        url += urlencode(kwargs)

        # Se organiza el directorio para guardar la imagen de la ubicación
        path = Path("images")
        path.mkdir(parents=True, exist_ok=True)
        filename = 'images/localizacion(' + \
            _posicion_a_string_url(ubicacion) + ').png'

        # Se hace la consulta al servicio REST y se guarda la imagen
        urllib.request.urlretrieve(url, filename)
        return Image(filename=filename)

    def _rest_ruta_imagen(self, inicio, final, via=[], width=500, height=500, **kwargs):
        """ Búsqueda de rutas de Bing Maps.
            Diccionario de parámetros requeridos: {'wayPoint.1': 'inicio', 'wayPoint.2': 'final'}
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            inicio ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación inicial.
            final ('lat, lng' o String): Latitud y longitud o Dirección de la ubicación final.
            via (list<('lat, lng')> o list<String>, optional): Lista de tuplas con las latitudes y longitudes 
                o Direcciones de las ubicaciones intermedias. Defaults to [].
            width (int, optional): Ancho de la imagen. Defaults to 500.
            height (int, optional): Alto de la imagen. Defaults to 500.
            **kwargs: Los posibles kwargs incluyen: 'wayPoint.2+n', 'heading', 'optimize', 'avoid', 
                'distanceBeforeFirstTurn', 'heading', 'optimize', 'routeAttributes', 
                'routePathOutput', 'maxSolutions', 'tolerances', 'distanceUnit', 'dateTime', 
                'timeType', 'mfaxSolutions', 'travelMode'.
        Returns:
            JSON: JSON con la respuesta del servicio REST de Rutas de Bing Maps.
        """
        # Se guardan en una lista las direcciones de inicio y fin y las paradas intermedias en la consulta
        paradas = []
        paradas.append(_posicion_a_string_url(inicio))
        if len(via) > 0:
            paradas = paradas + \
                [_posicion_a_string_url(latlng) for latlng in via]
        paradas.append(_posicion_a_string_url(final))

        # Se guarda el número de paradas totales (contando inicio y fin)
        numero_paradas = len(paradas)

        # Se transforma las direcciones y paradas en datos validos para la consulta al servicio REST
        viajes = {}
        for n, wp in zip(range(1, numero_paradas + 1), paradas):
            if n == 1 or n == numero_paradas:
                viajes['wayPoint.' + str(n)] = wp
            else:
                viajes['viaWayPoint.' + str(n)] = wp

        # Se agrega a los parámetros kwargs las ubicaciones
        kwargs.update(viajes)

        # Se agrega la clave de la API Bing Maps
        kwargs.update({'key': self._api_key})

        # Se agregan los parámetros de la imagen
        kwargs.update({'mapSize': str(width) + ',' + str(height)})
        kwargs.update({'dpi': "Large"})

        # Se crea y se agregan a la consulta todos los parámetros extra
        url = self._url_rutas_imagen + '?'
        url += urlencode(kwargs)

        # Se organiza el directorio para guardar la imagen de la ubicación
        path = Path("images")
        path.mkdir(parents=True, exist_ok=True)
        filename = 'images/Ruta(' + _posicion_a_string_url(inicio) + \
            ')(' + _posicion_a_string_url(final) + ').png'

        # Se hace la consulta al servicio REST y se guarda la imagen
        urllib.request.urlretrieve(url, filename)
        return Image(filename=filename)


class Localizacion(object):
    """ 
    Clase que representa una localización geográfica.
    """

    def __init__(self, map_service, latlng=None, direccion=None, **kwargs):
        """ Inicializa una localización geográfica.
            Si se ingresa una dirección recomendable escribir con el siguiente formato:
            "Búsqueda, Ciudad, País"

        Args:
            map_service (MapService): Objeto MapService con el servicio de mapas de Bing Maps.
            latlng (lat, lng): Tupla con la latitud y longitud de la ubicación.
            direccion (String): Dirección de la ubicación.

        Raises:
            ValueError: Cuando no es correcto alguno de los valores ingresados
        """

        self._data_procesada = False
        self._imagen_procesada = False
        self._latlng_recibido = False
        self._direccion_recibida = False

        self._lat = None
        self._lng = None
        self._latlng = None
        self._direccion = None

        if latlng is not None and direccion is not None:
            self._latlng_recibido = True
            self._direccion_recibida = True
        else:
            if latlng is not None:
                if type(latlng) is tuple or type(latlng) is list:
                    self._lat = latlng[0]
                    self._lng = latlng[1]
                    self._latlng = latlng
                    self._latlng_recibido = True
                else:
                    raise ValueError(
                        'La latitud y longitud deben ser una tupla o lista')
            elif direccion is not None:
                if type(direccion) is str:
                    self._direccion = direccion
                    self._direccion_recibida = True
                else:
                    print(type(direccion))
                    raise ValueError('La dirección debe ser un String')
            else:
                raise ValueError(
                    'Debe especificar una latitud y una longitud o una dirección')

        self._kwargs = kwargs
        self._map_service = map_service

    def procesar(self):
        """ Procesa los datos de la localización.

        Raises:
            ValueError: Cuando ocurre un error inesperado.

        Returns:
            JSON: JSON con los datos de la localización.
        """
        if self._data_procesada:
            raise ValueError('La localización ya ha sido procesada')
        if self._latlng_recibido and self._direccion_recibida:
            raise ValueError('No es necesario procesar la ubicación')
        else:
            if self._direccion is not None:

                try:
                    self.data = self._map_service._rest_localizacion(
                        self._direccion, **self._kwargs)
                    self._data_procesada = True
                except:
                    raise ValueError('Error, al procesar REST')

            elif self._latlng is not None:

                try:
                    self.data = self._map_service._rest_localizacion(
                        self._latlng, **self._kwargs)
                    self._data_procesada = True
                except:
                    raise ValueError('Error, al procesar REST')

            else:
                raise ValueError(
                    'Error, no hay datos de ubicación para procesar')

        return self.data

    def obtener_latlng(self):
        """ Obtiene la latitud y longitud de la localización.

        Returns:
            Tupla: Tupla con la latitud y longitud de la localización.
        """
        if self._latlng_recibido:
            return self._latlng
        else:
            if not self._data_procesada:
                self.procesar()
            return tuple(self.data['point']['coordinates'])

    def obtener_direccion(self):
        """ Obtiene la dirección de la localización.

        Returns:
            String: Dirección de la localización.
        """
        if self._direccion_recibida:
            return self._direccion
        else:
            if not self._data_procesada:
                self.procesar()
            return self.data['address']['formattedAddress']

    def obtener_imagen(self, **kwargs):
        """ Obtiene la imagen de la localización.
            Consulte  https://docs.microsoft.com/en-us/bingmaps/rest-services/imagery/get-a-static-map?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            **kwargs: Argumentos adicionales para la consulta.

        Returns:
            String: URL de la imagen de la localización.
        """
        if self._imagen_procesada:
            return self._imagen
        else:
            if not self._data_procesada:
                self.procesar()

            latlng = self.obtener_latlng()

            try:
                self._imagen = self._map_service._rest_localizacion_imagen(
                    latlng, **kwargs)
                self._imagen_procesada = True
                return self._imagen
            except:
                raise ValueError('Error, al procesar REST')


class Ruta(object):
    """ 
    Clase que representa una ruta.
    """

    def __init__(self, map_service, inicio, final, paradas=[], **kwargs):
        """ Inicializa una ruta.
            Las localizaciones dadas son recomendables que ya hayan sido procesadas.

        Args:
            map_service (MapService): Objeto MapService con el servicio de mapas de Bing Maps.
            inicio (Localizacion): Localización de inicio de la ruta.
            final (Localizacion): Localización de final de la ruta.
            paradas (list<Localizacion>, optional): Lista de localizaciones intermedias. Defaults to [].

        Raises:
            ValueError: Si hay alguna verificación fallida.
        """

        self._data_procesada = False
        self._imagen_procesada = False
        self._paradas = None

        if type(inicio) is Localizacion:
            self._inicio = inicio
        else:
            raise ValueError('El inicio debe ser una localización')

        if type(final) is Localizacion:
            self._final = final
        else:
            raise ValueError('El final debe ser una localización')

        if type(paradas) is list:
            self._paradas = paradas
        else:
            raise ValueError('Las paradas deben ser una lista')

        self._kwargs = kwargs
        self._map_service = map_service

    def procesar(self):
        """ Procesa los datos de la Ruta.

        Raises:
            ValueError: Cuando ocurre un error inesperado.

        Returns:
            JSON: JSON con los datos de la ruta.
        """
        if self._data_procesada:
            raise ValueError('La localización ya ha sido procesada')
        else:
            proc_inicio = None
            proc_final = None
            if self._inicio._latlng_recibido:
                proc_inicio = self._inicio.obtener_latlng()
            elif self._inicio._direccion_recibida:
                proc_inicio = self._inicio.obtener_direccion()
            else:
                raise ValueError(
                    'La localización de inicio no ha sido procesada, porfavor ejecutar método procesar()')

            if self._final._latlng_recibido:
                proc_final = self._final.obtener_latlng()
            elif self._final._direccion_recibida:
                proc_final = self._final.obtener_direccion()
            else:
                raise ValueError(
                    'La localización de final no ha sido procesada, porfavor ejecutar método procesar()')

            try:
                self.data = self._map_service._rest_ruta(proc_inicio, proc_final, [
                    loc.obtener_latlng() for loc in self._paradas], **self._kwargs)
                self._data_procesada = True
            except:
                raise ValueError('Error, al procesar REST')

        return self.data

    ################################################################################
    ################################ DISTANCIAS ####################################
    ################################################################################

    def distancia_geodesica_kilometros(self):
        """ Retorna la distancia geodesica en kilometros entre dos puntos.
            Usando la librería geopy.distance.

        Returns:
            float: Distancia de la geodesica en kilometros entre los puntos dados.
        """
        if self._inicio.obtener_latlng() is None or self._final.obtener_latlng() is None:
            raise ValueError(
                "Error, ejecutar el método procesar() en las localizaciones de la ruta")
        else:
            return geodesic(self._inicio.obtener_latlng(), self._final.obtener_latlng()).km

    def distancia_ruta_bing_kilometros(self):
        """ Retorna la distancia de viaje en kilometros teniendo en cuenta la ruta.
            Es decir, no se está midiendo una linea recta sino la ruta física de conducción entre los puntos dados.
            Todo esto usando el servicio REST de Bing Maps.

        Returns:
            float: Distancia de la ruta en conducción en kilometros entre los puntos dados.
        """
        if not self._data_procesada:
            self.procesar()
        return self.data['travelDistance']

    def distancia_ruta_bing_metros(self):
        """ Retorna la distancia de viaje en metros teniendo en cuenta la ruta.
            Es decir, no se está midiendo una linea recta sino la ruta física de conducción entre los puntos dados.
            Todo esto usando el servicio REST de Bing Maps.

        Returns:
            float: Distancia de la ruta en conducción en metros entre los puntos dados.
        """
        return self.distancia_ruta_bing_kilometros() * 1000

    ################################################################################
    ############################### TIEMPOS VIAJE ##################################
    ################################################################################

    def tiempo_de_viaje_minutos_con_velocidad_constante(self, distancia_km, velocidad_km_h):
        """ Retorna el tiempo de viaje en minutos teniendo en cuenta la velocidad constante.

        Args:
            distancia_km (float): Distancia en kilometros.
            velocidad_km_h (float): Velocidad en kilometros por hora.

        Raises:
            ValueError: Cuando la velocidad es menor a 0.

        Returns:
            float: Tiempo de viaje en minutos.
        """
        if velocidad_km_h <= 0:
            raise ValueError('La velocidad debe ser mayor a cero.')
        return (distancia_km / velocidad_km_h) * 60

    def tiempo_de_viaje_segundos(self):
        """ Retorna el tiempo de viaje en segundos teniendo en cuenta la ruta física de conducción.
            Este tiempo ha sido considerado sin tráfico.
            Todo esto usando el servicio REST de Bing Maps.

        Returns:
            float: Tiempo de viaje en segundos entre los puntos dados.
        """
        if not self._data_procesada:
            self.procesar()
        return self.data['travelDurationTraffic']

    def tiempo_de_viaje_minutos(self):
        """ Retorna el tiempo de viaje en minutos teniendo en cuenta la ruta física de conducción.
            Este tiempo ha sido considerado sin tráfico.
            Todo esto usando el servicio REST de Bing Maps.

        Returns:
            float: Tiempo de viaje en minutos entre los puntos dados.
        """
        return self.tiempo_de_viaje_segundos() / 60

    ################################################################################
    ################################### OTROS ######################################
    ################################################################################

    def indicaciones_ruta(self, traducir=False):
        """Retorna una lista de las indicaciones de la ruta teniendo en cuenta la ruta física de conducción.
            Todo esto usando el servicio REST de Bing Maps.
            Consulte https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route?redirectedfrom=MSDN
            para más información de las descripciones.

        Args:
            traducir (bool, optional): Indica si se debe traducir las indicaciones de la ruta. Defaults to False.

        Returns:
            List<String>: Lista de las indicaciones de la ruta.
        """
        if not self._data_procesada:
            self.procesar()
        # Se obtiene la lista de indicaciones
        indicacioneItems = self.data["routeLegs"][0]["itineraryItems"]

        indicaciones = []
        for item in indicacioneItems:
            texto = item["instruction"]["text"]
            # Si se quieren traducir las indicaciones, se hace la traducción a español
            if traducir:
                self._translator = Translator()
                texto = self._translator.translate(
                    item["instruction"]["text"], src='en', dest='es').text
            indicaciones.append(texto)
            # print(texto)

        return indicaciones

    def obtener_imagen(self, **kwargs):
        """ Obtiene la imagen de la localización.

        Args:
            kwargs: Argumentos de la función de la librería de mapas.

        Returns:
            String: URL de la imagen de la localización.
        """
        if self._imagen_procesada:
            return self._imagen
        if not self._data_procesada:
            self.procesar()
        proc_inicio = None
        proc_final = None
        if self._inicio._latlng_recibido:
            proc_inicio = self._inicio.obtener_latlng()
        elif self._inicio._direccion_recibida:
            proc_inicio = self._inicio.obtener_direccion()
        else:
            raise ValueError(
                'La localización de inicio no ha sido procesada, porfavor ejecutar método procesar()')

        if self._final._latlng_recibido:
            proc_final = self._final.obtener_latlng()
        elif self._final._direccion_recibida:
            proc_final = self._final.obtener_direccion()
        else:
            raise ValueError(
                'La localización de final no ha sido procesada, porfavor ejecutar método procesar()')

        try:
            self._imagen = self._map_service._rest_ruta_imagen(proc_inicio, proc_final, [
                loc.obtener_latlng() for loc in self._paradas], **kwargs)
            self._imagen_procesada = True
            return self._imagen
        except:
            raise ValueError('Error, al procesar REST')
