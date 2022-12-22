str_about = '''
    This module is responsible for handling some state related information
    which is mostly information about the ChRIS/CUBE instance.

    Core data includes information on the ChRIS/CUBE instances as well as
    information relevant to the pipeline to be scheduled.
'''

from    curses      import meta
from    pathlib     import Path
import  json
import  os

class env:
    '''
    A class that contains environmental data -- mostly information about CUBE
    as well as data pertaining to the orthanc instance
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''

class CUBEinstance:
    '''
    A class that contains data pertinent to a specific CUBE instance
    '''

    def __init__(self, *args, **kwargs):
        self.d_CUBE = {
            'user'      : 'chris',
            'password'  : 'chris1234',
            'address'   : '192.168.1.200',
            'port'      : '8000',
            'route'     : '/api/v1/',
            'protocol'  : 'http',
            'url'       : ''
        }
        self.parentPluginInstanceID     : str   = ''
        self.str_inputdir               : str   = None
        self.str_outputdir              : str   = None

    @property
    def IP(self):
        return self.d_CUBE['address']

    @IP.setter
    def IP(self, a):
        self.d_CUBE['address'] = a

    @property
    def port(self):
        return self.d_CUBE['port']

    @port.setter
    def port(self, a):
        self.d_CUBE['port'] = a

    @property
    def inputdir(self):
        return self.str_inputdir

    @inputdir.setter
    def inputdir(self, a):
        self.str_inputdir = a

    @property
    def outputdir(self):
        return self.str_outputdir

    @outputdir.setter
    def outputdir(self, a):
        self.str_outputdir = a

    def onCUBE(self) -> dict:
        '''
        Return a dictionary that is a subset of self.d_CUBE
        suitable for using in calls to the CLI tool 'chrispl-run'
        '''
        return {
            'protocol': self('protocol'),
            'port':     self('port'),
            'address':  self('address'),
            'user':     self('user'),
            'password': self('password')
        }

    def parentPluginInstanceID_discover(self) -> dict:
        '''
        Determine the pluginInstanceID of the parent plugin. CUBE provides
        several environment variables:

            CHRIS_JID
            CHRIS_PLG_INST_ID
            CHRIS_PREV_JID
            CHRIS_PREV_PLG_INST_ID

        '''

        self.parentPluginInstanceID = os.environ['CHRIS_PREV_PLG_INST_ID']

        return {
            'parentPluginInstanceID':   self.parentPluginInstanceID
        }

    def url(self, *args):
        '''
        get/set the URL
        '''
        str_colon : str = ""
        if len(self.d_CUBE['port']):
            str_colon   = ":"
        if len(args):
            self.d_CUBE['url']  = args[0]
        else:
            self.d_CUBE['url']  = '%s://%s%s%s%s' % (
                self.d_CUBE['protocol'],
                self.d_CUBE['address'],
                str_colon,
                self.d_CUBE['port'],
                self.d_CUBE['route']
            )
        return self.d_CUBE['url']

    def user(self, *args) -> str:
        '''
        get/set the CUBE user
        '''
        if len(args): self.d_CUBE['user']  = args[0]
        return self.d_CUBE['user']

    def password(self, *args) -> str:
        '''
        get/set the CUBE user
        '''
        if len(args): self.d_CUBE['password']  = args[0]
        return self.d_CUBE['password']

    def set(self, str_key, str_val):
        '''
        set str_key to str_val
        '''
        if str_key in self.d_CUBE.keys():
            self.d_CUBE[str_key]    = str_val

    def __call__(self, str_key):
        '''
        get a value for a str_key
        '''
        if str_key in self.d_CUBE.keys():
            return self.d_CUBE[str_key]
        else:
            return ''

class Orthancinstance:
    '''
    A class that contains data pertinent to a specific Orthanc instance
    '''

    def __init__(self, *args, **kwargs):
        self.d_orthanc = {
            'user'      : 'chris',
            'password'  : 'chris1234',
            'address'   : '192.168.1.200',
            'remote'    : ''
        }

    @property
    def address(self):
        return self.d_orthanc['address']

    @address.setter
    def address(self, a):
        self.d_orthanc['address'] = a

    @property
    def port(self):
        return self.d_CUBE['port']

    @port.setter
    def port(self, a):
        self.d_CUBE['port'] = a

    @property
    def username(self):
        return self.d_orthanc['user']

    @username.setter
    def username(self, a):
        self.d_orthanc['user'] = a

    @property
    def password(self):
        return self.d_orthanc['password']

    @password.setter
    def password(self, a):
        self.d_orthanc['password'] = a

    @property
    def remote(self):
        return self.d_orthanc['remote']

    @remote.setter
    def remote(self, a):
        self.d_orthanc['remote'] = a

    def user(self, *args) -> str:
        '''
        get/set the CUBE user
        '''
        if len(args): self.d_orthanc['user']  = args[0]
        return self.d_orthanc['user']

    def password(self, *args) -> str:
        '''
        get/set the CUBE user
        '''
        if len(args): self.d_orthanc['password']  = args[0]
        return self.d_orthanc['password']

    def set(self, str_key, str_val):
        '''
        set str_key to str_val
        '''
        if str_key in self.d_orthanc.keys():
            self.d_orthanc[str_key]    = str_val

    def __call__(self, str_key):
        '''
        get a value for a str_key
        '''
        if str_key in self.d_orthanc.keys():
            return self.d_orthanc[str_key]
        else:
            return ''

class Pipeline:
    '''
    Information pertinent to the pipline being scheduled. This is
    encapsulated with a class object to allow for possible future
    expansion.
    '''

    def __init__(self, *args, **kwargs):

        self.str_pipelineName       = ''

