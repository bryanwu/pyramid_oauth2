import urllib
import urllib2

from pyramid.path import DottedNameResolver
from pyramid.view import view_config
from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPFound

ENABLED_CLIENTS = 'oauth2.clients'
CLIENT_ID = 'oauth2.%s.client_id'
SECRET = 'oauth2.%s.secret'
AUTHORIZE_ENDPOINT = 'oauth2.%s.authorize_endpoint'
TOKEN_ENDPOINT = 'oauth2.%s.token_endpoint'
SCOPE = 'oauth2.%s.scope'
CALLBACK = 'oauth2.%s.callback'

class Provider(object):

    def __init__(self,name, client_id, secret, authorize_url, access_token_url, callback=None, **kargs):
        self.name = name
        self.client_id = client_id
        self.secret = secret
        self.authorize_url = authorize_url
        self.access_token_url = access_token_url
        self.callback = callback
        self.extra = kargs

    def __call__(self, request, data):
        if self.callback:
            self.callback(request, data)

        raise HTTPFound('/')

    def access_url(self, request):
        code = request.params.get('code')

        params = dict()
        params['client_id'] = self.client_id
        params['client_secret'] = self.secret
        params['redirect_uri'] = request.route_url('oauth_callback', provider=self.name)
        params['code'] = code

        return "%s?%s" % (self.access_token_url, urllib.urlencode(params))

    def authenticate_url(self, request):
        params = dict(**self.extra)

        params['client_id'] =  self.client_id
        params['redirect_uri'] = request.route_url('oauth_callback', provider=self.name)
        params['response_type'] = 'code'

        return "%s?%s" % (self.authorize_url, urllib.urlencode(params))

def authenticate(request):
    provider = get_provider(request)

    if provider:
        raise HTTPFound(provider.authenticate_url(request))
    else:
        raise NotFound()

def view_callback(request):
    provider = get_provider(request)

    if not provider:
        raise NotFound()

    data = urllib2.urlopen(provider.access_url(request)).read()
    provider(request, data)

def get_provider(request):
    provider = request.matchdict.get('provider')
    if provider:
        return request.registry.oauth2_providers.get(provider)
    else:
        return None

def add_oauth2_provider(config, provider):
    config.registry.oauth2_providers[provider.name] = provider

def load_providers(config):
    resolver = DottedNameResolver()
    config.registry.oauth2_providers = dict()
    settings = config.registry.settings

    clients = config.registry.settings.get(ENABLED_CLIENTS)
    for client in clients.split(','):
        scope = settings.get(SCOPE % client)
        authorize_endpoint = settings.get(AUTHORIZE_ENDPOINT % client)
        token_endpoint = settings.get(TOKEN_ENDPOINT % client)
        client_id = settings.get(CLIENT_ID % client)
        secret = settings.get(SECRET % client)
        callback = settings.get(CALLBACK % client)

        if callback:
            callback = resolver.resolve(callback)

        # self,name, client_id, secret, authorize_url, access_token_url, callback=None, **kargs
        provider = Provider(client, client_id, secret, authorize_endpoint, token_endpoint, callback, scope=scope)
        config.add_oauth2_provider(provider)

    

def includeme(config):
    config.add_route('oauth_authenticate', '/oauth/{provider}/authenticate')
    config.add_view(authenticate, route_name='oauth_authenticate')

    config.add_route('oauth_callback', '/oauth/{provider}/callback')
    config.add_view(view_callback, route_name='oauth_callback')

    config.add_directive('add_oauth2_provider', add_oauth2_provider)

    load_providers(config)
