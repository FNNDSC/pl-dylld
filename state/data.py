str_about = '''
    This module is responsible for handling some state related information
    which is mostly information about the ChRIS/CUBE instance.

    Core data includes information on the ChRIS/CUBE instances as well as
    information relevant to the pipeline to be scheduled.
'''

from    pudb.remote             import set_trace
from    curses                  import meta
from    pathlib                 import Path
import  pudb
import  json
import  os
from    urllib.parse            import urlparse
import  logging
logging.basicConfig(level=logging.CRITICAL)

class env:
    '''
    A class that contains environmental data -- mostly information about CUBE
    as well as data pertaining to the orthanc instance
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor
        '''
        self.inputdir   : Path              = None
        self.outputdir  : Path              = None
        self.CUBE       : CUBEinstance      = CUBEinstance()
        self.orthanc    : Orthancinstance   = Orthancinstance()
        self.debug      : dict              = {
            'do'        : False,
            'termsize'  : (80,25),
            'port'      : 7900,
            'host'      : '0.0.0.0'
        }

    def debug_setup(self, **kwargs) -> dict:
        """
        Setup the debugging structure based on <kwargs>

        Returns:
            dict: the debug structure
        """
        str_termsize    : str   = ""
        str_port        : str   = ""
        str_host        : str   = "0.0.0.0"
        b_debug         : bool  = False
        for k,v in kwargs.items():
            if k == 'debug'     :   b_debug         = v
            if k == 'termsize'  :   str_termsize    = v
            if k == 'port'      :   str_port        = v
            if k == 'host'      :   str_host        = v

        cols, rows  = str_termsize.split(',')
        self.debug['do']        = b_debug
        self.debug['termsize']  = (int(cols), int(rows))
        self.debug['port']      = int(str_port)
        self.debug['host']      = str_host
        return self.debug

    def set_telnet_trace_if_specified(self):
        """
        If specified in the env, pause for a telnet debug.

        If you are debugging, just "step" to return to the location
        in your code where you specified to break!
        """
        if self.debug['do']:
            set_trace(
                term_size   = self.debug['termsize'],
                host        = self.debug['host'],
                port        = self.debug['port']
            )

    def set_trace(self):
        """
        Simple "override" for setting a trace. If the Env is configured
        for debugging, then this set_trace will be called. Otherwise it
        will be skipped.

        This is useful for leaving debugging set_traces in the code, and
        being able to at runtime choose to debug or not.

        If you are debugging, just "step" to return to the location
        in your code where you specified to break!

        Returns:
            _type_: _description_
        """
        if self.debug['do']:
            pudb.set_trace()

    def __call__(self, str_key) -> str | None:
        '''
        get a value for a str_key
        '''
        if str_key in ['inputdir', 'outputdir']:
            return getattr(self, str_key)
        else:
            return None

    def set(self, **kwargs) -> bool:
        """
        A custom setter -- the normal python getter/setter approach suffers
        IMHO from implicitly adding members directly to the object.

        Returns:
            bool: True or False on setting
        """
        b_status:bool       = False
        for k,v in kwargs.items():
            if k == 'inputdir'  : self.inputdir     = v ; b_status = True
            if k == 'outputdir' : self.outputdir    = v ; b_status = True
        return b_status

class CUBEinstance:
    '''
    A class that contains data pertinent to a specific CUBE instance
    '''

    def __init__(self, *args, **kwargs):
        self.d_CUBE = {
            'username'  : 'chris',
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

    def setCUBE(self, str_key, str_val):
        '''
        set str_key to str_val
        '''
        if str_key in self.d_CUBE.keys():
            self.d_CUBE[str_key]    = str_val

    def __call__(self, str_key) -> str | None:
        '''
        get a value for a str_key
        '''
        if str_key in self.d_CUBE.keys():
            return self.d_CUBE[str_key]
        else:
            if str_key in ['inputdir', 'outputdir']:
                return getattr(self, str_key)
            else:
                return None

    def set(self, **kwargs) -> bool:
        """
        A custom setter -- the normal python getter/setter approach suffers
        IMHO from implicitly adding members directly to the object.

        Returns:
            bool: True or False on setting
        """
        b_status:bool       = False
        for k,v in kwargs.items():
            if k == 'inputdir'  : self.str_inputdir     = v ; b_status = True
            if k == 'outputdir' : self.str_outputdir    = v ; b_status = True
            if k == 'parentPluginInstanceID' :
                            self.parentPluginInstanceID = v ; b_status  = True
            if k == 'username'  : self.setCUBE(k, v)        ; b_status  = True
            if k == 'password'  : self.setCUBE(k, v)        ; b_status  = True
            if k == 'addreses'  : self.setCUBE(k, v)        ; b_status  = True
            if k == 'port'      : self.setCUBE(k, v)        ; b_status  = True
            if k == 'route'     : self.setCUBE(k, v)        ; b_status  = True
            if k == 'protocol'  : self.setCUBE(k, v)        ; b_status  = True
            if k == 'url'       :
                self.setCUBE(k, v)
                self.url_decompose()
                b_status  = True
        return b_status

    def onCUBE(self) -> dict:
        '''
        Return a dictionary that is a subset of self.d_CUBE
        suitable for using in calls to the CLI tool 'chrispl-run'
        '''
        return {
            'protocol': self('protocol'),
            'port':     self('port'),
            'address':  self('address'),
            'user':     self('username'),
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

    def url_decompose(self, *args):
        '''
        Decompose the internal URL into constituent parts
        '''

        o   = urlparse(self.d_CUBE['url'])
        self.d_CUBE['protocol']     = o.scheme
        self.d_CUBE['address']      = o.hostname
        self.d_CUBE['port']         = o.port
        if not self.d_CUBE['port']:
            self.d_CUBE['port']     = ''
        self.d_CUBE['route']        = o.path
        return self.d_CUBE['url']

class Orthancinstance:
    '''
    A class that contains data pertinent to a specific Orthanc instance
    '''

    def __init__(self, *args, **kwargs) -> None:
        self.d_orthanc: dict[str, str] = {
            'username'  : 'orthanc',
            'password'  : 'orthanc',
            'IP'        : '192.168.1.200',
            'port'      : '4242',
            'remote'    : '',
            'protocol'  : 'http',
            'route'     : '',
            'url'       : ''
        }

    def setOrthanc(self, str_key, str_val) -> bool:
        '''
        set str_key to str_val
        '''
        b_status:bool   = False
        if str_key in self.d_orthanc.keys():
            b_status    = True
            self.d_orthanc[str_key]    = str_val
        return b_status

    def __call__(self, str_key) -> str | None:
        '''
        get a value for a str_key
        '''
        if str_key in self.d_orthanc.keys():
            return self.d_orthanc[str_key]
        else:
            return None

    def set(self, **kwargs) -> bool:
        """
        A custom setter -- the normal python getter/setter approach suffers
        IMHO from implicitly adding members directly to the object.

        Returns:
            bool: True or False on setting
        """
        b_status:bool       = False
        for k,v in kwargs.items():
            if k == 'username'  : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'password'  : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'IP'        : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'port'      : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'remote'    : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'protocol'  : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'route'     : self.setOrthanc(k, v)        ; b_status  = True
            if k == 'url'       :
                self.setOrthanc(k, v)
                self.url_decompose()
                b_status  = True
        return b_status

    def url_decompose(self, *args):
        '''
        Decompose the internal URL into constituent parts
        '''
        o   = urlparse(self.d_orthanc['url'])

        self.d_orthanc['protocol']  = o.scheme
        self.d_orthanc['IP']        = o.hostname
        self.d_orthanc['port']      = o.port
        if not self.d_orthanc['port']:
            self.d_orthanc['port']       = ''
        self.d_orthanc['route']     = o.path
        return self.d_orthanc['url']

class Pipeline:
    '''
    Information pertinent to the pipline being scheduled. This is
    encapsulated with a class object to allow for possible future
    expansion.
    '''

    def __init__(self, *args, **kwargs):

        self.str_pipelineName       = ''

