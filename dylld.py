#!/usr/bin/env python

from    pathlib                 import Path
from    argparse                import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter

from    chris_plugin            import chris_plugin, PathMapper

from    pathlib                 import Path

from    io                      import TextIOWrapper
import  os, sys
import  pudb
from    pudb.remote             import set_trace

from    loguru                  import logger
from    concurrent.futures      import ThreadPoolExecutor, ProcessPoolExecutor
from    threading               import current_thread, get_native_id

from    typing                  import Callable

from    datetime                import datetime, timezone
import  json

from    state                   import data
from    logic                   import behavior
from    control                 import action
from    control.filter          import PathFilter


LOG             = logger.debug

logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<yellow>{name: >28}</yellow>::"
    "<cyan>{function: <30}</cyan> @"
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)
logger.remove()
logger.add(sys.stderr, format=logger_format)

pluginInputDir:Path     = None
pluginOutputDir:Path    = None
ld_forestResult:list    = []

__version__ = '4.2.4'

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


parser: ArgumentParser      = ArgumentParser(
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
            '--CUBEurl',
            default = 'http://localhost:8000/api/v1/',
            help    = 'CUBE URL'
)
parser.add_argument(
            '--CUBEuser',
            default = 'chris',
            help    = 'CUBE/ChRIS username'
)
parser.add_argument(
            '--CUBEpassword',
            default = 'chris1234',
            help    = 'CUBE/ChRIS password'
)
parser.add_argument(
            '--orthancURL',
            default = 'https://orthanc-chris-public.apps.ocp-prod.massopen.cloud/',
            help    = 'IP of the orthanc to receive analysis results'
)
parser.add_argument(
            '--orthancuser',
            default = 'fnndsc',
            help    = 'Orthanc username'
)
parser.add_argument(
            '--orthancpassword',
            default = 'Lerkyacyids5',
            help    = 'Orthanc password'
)
parser.add_argument(
            '--orthancremote',
            default = '',
            help    = 'remote orthanc modality'
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
            default = False
)
parser.add_argument(
            "--inNode",
            help    = "perform in-node implicit parallelization in conjunction with --thread",
            dest    = 'inNode',
            action  = 'store_true',
            default = False
)
parser.add_argument(
            "--debug",
            help    = "if true, toggle telnet pudb debugging",
            dest    = 'debug',
            action  = 'store_true',
            default = False
)
parser.add_argument(
            "--debugTermSize",
            help    = "the terminal 'cols,rows' size for debugging",
            default = '253,62'
)
parser.add_argument(
            "--debugPort",
            help    = "the debugging telnet port",
            default = '7900'
)
parser.add_argument(
            "--debugHost",
            help    = "the debugging telnet host",
            default = '0.0.0.0'
)

def Env_setup(  options         : Namespace,
                inputdir        : Path,
                outputdir       : Path,
                debugPortOffset : int = 0) -> data.env:
    """
   Setup the environment

    Args:
        options (Namespace):    options passed from the CLI caller
        inputdir (Path):        plugin global input directory
        outputdir (Path):       plugin global output directory
        debugPortOffset (int, optional): offset added to debug port -- useful for multithreading. Defaults to 0.

    Returns:
        data.env: _description_
    """
    Env: data.env           = data.env()
    Env.CUBE.inputdir       = str(inputdir)
    Env.CUBE.outputdir      = str(outputdir)
    Env.CUBE.url            = str(options.CUBEurl)
    Env.CUBE.user           = str(options.CUBEuser)
    Env.CUBE.password       = str(options.CUBEpassword)
    Env.orthanc.url         = str(options.orthancURL)
    Env.orthanc.username    = str(options.orthancuser)
    Env.orthanc.password    = str(options.orthancpassword)
    Env.inputdir            = inputdir
    Env.outputdir           = outputdir
    Env.debug_setup(    debug       = options.debug,
                        termsize    = options.debugTermSize,
                        port        = int(options.debugPort) + debugPortOffset,
                        host        = options.debugHost
    )
    return Env

def preamble_show(options: Namespace) -> None:
    """
    Just show some preamble "noise" in the output terminal
    """

    print(DISPLAY_TITLE)

    LOG("plugin arguments...")
    for k,v in options.__dict__.items():
         LOG("%25s:  [%s]" % (k, v))
    LOG("")

    LOG("base environment...")
    for k,v in os.environ.items():
         LOG("%25s:  [%s]" % (k, v))
    LOG("")

    LOG("Starting growth cycle...")

def ground_prep(options: Namespace, Env : data.env) -> action.PluginRun:
    """
    Do some per-tree setup -- prepare the ground!

    Args:
        options (Namespace): options namespace
        Env (data.env): the environment for this tree

    Returns:
        action.PluginRun: A filter specific to this tree that will
                          filter a study of interest in the parent
                          space -- analogously akin to choosing a
                          seed.
    """

    LOG("Prepping ground for tree in thread %s..." % get_native_id())
    LOG("Constructing object to filter parent field")
    PLinputFilter: action.PluginRun = action.PluginRun(env = Env, options = options)

    if len(options.pluginInstanceID):
        Env.CUBE.parentPluginInstanceID  = options.pluginInstanceID
    else:
        Env.CUBE.parentPluginInstanceID  = \
            Env.CUBE.parentPluginInstanceID_discover()['parentPluginInstanceID']
    return PLinputFilter

def replantSeed_catchError(PLseed:action.PluginRun, input: Path) -> dict:
    """
    Re-run a failed filter (pl-shexec) with explicit error catching

    Args:
        PLseed (action.Pluginrun): the plugin run object to re-execute
        input (Path): the input on which the seed failed

    Returns:
        dict: the detailed error log from the failed run
    """
    global  LOG
    LOG("Some error was returned when planting the seed!")
    LOG('Replanting seed with error catching on...')
    d_seedreplant:dict  = PLseed(str(input), append = "--jsonReturn")
    return d_seedreplant

def tree_grow(options: Namespace, input: Path, output: Path = None) -> dict:
    """
    Based on some conditional applied to the <input> file space, direct the
    dynamic "growth" of this feed tree from the parent node of *this* plugin.

    Args:
        options (Namespace): CLI options
        input (Path): input path returned by mapper
        output (Path, optional): ouptut path returned by mapper. Defaults to None.

    Returns:
        dict: resulant object dictionary of this (threaded) growth
    """
    global pluginInputDir, pluginOutputDir, LOG, ld_forestResult

    Env:data.env = Env_setup(
                        options,
                        pluginInputDir,
                        pluginOutputDir,
                        get_native_id()
                    )
    Env.set_telnet_trace_if_specified()

    timenow:Callable[[], str]       = lambda: datetime.now(timezone.utc).astimezone().isoformat()
    conditional:behavior.Filter     = behavior.Filter()
    conditional.obj_pass            = behavior.unconditionalPass
    PLinputFilter:action.PluginRun  = ground_prep(options, Env)
    LLD:action.LLDcomputeflow       = action.LLDcomputeflow(env = Env, options = options)
    str_threadName:str              = current_thread().getName()
    d_seedGet:dict                  = {
        "status"    : False,
        "message"   : "unable to plant seed"
    }
    d_treeGrow:dict                 = {
        "status"    : False,
        "message"   : "unable to grow tree"
    }
    d_ret:dict                      = {
        "seed"      : {},
        "tree"      : {}
    }

    Path('%s/start-%s.touch' % (Env.outputdir.touch(), str_threadName))
    LOG("Growing a new tree in thread %s..." % str_threadName)
    str_heartbeat:str               = str(Env.outputdir.joinpath('heartbeat-%s.log' % \
                                            str_threadName))
    fl:TextIOWrapper                = open(str_heartbeat, 'w')
    fl.write('Start time: {}\n'.format(timenow()))
    if conditional.obj_pass(str(input)):
        LOG("Planting seed off %s" % str(input))
        d_seedGet                   = PLinputFilter(str(input))
        if d_seedGet['status']:
            d_treeGrow              = LLD(d_seedGet['branchInstanceID'])
        else:
            d_seedGet['failed']     = replantSeed_catchError(PLinputFilter, input)
    fl.write('End   time: {}\n'.format(timenow()))
    fl.close()
    d_ret['seed']       = d_seedGet
    d_ret['tree']       = d_treeGrow
    ld_forestResult.append(d_ret)
    return d_ret

def treeGrowth_savelog(outputdir : Path) -> None:
    """
    Write the global log file on the tree growth to the passed
    <outputdir>

    Args:
        outputdir (Path): the plugin base output directory
    """
    global ld_forestResult

    with open(str(outputdir.joinpath('treeLog.json')), 'w') as f:
        f.write(json.dumps(ld_forestResult, indent=4))
    f.close()

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
    global pluginInputDir, pluginOutputDir
    pluginInputDir  = inputdir
    pluginOutputDir = outputdir

    # set_trace(term_size=(253, 62), host = '0.0.0.0', port = 7900)

    preamble_show(options)

    output: None = None
    if not options.inNode:
        mapper  = PathMapper.file_mapper(
                            inputdir,
                            outputdir,
                            glob        = options.pattern
                        )
    else:
        mapper  = PathMapper.dir_mapper_deep(
                            inputdir,
                            outputdir
                        )
    if int(options.thread):
        with ThreadPoolExecutor(max_workers=len(os.sched_getaffinity(0))) as pool:
            results = pool.map(lambda t: tree_grow(options, *t), mapper)
    else:
        for input, output in mapper:
            results: dict = tree_grow(options, input, output)

    LOG("Ending growth cycle...")
    treeGrowth_savelog(outputdir)

if __name__ == '__main__':
    main()
