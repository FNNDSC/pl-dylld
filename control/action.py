str_about = '''
    The action module provides functionality to run individual
    plugins as well as "pipelines" of plugins.

    This module is the contact "surface" between dypi and a CUBE
    instance. Control/manipulation of the ChRIS instance is effected
    by a set of CLI scripts that this module creates and then executes.

    NOTE: This module is "fragily" dependent on python-chrisclient and
    caw! Changes in those modules could break things here rather
    completely.
'''

from    .                       import  jobber
from    state                   import  data
import  os
import  re
import  pudb
import  json
from    argparse                import ArgumentParser, Namespace
from    chrisclient             import client

class PluginRun:
    '''
    A class wrapper about the CLI tool "chrispl-run" that POSTs a pl-shexec
    to CUBE.
    '''
    def __init__(self, *args, **kwargs):
        self.env                                    = None
        self.plugin                                 = ''
        self.shell              : jobber.Jobber     = jobber.Jobber({
                                                        'verbosity' :   1,
                                                        'noJobLogging': True
                                                        })
        self.attachToPluginID   : str               = ''
        self.options            : Namespace         = None
        for k, v in kwargs.items():
            if k == 'attachToPluginID'  : self.attachToPluginID     = v
            if k == 'env'               : self.env                  = v
            if k == 'options'           : self.options              = v

        self.l_runCMDresp       : list  = []
        self.l_branchInstanceID : list  = []

    def PLpfdorun_args(self, str_input : str) -> dict:
        '''
        Return the argument string pertinent to the pl-pfdorun plugin
        '''
        str_args : str = """
            --fileFilter=%s;
            --exec=cp %%inputWorkingDir/%%inputWorkingFile %%outputWorkingDir/%%inputWorkingFile;
            --noJobLogging;
            --verbose=5;
            --title=%s;
            --previous_id=%s
        """ % (str_input, str_input, self.env.parentPluginInstanceID)
        str_args = re.sub(r';\n.*--', ';--', str_args)
        str_args = str_args.strip()
        return {
            'args':     str_args
        }

    def chrispl_onCUBEargs(self):
        '''
        Return a string specifying the CUBE instance
        '''
        return {
            'onCUBE':  json.dumps(self.env.onCUBE())
        }

    def chrispl_run_cmd(self, str_inputData : str) -> dict:
        '''
        Return the CLI for the chrispl_run
        '''
        str_cmd = """chrispl-run --plugin name=pl-shexec --args="%s" --onCUBE %s""" % (
                self.PLpfdorun_args(str_inputData)['args'],
                json.dumps(self.chrispl_onCUBEargs()['onCUBE'], indent = 4)
            )
        str_cmd = str_cmd.strip().replace('\n', '')
        return {
            'cmd' : str_cmd
        }

    def __call__(self, str_input : str) ->dict:
        '''
        Copy the <str_input> to the output using pl-pfdorun
        '''
        # Remove the '/incoming/' from the str_input
        str_inputTarget     : str   = str_input.split('/')[-1]
        d_PLCmd             : dict  = self.chrispl_run_cmd(str_inputTarget)
        str_PLCmd           : str   = d_PLCmd['cmd']
        str_PLCmdfile       : str   = '/tmp/%s.sh' % str_inputTarget
        branchID            : int   = -1
        b_status            : bool  = False

        if self.options:
            str_scriptDir   : str   = '%s/%s' % (self.options.outputdir, str_inputTarget)
            os.mkdir(str_scriptDir)
            str_PLCmdfile   = '%s/%s/copy.sh' % (self.options.outputdir, str_inputTarget)

        with open(str_PLCmdfile, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(str_PLCmd)
        os.chmod(str_PLCmdfile, 0o755)
        d_runCMDresp        : dict  = self.shell.job_run(str_PLCmdfile)
        if not d_runCMDresp['returncode']:
            b_status                = True
            self.l_runCMDresp.append(d_runCMDresp)
            branchID        : int   = d_runCMDresp['stdout'].split()[2]
            self.l_branchInstanceID.append(branchID)
        else:
            b_status                = False

        return {
            'status'            : b_status,
            'run'               : d_runCMDresp,
            'input'             : str_input,
            'branchInstanceID'  : branchID
        }

class LLDcomputeflow:
    '''
    A class to create / manage the LLD compute flow
    '''

    def __init__(self, *args, **kwargs):
        self.env                : data.CUBEinstance =  None
        self.options            : Namespace         = None

        for k, v in kwargs.items():
            if k == 'env'               : self.env                  = v
            if k == 'options'           : self.options              = v

        self.cl          : client.Client = None
        self.cl                         = client.Client(self.env.url() , self.env.user(), self.env.password())
        self.d_pipelines : dict         = self.cl.get_pipelines()
        self.newTreeID   : int          = '-1'

    def waitForNodeInWorkflow(d_workflow, node_title : str):
        """
        Wait for a node in a workflow to transition to a finishedState
        """
        pass

    def inferenceOnData_do(self, inputDataNode):
        '''
        Generate the inference outputs on a given input
        '''
        d_inference   : dict  = self.cl.get_pipelines({'name': 'Leg Length Discrepency inference'})
        id_pipeline   : int   = d_inference['data'][0]['id']
        d_response    : dict  = self.cl.get_pipeline_default_parameters(id_pipeline, {'limit': 1000})
        d_nodes       : dict  = self.cl.compute_workflow_nodes_info(d_response['data'])
        dwf_inference : dict  = self.cl.create_workflow(id_pipeline,
                                    {
                                        'previous_plugin_inst_id'   : inputDataNode,
                                        'nodes_info'                : json.dumps(d_nodes)
                                    })
        dwf_detail   : dict  = self.cl.get_workflow_plugin_instances(
                    dwf_inference['id'], {'limit': 1000}
        )

    def computeFlow_build(self):
        """
        The main controller for the compute flow logic
        """
        self.inferenceOnData_do(self.newTreeID)

    def __call__(self,      filteredCopyInstanceID  : int) -> dict:
        '''
        Execute/manage the LLD compute flow
        '''
        self.newTreeID  : str           = filteredCopyInstanceID
        self.computeFlow_build()

class Caw:
    '''
    A class wrapper about the CLI tool "caw" that can POST a pipeline to
    a plugin instance ID
    '''

    def __init__(self, *args, **kwargs):
        self.env                                    = None
        self.pipeline           : str               = ''
        self.shell              : jobber.Jobber     = jobber.Jobber({
                                                        'verbosity' :   1,
                                                        'noJobLogging': True
                                                        })
        self.attachToPluginID   : str               = ''
        self.options            : Namespace         = None
        for k, v in kwargs.items():
            if k == 'attachToPluginID'  : self.attachToPluginID     = v
            if k == 'env'               : self.env                  = v
            if k == 'options'           : self.options              = v
        self.l_runCMDresp       : list  = []

    def pipeline(self, *args) -> str:
        '''
        pipeline name get/set
        '''
        if len(args):
            self.pipeline   = args[0]
        return self.pipeline

    def caw_argsCore(self) -> dict:
        '''
        Return the argument string pertinent to the caw
        '''
        str_args : str = """
            --address %s --username %s --password %s
        """ % (
            self.env.url(), self.env('user'), self.env('password')
        )
        return {
            'args': str_args
        }

    def caw_run_cmd(self,   attachToPluginID    : int,
                            pipeline            : str) -> dict:
        '''
        Return the CLI for the caw call
        '''
        str_cmd = """caw %s pipeline --target %s "%s" """ % (
            self.caw_argsCore()['args'], attachToPluginID, pipeline
        )
        str_cmd = str_cmd.strip().replace('\n', '')
        return {
            'cmd' : str_cmd
        }

    def __call__(self,      filteredCopyInstanceID  : int,
                            str_pipeline            : str,
                            str_input               : str = "") -> dict:
        '''
        Call caw on the appropriate plugin instance ID
        '''
        d_cawCmd            : dict  = self.caw_run_cmd(filteredCopyInstanceID, str_pipeline)
        str_cawCmd          : str   = d_cawCmd['cmd']
        str_cawCmdfile      : str   = '/tmp/caw-%s.sh' % filteredCopyInstanceID

        if self.options:
            str_cawCmdfile  = '%s/%s/caw-%s.sh' % ( self.options.outputdir,
                                                    str_input.split('/')[-1],
                                                    filteredCopyInstanceID)

        with open(str_cawCmdfile, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(str_cawCmd)
        os.chmod(str_cawCmdfile, 0o755)
        d_runCMDresp        : dict  = self.shell.job_run(str_cawCmdfile)
        return {
            'response'      : d_runCMDresp
        }

