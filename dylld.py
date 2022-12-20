#!/usr/bin/env python

from    pathlib                 import Path
from    argparse                import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter

from    chris_plugin            import chris_plugin, PathMapper

from    pathlib                 import Path

import  os
import  pudb
from    pudb.remote             import set_trace

from    loguru                  import logger
from    concurrent.futures      import ThreadPoolExecutor
from    typing                  import Callable

from    state                   import data
from    logic                   import behavior
from    control                 import action
from    control.filter          import PathFilter


Env             = data.CUBEinstance()
PLinputFilter   = None
LOG             = None
LLD             = None

__version__ = '1.0.13'

DISPLAY_TITLE = r"""
       _           _       _ _     _ 
      | |         | |     | | |   | |
 _ __ | |______ __| |_   _| | | __| |
| '_ \| |______/ _` | | | | | |/ _` |
| |_) | |     | (_| | |_| | | | (_| |
| .__/|_|      \__,_|\__, |_|_|\__,_|
| |                   __/ |          
|_|                  |___/           
"""


parser          = ArgumentParser(
    description = '''
A ChRIS plugin that dynamically builds a workflow to compute length
discrepencies from extremity X-Rays
''',
    formatter_class=ArgumentDefaultsHelpFormatter)


parser.add_argument('-V', '--version', action='version',
                    version=f'%(prog)s {__version__}')

parser.add_argument(
            '--pattern',
            default = '**/*dcm',
            help    = '''
            pattern for file names to include (you should quote this!)
            (this flag triggers the PathMapper on the inputdir).'''
)
parser.add_argument(
            '--pluginInstanceID',
            default = '',
            help    = 'plugin instance ID from which to start analysis'
)
parser.add_argument(
            '--verbosity',
            default = '0',
            help    = 'verbosity level of app'
)
parser.add_argument(
            "--thread",
            help    = "use threading to branch in parallel",
            dest    = 'thread',
            action  = 'store_true',
            default = False)
parser.add_argument(
            "--inNode",
            help    = "perform in-node implicit parallelization",
            dest    = 'inNode',
            action  = 'store_true',
            default = False)

def _mapper_dir_contains_factory(glob: str) -> Callable[[Path], bool]:
    """
    Creates a function suitable for use with a ``PathMapper``.
    That function returns true if its path argument is a directory
    containing a file which matches the given glob.
    """

    def _dir_contains(path: Path) -> bool:
        if not path.is_dir():
            return False
        match = path.glob(glob)
        return next(match, None) is not None

    return _dir_contains


def ground_prep(options: Namespace, inputdir: Path, outputdir: Path):
    '''
    Perform some setup and initial LOG output
    '''
    global Env, LOG, LLD, PLinputFilter
    Env.inputdir        = str(inputdir)
    Env.outputdir       = str(outputdir)

    PLinputFilter       = action.PluginRun(     env = Env, options = options)
    LOG                 = logger.debug

    LOG("Starting growth cycle...")

    LOG("plugin arguments...")
    for k,v in options.__dict__.items():
         LOG("%25s:  [%s]" % (k, v))
    LOG("")

    LOG("base environment...")
    for k,v in os.environ.items():
         LOG("%25s:  [%s]" % (k, v))
    LOG("")

    LOG("inputdir  = %s" % str(inputdir))
    LOG("outputdir = %s" % str(outputdir))

    if len(options.pluginInstanceID):
        Env.parentPluginInstanceID  = options.pluginInstanceID
    else:
        Env.parentPluginInstanceID  = Env.parentPluginInstanceID_discover()['parentPluginInstanceID']

def tree_grow(options: Namespace, input: Path, output: Path = None) -> dict:
    '''
    Based on some conditional of the <input> direct the
    dynamic "growth" of this feed tree from the parent node
    of *this* plugin.
    '''
    global Env, PLinputFilter, LLD, LOG

    LLD                     = action.LLDcomputeflow(env = Env, options = options)
    conditional             = behavior.Filter()
    conditional.obj_pass    = behavior.unconditionalPass

    pudb.set_trace()
    LOG("Growing a tree off new data root %s..." % str(input))
    if conditional.obj_pass(str(input)):
        LOG("Tree planted off %s" % str(input))
        d_nodeInput         = PLinputFilter(str(input))
        if d_nodeInput['status']:
            d_LLDflow       = LLD(  d_nodeInput['branchInstanceID'])
        else:
            LOG("Some error was returned from the node analysis!",  comms = 'error')
            LOG('stdout: %s' % d_nodeInput['run']['stdout'],        comms = 'error')
            LOG('stderr: %s' % d_nodeInput['run']['stderr'],        comms = 'error')
            LOG('return: %s' % d_nodeInput['run']['returncode'],    comms = 'error')

# documentation: https://fnndsc.github.io/chris_plugin/chris_plugin.html#chris_plugin
@chris_plugin(
    parser              = parser,
    title               = 'Leg-Length Discrepency - Dynamic Compute Flow',
    category            = '',               # ref. https://chrisstore.co/plugins
    min_memory_limit    = '100Mi',          # supported units: Mi, Gi
    min_cpu_limit       = '1000m',          # millicores, e.g. "1000m" = 1 CPU core
    min_gpu_limit       = 0                 # set min_gpu_limit=1 to enable GPU
)
def main(options: Namespace, inputdir: Path, outputdir: Path):
    """
    :param options: non-positional arguments parsed by the parser given to @chris_plugin
    :param inputdir: directory containing input files (read-only)
    :param outputdir: directory where to write output files
    """

    print(DISPLAY_TITLE)

    set_trace(term_size=(253, 62), host = '0.0.0.0', port = 7900)

    global Env, PFMlogger, LOG, CAW, PLinputFilter
    ground_prep(options, inputdir, outputdir)
    if len(Env.parentPluginInstanceID):
        LOG("Sewing seeds...")
        Path('%s/start.touch' % str(outputdir)).touch()
        output = None

        if int(options.thread):
            with ThreadPoolExecutor(max_workers=len(os.sched_getaffinity(0))) as pool:
                if not options.inNode:
                    mapper  = PathMapper.file_mapper(inputdir, outputdir,
                                        globs       = [options.pattern])
                else:
                    # mapper  = PathMapper.file_mapper(inputdir, outputdir,
                    #                     glob        = options.pattern,
                    #                     filter      = _mapper_dir_contains_factory('*dcm'))
                    # mapper  = PathMapper.file_mapper(inputdir, outputdir,
                    #                     glob        = options.pattern,
                    #                     filter      = _mapper_dir_contains_factory(options.pattern))
                    mapper  = PathMapper.file_mapper(inputdir, outputdir,
                                        filter      = _mapper_dir_contains_factory('*dcm'))
                results = pool.map(lambda t: tree_grow(options, *t), mapper)
        else:
            for input, output in mapper:
                tree_grow(options, input, output)

    LOG("Ending growth cycle...")


if __name__ == '__main__':
    main()
