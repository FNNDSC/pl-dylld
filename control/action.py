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
import  time

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
        pudb.set_trace()
        str_filter  : str   = ""
        # Remove any '*' and/or '/' chars from pattern search. This will
        # transform a string of '**/*dcm" to just 'dcm', suitable for pl-shexec
        str_ff      : str   = re.subn(r'[*/]', '', self.options.pattern)[0]
        if not self.options.inNode:
            str_filter  = "--fileFilter=%s" % str_input
        else:
            str_filter  = "--dirFilter=%s" % str_input
            if len(str_ff): str_filter += ";--fileFilter=%s" % str_ff

        str_args    : str = """
            %s;
            --exec=cp %%inputWorkingDir/%%inputWorkingFile %%outputWorkingDir/%%inputWorkingFile;
            --noJobLogging;
            --verbose=5;
            --title=%s;
            --previous_id=%s
        """ % (str_filter, str_input, self.env.CUBE.parentPluginInstanceID)

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
            'onCUBE':  json.dumps(self.env.CUBE.onCUBE())
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
        Copy the <str_input> to the output using pl-pfdorun. If the in-node
        self.options.inNode is true, perform a bulk copy of all files in the
        passed directory that conform to the filter.
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
        self.env                : data.env          =  None
        self.options            : Namespace         = None

        for k, v in kwargs.items():
            if k == 'env'               : self.env                  = v
            if k == 'options'           : self.options              = v

        self.cl         : client.Client = None
        self.cl                         = client.Client(self.env.CUBE.url() , self.env.CUBE.user(), self.env.CUBE.password())
        self.d_pipelines        : dict  = self.cl.get_pipelines()
        self.pltopo             : int   = self.cl.get_plugins({'name': 'pl-topologicalcopy'})
        self.newTreeID          : int   = -1
        self.ld_workflowhist    : list  = []
        self.ld_topologicalNode : dict  = {'data': []}

    def pluginInstanceID_findWithTitle(self, d_workflowDetail : dict, node_title : str) -> int:
        """
        Determine the plugin instance id in the workflow detail that has
        title substring <node_title>. If the d_workflowDetail is simply a plugin
        instance, return its id provided it has the <node_title>.
        """
        def plugin_hasTitle(d_plinfo, title):
            nonlocal pluginIDwithTitle
            if title.lower() in d_plinfo['title'].lower():
                pluginIDwithTitle   = d_plinfo['id']
                return True
            else:
                return False

        pluginIDwithTitle   : int           = -1
        d_plinfo            : dict          = {}
        if 'data' in d_workflowDetail:
            for d_plinfo in d_workflowDetail['data']:
                if plugin_hasTitle(d_plinfo, node_title): break
        else:
            plugin_hasTitle(d_workflowDetail, node_title)

        return pluginIDwithTitle

    def waitForNodeInWorkflow(self, d_workflowDetail, node_title : str):
        """
        Wait for a node in a workflow to transition to a finishedState
        """
        waitPoll        : int   = 5
        totalPolls      : int   = 100
        pollCount       : int   = 0
        b_finished      : bool  = False
        waitOnPluginID  : int   = self.pluginInstanceID_findWithTitle(
                                        d_workflowDetail, node_title
                                )
        str_pluginStatus: str   = 'unknown'
        d_plinfo        : dict  = {}
        if waitOnPluginID >= 0:
            while 'finished' not in str_pluginStatus.lower() and \
                pollCount < totalPolls :
                d_plinfo         = self.cl.get_plugin_instance_by_id(waitOnPluginID)
                str_pluginStatus = d_plinfo['status']
                time.sleep(waitPoll)
                pollCount += 1
            if 'finished' in d_plinfo['status']:
                b_finished  = d_plinfo['status'] == 'finishedSuccessfully'
        return {
            'finished'  : b_finished,
            'status'    : str_pluginStatus,
            'plinst'    : d_plinfo,
            'polls'     : pollCount,
            'plid'      : waitOnPluginID
        }

    def pipelineWithName_getNodes(self, str_pipelineName):
        """
        Find a pipeline that contains the passed name <str_pipelineName>
        and if found, return a nodes dictionary.
        """
        id_pipeline     : int   = -1
        d_nodes         : dict  = {}
        d_pipeline      : dict  = self.cl.get_pipelines({'name': str_pipelineName})
        if 'data' in d_pipeline:
            id_pipeline : int   = d_pipeline['data'][0]['id']
            d_response  : dict  = self.cl.get_pipeline_default_parameters(
                                        id_pipeline, {'limit': 1000}
                                )
            if 'data' in d_response:
                d_nodes : dict  = self.cl.compute_workflow_nodes_info(d_response['data'])
        return {
            'nodes'         : d_nodes,
            'id'            : id_pipeline
        }

    def workflow_schedule(
        self,
        inputDataNodeID     : str,
        str_pipelineName    : str,
        ld_nodeArgs         : list  = []
    ) -> dict:
        '''
        Schedule a workflow that has name <str_pipelineName> off a given node id
        of <inputDataNodeID>.
        '''
        d_pipeline      : dict  = self.pipelineWithName_getNodes(str_pipelineName)
        d_workflow      : dict  = self.cl.create_workflow(
                d_pipeline['id'],
                {
                    'previous_plugin_inst_id'   : inputDataNodeID,
                    'nodes_info'                : json.dumps(d_pipeline['nodes'])
                })
        d_workflowInst  : dict  = self.cl.get_workflow_plugin_instances(
                    d_workflow['id'], {'limit': 1000}
        )
        self.ld_workflowhist.append({
            'name'                      : str_pipelineName,
            'pipeline'                  : d_pipeline,
            'previous_plugin_inst_id'   : inputDataNodeID,
            'pipeline_plugins'          : d_workflowInst
        })
        return d_workflowInst

    def topologicalNode_run(self, str_nodeTitle : str, l_nodes : list, str_filterArgs):
        """
        Perform a toplogical join between nodes
        """
        idTopo          : int   = self.pltopo['data'][0]['id']
        d_plInstTopo    : dict  = self.cl.create_plugin_instance(
                                    idTopo,
                                    {
                                        'filter'            : str_filterArgs,
                                        'plugininstances'   : ','.join(map(str, l_nodes)),
                                        'title'             : str_nodeTitle,
                                        'previous_id'       : l_nodes[0]
                                    }
                                )
        self.ld_topologicalNode['data'].append(d_plInstTopo)
        return d_plInstTopo

    def nodes_join(self, str_title : str, l_nodes : list, str_joinArgs : str):
        d_topological_run : dict = self.topologicalNode_run(
            str_title, l_nodes, str_joinArgs
        )
        d_topological_done  : dict  = self.waitForNodeInWorkflow(
            d_topological_run,
            str_title
        )
        return d_topological_done

    def parentNode_isFinished(self, *args):
        d_parent            : dict          = None
        b_finished          : bool          = False
        if len(args)        : d_parent      = args[0]
        if not d_parent     : b_finished    = True
        else                : b_finished    = d_parent['finished']
        return b_finished

    def parentNode_IDappend(self, l_nodes, *args) -> list:
        """
        Append the node ID of the parent in the *args to l_nodes and
        return the new list
        """
        d_parent            : dict          = None
        if len(args):
            d_parent    = args[0]
            l_nodes.append(self.parentNode_IDget(*args))
        return l_nodes

    def parentNode_IDget(self, *args) -> int:
        """
        Simply get the plugin instance of the passed parent node
        """
        id                  : int           = -1
        d_parent            : dict          = None
        if len(args):
            d_parent    = args[0]
            id          = d_parent['plinst']['id']
        return id

    def pluginID_findInWorkflowDesc(self, tp_workflowAndNode) -> int :
        """
        Given a tuple of (<workflowName>, <nodeName>) substrings,
        return the corresponding plugin instance id of node
        <nodeName> in workflow <workflowName>. Handle the special case
        when the "workflow" is a "topological" node.
        """
        pluginID    : int       = -1
        l_hit       : list      = []
        workflow                = None
        if type(tp_workflowAndNode) == int:
            return tp_workflowAndNode
        str_workflow, str_node  = tp_workflowAndNode

        # pudb.set_trace()
        if str_workflow.lower() == 'topological':
            workflow    = self.ld_topologicalNode
        else:
            filterHit   = filter(lambda p: str_workflow in p['name'], self.ld_workflowhist)
            workflow    = list(filterHit)[0]['pipeline_plugins']
        if workflow:
            pluginID    = self.pluginInstanceID_findWithTitle(
                            workflow, str_node
                        )
        return pluginID

    def nodeIDs_verify(self, l_nodeID):
        """
        Verify that a list of <l_nodeID> contains only int
        types. This will map any 'distalNodeIDs' that are string
        tuples of (<workflow>, <nodeTitle>) to the corrsponding
        plugin instance id
        """
        l_nodeID = [self.pluginID_findInWorkflowDesc(x) for x in l_nodeID]
        return l_nodeID

    def flow_executeAndBlockUntilNodeComplete(
            self,
            *args,
            **kwargs,
    ) -> dict:
        """
        Execute a workflow identified by a (sub string) in its
        <str_workflowTitle> by anchoring it to <attachToNodeID> in the
        feed/compute tree. This <attachToNodeID> can be supplied in the
        kwargs, or if omitted, then the "parent" node passed in args[0]
        is assumed to be the connector.

        Once attached to a node, the whole workflow is scheduled. This
        workflow will have N>=1 compute nodes, each identified by a
        title. This method will only "return" to a caller when one of
        these nodes with 'waitForNodeWithTitle' enters the finished
        state. Note that this state can be 'finishedSuccessfully' or
        'finishedWithError'.
        """
        d_prior             : dict  = None
        str_workflowTitle   : str   = "no workflow title"
        attachToNodeID      : int   = -1
        str_blockNodeTitle  : str   = "no node title"
        b_canFlow           : bool  = False

        for k, v in kwargs.items():
            if k == 'workflowTitle'         :   str_workflowTitle   = v
            if k == 'attachToNodeID'        :   attachToNodeID      = v
            if k == 'waitForNodeWithTitle'  :   str_blockNodeTitle  = v

        if self.parentNode_isFinished(*args):
            if attachToNodeID == -1:
                attachToNodeID = self.parentNode_IDget(*args)
            return  self.waitForNodeInWorkflow(
                        self.workflow_schedule(
                            attachToNodeID,
                            str_workflowTitle
                        ),
                        str_blockNodeTitle
                    )

    def flows_connect(
        self,
        *args,
        **kwargs):
        """
        Perform a toplogical join by using the args[0] as logical
        parent and connect this parent to a list of distalNodeIDs
        """
        d_prior             : dict  = None
        str_joinNodeTitle   : str   = "no title specified for topo node"
        l_nodeID            : list  = []
        str_topoJoinArgs    : str   = ""
        b_canFlow           : bool  = False
        d_ret               : dict  = {}
        b_invertOrder       : bool  = False

        # pudb.set_trace()
        for k, v in kwargs.items():
            if k == 'connectionNodeTitle'   :   str_joinNodeTitle   = v
            if k == 'distalNodeIDs'         :   l_nodeID            = v
            if k == 'invertIDorder'         :   b_invert            = v
            if k == 'topoJoinArgs'          :   str_topoJoinArgs    = v

        if self.parentNode_isFinished(*args):
            l_nodeID    = self.parentNode_IDappend(l_nodeID, *args)
            l_nodeID    = self.nodeIDs_verify(l_nodeID)
            if b_invertOrder: l_nodeID.reverse()
            d_ret       = self.nodes_join(
                str_joinNodeTitle,
                l_nodeID,
                str_topoJoinArgs
            )
        return d_ret

    def computeFlow_build(self):
        """
        The main controller for the compute flow logic
        """

        d_ret : dict = \
        self.flow_executeAndBlockUntilNodeComplete(
            self.flows_connect(
                self.flow_executeAndBlockUntilNodeComplete(
                    self.flows_connect(
                        self.flow_executeAndBlockUntilNodeComplete(
                            self.flows_connect(
                                self.flow_executeAndBlockUntilNodeComplete(
                                    attachToNodeID          = self.newTreeID,
                                    workflowTitle           = 'Leg Length Discrepency inference',
                                    waitForNodeWithTitle    = 'heatmaps'
                                ),
                                connectionNodeTitle     = 'mergeDICOMSwithInference',
                                distalNodeIDs           = [self.newTreeID],
                                topoJoinArgs            = '\.dcm$,\.csv$'
                            ),
                            workflowTitle           = 'Leg Length Discrepency prediction formatter',
                            waitForNodeWithTitle    = 'landmarks-to-json'
                        ),
                        connectionNodeTitle     = 'mergeJPGSwithInference',
                        distalNodeIDs           = [('Leg Length Discrepency inference', 'heatmaps')],
                        topoJoinArgs            = '\.jpg$,\.json$'
                    ),
                    workflowTitle           = 'Leg Length Discrepency measurement',
                    waitForNodeWithTitle    = 'measure-leg-segments'
                ),
                connectionNodeTitle     = 'mergeMarkedJPGSwithDICOMS',
                distalNodeIDs           = [('Topological', 'mergeDICOMSwithInference')],
                topoJoinArgs            = '\.dcm$,\.png$'
            ),
            workflowTitle           = 'PNG-to-DICOM',
            waitForNodeWithTitle    = 'pacs-push'
        )
        # pudb.set_trace()
        return d_ret

    def __call__(self,      filteredCopyInstanceID  : int) -> dict:
        '''
        Execute/manage the LLD compute flow
        '''
        self.newTreeID  : str           = int(filteredCopyInstanceID)
        d_computeFlow   : dict          = self.computeFlow_build()
        return d_computeFlow

