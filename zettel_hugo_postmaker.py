#!/usr/bin/env python

import logging
import pathlib
import configargparse
import sys
import os
import stat
import time
from sultan.api import Sultan
import regex

# Configure logging early
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(funcName)s():%(lineno)i:        %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def parse_config():
    default_config = pathlib.Path(__file__).stem + '.ini'
    config = configargparse.ArgParser(default_config_files=[default_config])
    config.add_argument('-c', '--config', is_config_file=True,
                        help='Specify path to Configuration file. Default is {0}.ini'.format(
                            pathlib.Path(__file__).stem), metavar='CONFIG'
                        )
    config.add_argument('-v', '--verbosity', action='store',
                        help='Specify logging level for script. Default is %(default)s.',
                        choices=['warning', 'info', 'debug'],
                        default='warning')
    config.add_argument('-f', '--file', action='store',
                        help='Write log messages to a file', metavar='LOGFILE')
    config.add_argument('--source_files', action='store',
                        help='Specify path to directory containing source markdown files. Default is to use a '
                             '\'source\' folder in the current directory. '
                             'Spaces are allowed in paths. Use double quotes for paths with spaces when specifying '
                             'paths on the command line only. The script will handle paths with spaces in the config '
                             'file automatically. ',
                        default=pathlib.Path.joinpath(pathlib.Path(__file__).parent, 'source'),
                        metavar='DIRECTORY')
    config.add_argument('--target_files', action='store',
                        help='Specify path to posts directory in Hugo site where processed markdown files should be '
                             'saved. This parameter must be specified. '
                             'Spaces are allowed in paths.  Use double quotes for paths with spaces when specifying '
                             'paths on the command line only. The script will handle paths with spaces in the config '
                             'file automatically. ',
                        required=True, metavar='DIRECTORY')
    config.add_argument('--images', action='store',
                        help='Specify whether pandoc should extract and rewrite linked images. Default is %(default)s.',
                        choices=['yes', 'no'],
                        default='no')
    config.add_argument('--images_in', action='append',
                        help='Specify path(s) to directories where images linked in source markdown files are saved. '
                             'Use double quotes for paths with spaces when specifying '
                             'paths on the command line only. The script will handle paths with spaces in the config '
                             'file automatically. This parameter can specified multiple times to include different '
                             'directories and must be specified if the --images parameter is set to "yes". Path '
                             'specified must be for the parent folder to where images are saved. For example if '
                             'images are saved in /my/images/folder/ (and the image link in the source Markdown file '
                             'is ![](./folder/my.jpg) then this parameter should be specified as /my/images/.',
                        metavar='DIRECTORY')
    config.add_argument('--images_out', action='store',
                        help='Specify path to directory where pandoc will store images after extracting them from the '
                             'source markdown files. Images will be saved with a filename equal to the file '
                             'SHA. The path specified here should be relative to the Hugo site URL - for example /img '
                             'if images are served from an img folder on the Hugo site. The script will set the '
                             'images path after extraction based on the name of the last folder in the path. For '
                             'example, if the parameter is set to /my/hugo/images/, the path for images will be set to '
                             '/images/. It is recommended to create a symlink in the same partition as the target '
                             'directory for markdown files for this purpose. This parameter must be specified if the '
                             '--images parameter is set to "yes". ',
                        metavar='DIRECTORY')
    config.add_argument('--filters', action='append',
                        help='Specify pandoc LUA filter names that should be included when running pandoc. This '
                             'parameter can specified multiple times to include different filters - note that pandoc '
                             'processes filters in sequence, so the order is important! The script is configured such '
                             'that pandoc will look for filters in the target directory for markdown files and the '
                             'pandoc user directory only.', metavar='FILE')
    config.add_argument('--cite', action='store_true',
                        help='Specify whether pandoc should process citation references in source Markdown files. Set '
                             'to TRUE by default and requires --bib and --csl parameters to be supplied as well.',
                        required=True)
    config.add_argument('--bib', action='store',
                        help='Specify path to Bibiliography file that should be used by pandoc for looking up '
                             'citations. Use double quotes for paths with spaces when specifying '
                             'paths on the command line only. The script will handle paths with spaces in the config '
                             'file automatically. ', metavar='FILE')
    config.add_argument('--csl', action='store',
                        help='Specify path to Citation Language Style file that should be used by pandoc when '
                             'formatting citations. Use double quotes for paths with spaces when specifying '
                             'paths on the command line only. The script will handle paths with spaces in the config '
                             'file automatically. ', metavar='FILE')
    config.add_argument('--metafile', action='store',
                        help='Optional path to file containing additional metadata in YAML format that should be '
                             'included in every markdown file while being processed in pandoc. Use double quotes for '
                             'paths with spaces when specifying paths on the command line only. The script will '
                             'handle paths with spaces in the config file automatically. ', metavar='FILE')
    config.add_argument('-p', '--process', action='store',
                        help='Determine whether to process all source files or only recently modified files. Default '
                             'is %(default)s.',
                        choices=['all', 'modified'],
                        default='all')
    config.add_argument('-m', '--modified', action='store', type=int,
                        help='Specify in minutes what is the time limit for recently modified files. Default is '
                             '%(default)s.',
                        default=60, metavar='MINUTES')

    options = config.parse_known_args()
    # Convert tuple of parsed arguments into a dictionary. There are two values within this tuple.
    # [0] represents recognized arguments. [1] represents unrecognized arguments on command-line or config file.
    option_values = vars(options[0])
    # Assign dictionary values to variables.
    config_file = option_values.get('config')
    source_files = option_values.get('source_files')
    target_files = option_values.get('target_files')
    process_images = option_values.get('images')
    img_inputs = option_values.get('images_in')
    img_output = option_values.get('images_out')
    filters = option_values.get('filters')
    citations = option_values.get('cite')
    bib_file = option_values.get('bib')
    csl_file = option_values.get('csl')
    metafile = option_values.get('metafile')
    logging_level = option_values.get('verbosity')
    log_file = option_values.get('file')
    process_type = option_values.get('process')
    modified_time = option_values.get('modified')

    # Reset logging levels as per config
    logger = logging.getLogger()
    logger.setLevel(logging_level.upper())

    # Configure file-based logging
    if log_file is None:
        logging.info('No log file set. All log messages will print to Console only')
    else:
        filelogger = logging.FileHandler('{0}'.format(log_file))
        filelogformatter = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(funcName)s():%(lineno)i:        %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        filelogger.setFormatter(filelogformatter)
        logger.addHandler(filelogger)
        logging.info('Outputting to log file')

    # Check if specified config file exists else bail
    if config_file is None:
        config_file = default_config
        logging.debug('No configuration file specified. Using the default configuration file {}'.format(default_config))
    elif pathlib.Path(config_file).exists():
        logging.debug('Found configuration file %s', config_file)
    else:
        logging.exception('Did not find the specified configuration file {}'.format(config_file))
        raise FileNotFoundError

    # Check if somehow modified_time is set to NIL when processing modified files.
    if process_type == 'modified' and not modified_time:
        raise ValueError('Script is set to process only recently modified files. But the modified time parameter is '
                         'incorrectly defined.')

    return config_file, source_files, target_files, process_images, img_inputs, img_output, filters, citations, \
           bib_file, csl_file, metafile, log_file, process_type, modified_time


def output_dir(target):
    """
    This function will check for the presence of a 'resources' directory,
    which will be used later in the script to store the output from pandoc.

    :param target: Path to directory within Hugo where processed markdown files are to be stored.
    :return: Path to resource directory where intermediate markdown files should be stored.
    """
    temp_dir = pathlib.Path.joinpath(pathlib.Path(target).parents[1], 'resources')
    if pathlib.Path(temp_dir).exists():
        logging.debug('Found directory for storing temporary files')
    else:
        print('Did not find the directory {} to store temporary output files. Will try create it now'.
              format(temp_dir))
        pathlib.Path(temp_dir).mkdir(exist_ok=True)

    return temp_dir


def check_dirs(source_dir, target_dir, process_images, img_input_dir, img_output_dir):
    """
    Function to check if specified directories exist. The function will create the destination directory if it does
    exist.

    :param source_dir: Directory containing markdown files to be processed.
    :param target_dir: Directory to store markdown files after they are processed.
    :param process_images: Flag for whether images should be processed by the script
    :param img_input_dir: Directory path(s) where images linked in source markdown files are stored.
    :param img_output_dir: Directory to store images after they are extracted from source markdown files.
    :return: Path to directory where temporary output file from run_pandoc() should be stored.
    """
    if pathlib.Path(source_dir).exists():
        pass
    elif source_dir == str(pathlib.Path.joinpath(pathlib.Path(__file__).parent, 'source')) and pathlib.Path(
            source_dir).exists():
        print('No source directory found in specified configuration file. Using default {} instead'.format(source_dir))
    else:
        logging.exception('Did not find the directory {}'.format(source_dir))
        raise NotADirectoryError

    if pathlib.Path(target_dir).exists():
        temp_dir = output_dir(target_dir)
    else:
        print('Did not find the target directory {}. Will try create it now'.format(target_dir))
        pathlib.Path(target_dir).mkdir(exist_ok=True)
        temp_dir = output_dir(target_dir)
        # exist_ok=True will function like mkdir -p so there is no need to wrap this in a try-except block.

    if process_images == 'yes':
        for input_dir in (img_input_dir[0].split(',')):
            if pathlib.Path(input_dir).exists():
                pass
            else:
                logging.exception('Did not find the source image directory {}'.format(input_dir))
                raise NotADirectoryError

    if process_images == 'yes' and sys.platform != 'win32':
        # Checking for symlinks is unfortunately not consistent across OS'es so we have to make separate checks
        # per-platform. The is_symlink check should work on any UNIX-y platform.
        if pathlib.Path(img_output_dir).exists() and pathlib.Path(img_output_dir).is_symlink():
            logging.debug('Target directory for storing extracted images is a symlink, which is ideal.')
        elif pathlib.Path(img_output_dir).exists():
            logging.warning('Image output directory exists but is an actual directory and not a symlink. This can '
                            'result in broken links within processed Markdown files')
        else:
            logging.exception('Did not find the directory {}'.format(img_output_dir))
            raise NotADirectoryError
        if pathlib.Path(target_dir).root == pathlib.Path(img_output_dir).root:
            logging.info('Target partition for processed markdown files and images is the same, which is ideal.')
        else:
            logging.warning('Processed markdown files and extracted images are not being stored in the same '
                            'partition. This can result in broken links within processed Markdown files.')
    elif process_images == 'yes' and sys.platform == 'win32':
        # noinspection PyUnresolvedReferences
        if (pathlib.Path(img_output_dir).exists() and
            pathlib.Path(img_output_dir).lstat().st_file_attributes == stat.FILE_ATTRIBUTE_REPARSE_POINT) \
                or \
                (pathlib.Path(img_output_dir).exists() and
                 pathlib.Path(img_output_dir).lstat().st_file_attributes == 1040):
            # Python docs (https://docs.python.org/3/library/stat.html#module-stat) state that st_file_attributes for
            # junction links/directory links on Windows should be equal to FILE_ATTRIBUTE_REPARSE_POINT (1024).
            # However, an empirical test shows that on Windows 10 (using ReFS instead of NTFS?),
            # st_file_attributes returns a different value for junction links/directory links and so we add an extra
            # 'magic value' check.
            logging.debug('Target directory for storing extracted images exists and is a symlink, which is ideal.')
        elif pathlib.Path(img_output_dir).exists():
            logging.warning('Image output directory exists but is an actual directory and not a symlink. This can '
                            'result in broken links within processed Markdown files')
        else:
            logging.exception('Did not find the directory %s', img_output_dir)
            raise NotADirectoryError
        if pathlib.Path(target_dir).root == pathlib.Path(img_output_dir).root:
            logging.info('Target partition for processed markdown files and images is the same, which is ideal.')
        else:
            logging.warning('Processed markdown files and extracted images are not being stored in the same '
                            'partition. This can result in broken links within processed Markdown files.')
    elif process_images == 'no':
        logging.debug('Skipping image processing checks.')
    else:
        logging.exception('Invalid parameter value for processing images')
        raise ValueError

    return temp_dir


def check_files(filters, bibfile, cslfile, metafile):
    """
    Function to check if specified files exist.

    :param filters: List of LUA filters to be included when running pandoc.
    :param bibfile: Path to bibliography file.
    :param cslfile: Path to Citation Language Style file.
    :param metafile: Path to YAML file containing optional additional metadata.
    :return: None
    """
    filelist = [bibfile, cslfile]

    if filters is not None:
        logging.warning('Filters have been specified. However the script does not check if these filters are actually '
                        'available in the default locations used by pandoc.')

    if metafile is not None and pathlib.Path(metafile).exists():
        logging.debug('Found input file {}'.format(metafile))
    elif metafile is not None and pathlib.Path(metafile).exists() is not True:
        logging.exception('Did not find the specified input file {}'.format(metafile))
        raise FileNotFoundError
    elif metafile is None:
        logging.debug('Skipping checks for metadata file as it not specified.')

    for file in filelist:
        if pathlib.Path(file).exists():
            logging.debug('Found input file {}'.format(file))
        else:
            logging.exception('Did not find the specified input file {}'.format(file))
            raise FileNotFoundError
    return None


def run_pandoc(file, process_images, img_input_dir, img_output_dir, filters, bibfile, cslfile, metafile, temp_dir,
               target_dir):
    """
    Function to process markdown files in the source directory with pandoc to add complete citations and optionally
    extract & rewrite images and/or add additional YAML metadata.

    :param file: Input markdown file to be processed by pandoc. Will be supplied by process_files() in a loop.
    :param process_images: Flag for whether images should be processed by the script
    :param img_input_dir: Directory path(s) where images linked in source markdown files are stored.
    :param img_output_dir: Directory to store images after they are extracted from source markdown files.
    :param filters: List of Pandoc LUA filters to be included when running pandoc.
    :param bibfile: Path to bibliography file.
    :param cslfile: Path to Citation Language Style file.
    :param metafile: Path to YAML file containing optional additional metadata.
    :param temp_dir:  Path to directory where temporary output file should be stored.
    :param target_dir: Directory to store markdown files after they are processed.
    :return: Complete path to intermediate output file in Multi-Markdown format generated by pandoc.
    """

    # Generate pandoc filter list based on availability of filter parameter.
    filterlist = None
    if filters is not None:
        filterlist = ''.join([' --lua-filter="{}"'.format(value) for value in filters[0].split(',')])
    else:
        logging.debug('Skipping filter parameters since no filters have been defined.')

    # We cannot use the same approach that we use for filters to get the list of resource paths for images, i.e:
    # img_inputdir_list = ''.join([' --resource-path=.;{}'.format(value) for value in img_input_dir[0].split(',')])
    # Multiple invocations of --resource-path will result in only the last directory being considered. In addition
    # to specify fully quoted paths, we must use escaped slash characters in Windows.
    # This requires a OS-specific approach due to path separator & environment separator differences.
    img_inputdir = None
    if process_images == 'yes' and sys.platform != 'win32':
        img_input_dir[:] = [i.replace(',', ':"') for i in img_input_dir]
        img_inputdir_list = img_input_dir[0]
        img_inputdir_str = ' --resource-path=.:"' + img_inputdir_list
        img_inputdir_str = img_inputdir_str.replace('/:', '/":')
        img_inputdir = img_inputdir_str + '"'
    elif process_images == 'yes' and sys.platform == 'win32':
        img_input_dir[:] = [i.replace(',', ';"') for i in img_input_dir]
        img_inputdir_list = img_input_dir[0]
        img_inputdir_str = ' --resource-path=.;"' + img_inputdir_list
        img_inputdir_str = img_inputdir_str.replace('\\', '\\\\')
        img_inputdir_str = img_inputdir_str.replace('\\\\;', '\\\\";')
        img_inputdir = img_inputdir_str + '"'
    elif process_images == 'no':
        logging.debug('Skipping image input directories parameter since images processing is set to no.')

    metadata_file = None
    if metafile is not None:
        metafile_str = metafile.replace('\\', '\\\\')
        metadata_file = '--metadata-file="' + metafile_str + '"'
    else:
        logging.debug('Skipping additional metadata file parameter since no input file has been specified.')

    img_output_path = None
    if process_images == 'yes':
        img_output_name = pathlib.Path(img_output_dir).name
        img_output_path = '--extract-media=/' + img_output_name
    elif process_images == 'no':
        logging.debug('Skipping image output directories parameter since images processing is set to no.')

    bibfile_str = bibfile.replace('\\', '\\\\')
    cslfile_str = cslfile.replace('\\', '\\\\')
    inputfile_str = str(file)
    inputfile_str = inputfile_str.replace('\\', '\\\\')
    bibliography = '--bibliography="' + bibfile_str + '"'
    csl = '--csl="' + cslfile_str + '"'
    inputfile = '"' + inputfile_str + '"'
    # os.remove('outfile.md')
    # pathlib.Path.unlink(pathlib.Path.joinpath(temp_dir, 'outfile.md'))
    tempdir_str = str(temp_dir)
    tempdir_str = tempdir_str.replace('\\', '\\\\')
    outfile = '-o ' + '"' + tempdir_str + "\\" + 'outfile.md"'

    # This is not a recommended practice, but pandoc needs to be running in the eventual output folder for image
    # extraction to work reliably.
    os.chdir(target_dir)

    # Run pandoc for different combinations of process_images, metadata_file & filter availability:

    logging.debug('Start processing {} with pandoc'.format(file))
    if process_images == 'yes' and metadata_file is not None and filterlist is not None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', img_inputdir, img_output_path, filterlist,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc', metadata_file,
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'yes' and metadata_file is not None and filterlist is None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', img_inputdir, img_output_path,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc', metadata_file,
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'yes' and metadata_file is None and filterlist is not None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', img_inputdir, img_output_path, filterlist,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc',
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'yes' and metadata_file is None and filterlist is None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', img_inputdir, img_output_path,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc',
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'no' and metadata_file is not None and filterlist is not None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', filterlist,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc', metadata_file,
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'no' and metadata_file is not None and filterlist is None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone',
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc', metadata_file,
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'no' and metadata_file is None and filterlist is not None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone', filterlist,
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc',
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    if process_images == 'no' and metadata_file is None and filterlist is None:
        with Sultan.load(logging=False) as s:
            result = s.pandoc(inputfile, '-f markdown', '--standalone',
                              '--wrap=preserve', '--markdown-headings=atx', '--citeproc',
                              '--metadata=suppress-bibliography', '-t markdown_mmd+yaml_metadata_block', bibliography,
                              csl, outfile).run()
            logging.debug('Pandoc command execution Status: {} and '.format(result.rc) +
                          'command output: {}'.format(result.stdout + result.stderr))

    # Due to a known bug with Sultan (https://github.com/aeroxis/sultan/issues/64), the output file could have ";"
    # appended to the filename on Windows. Hence, we will check for both variants before returning the output file name.
    tempfile = pathlib.Path.joinpath(temp_dir, 'outfile.md')
    if pathlib.Path(tempfile).exists():
        return tempfile
    elif pathlib.Path(pathlib.Path.joinpath(temp_dir, 'outfile.md;')).exists():
        tempfile = pathlib.Path.joinpath(temp_dir, 'outfile.md;')
        return tempfile
    else:
        logging.exception('Could not find the temporary output file {}'.format(tempfile))
        raise FileNotFoundError


def modify_links(file_obj):
    """
    Function will parse contents of intermediate output file generated by pandoc (opened in utf-8 mode) and modify
    standalone [[wikilinks]] with different combinations of escaped characters and in-line [[wikilinks]](wikilinks)
    (again with different combinations of escape characters) into Hugo link syntax using relref cross-references.

    :param file_obj: Path to file
    :return: String containing modified text. Newlines will be returned as '\\n' in the string.
    """

    file = file_obj
    logging.debug('Going to start processing {}.'.format(file))
    try:
        with open(file, encoding="utf8") as infile:
            content = infile.read()
            # Read the entire file as a single string
            firstpass = regex.sub(r'(?V1)'
                                  r'(?s)```.*?```(*SKIP)(*FAIL)(?-s)|(?s)`.*?`(*SKIP)(*FAIL)(?-s)'
                                  # Ignore fenced & inline code blocks. V1 engine allows in-line flags so we 
                                  # enable newline matching only here. 
                                  # r'|(\ {4}|\t).*(*SKIP)(*FAIL)      
                                  # We cannot support skipping code blocks beginning with 4 spaces/1 tab 
                                  # as pandoc conversion changes Note-Link-Janitor links to use 4 spaces. 
                                  r'|(\\\[\\\[(.*)\\\]\\\](?!\s\(|\())', r'[\2]({{< relref "\2.md" >}})', content)
            # Finds  references that are in style \[\[foo\]\] only by excluding links in style \[\[foo\]\](bar) or
            # \[\[foo\]\] (bar). Capture group $2 returns just foo
            secondpass = regex.sub(r'(?V1)'
                                   r'(?s)```.*?```(*SKIP)(*FAIL)(?-s)|(?s)`.*?`(*SKIP)(*FAIL)(?-s)'
                                   # Ignore fenced & inline code blocks. V1 engine allows in-line flags so we enable 
                                   # newline matching only here. 
                                   # r'|(\ {4}|\t).*(*SKIP)(*FAIL) 
                                   # We cannot support skipping code blocks beginning with 4 spaces/1 tab as pandoc 
                                   # conversion changes Note-Link-Janitor links to use 4 spaces. 
                                   r'|(\[\\\[(\d+)\\\]\])', r'[\2]', firstpass)
            # Finds references that are in style [\[123\]] only. Capture Group $2 returns just 123.
            thirdpass = regex.sub(r'(?V1)'
                                  r'(?s)```.*?```(*SKIP)(*FAIL)(?-s)|(?s)`.*?`(*SKIP)(*FAIL)(?-s)'
                                  # Ignore fenced & inline code blocks. V1 engine allows in-line flags so
                                  # we enable newline matching only here. 
                                  # r'|(\ {4}|\t).*(*SKIP)(*FAIL)'
                                  # We cannot support skipping code blocks beginning with 4 spaces/1 tab as pandoc  
                                  # conversion changes Note-Link-Janitor links to use 4 spaces.   
                                  r'|(\%20+(?=[^(\)]*\)))', r' ', secondpass)
            # Finds references that are in style (foo%20bar) only and changes it to (foo bar).
            fourthpass = regex.sub(r'(?V1)'
                                   r'(?s)```.*?```(*SKIP)(*FAIL)(?-s)|(?s)`.*?`(*SKIP)(*FAIL)(?-s)'
                                   # Ignore fenced & inline code blocks. V1 engine allows in-line flags so
                                   # we enable newline matching only here.
                                   # r'|(\ {4}|\t).*(*SKIP)(*FAIL)'
                                   # We cannot support skipping code blocks beginning with 4 spaces/1 tab as pandoc  
                                   # conversion changes Note-Link-Janitor links to use 4 spaces.   
                                   r'|(\[(\d+)\](\()(.*)(?=\))\))', r'[\2 \4]({{< relref "\2 \4.md" >}})', thirdpass)
            # Finds only references in style [123](bar). Capture group $2 returns 123 and capture
            # group $4 returns bar
            finalpass = regex.sub(r'(?V1)'
                                  r'(?s)```.*?```(*SKIP)(*FAIL)(?-s)|(?s)`.*?`(*SKIP)(*FAIL)(?-s)'
                                  # Ignore fenced & inline code blocks. V1 engine allows in-line flags so
                                  # we enable newline matching only here.
                                  # r'|(\ {4}|\t).*(*SKIP)(*FAIL)'
                                  # We cannot support skipping code blocks beginning with 4 spaces/1 tab as pandoc  
                                  # conversion changes Note-Link-Janitor links to use 4 spaces.   
                                  r'|(\\\[\\\[(\d+)\\\]\\\](\s\(|\()(.*)\))', r'[\2 \4]({{< relref "\2 \4.md" >}})',
                                  fourthpass)
            # Finds only references in style \[\[123\]\] (bar). Capture group $2 returns 123 and capture
            # group $4 returns bar
            # print(finalpass)
    except EnvironmentError:
        logging.exception('Unable to open file {} for reading'.format(file))
    logging.debug('Finished processing {}'.format(file))
    return finalpass


def write_file(file_contents, file, target_dir):
    """
    Function will take modified contents of file from modify_links() function and output to target directory. File
    extensions are preserved and file is written in utf-8 mode.

    :param file_contents: String containing modified text.
    :param file: Path to source file. Will be used to construct target file name.
    :param target_dir: Path to destination directory
    :return: Full path to file that was written to target directory.
    """

    name = pathlib.Path(file).name
    fullpath = pathlib.Path(target_dir).joinpath(name)
    logging.debug('Going to write file {} now.'.format(fullpath))
    try:
        with open(fullpath, 'w', encoding="utf8") as outfile:
            for item in file_contents:
                outfile.write("%s" % item)
    except EnvironmentError:
        logging.exception('Unable to write contents to {}'.format(fullpath))

    logging.debug('Finished writing file {} now.'.format(fullpath))
    return fullpath


def process_files(temp_dir, source_dir, target_dir, process_images, img_input_dir, img_output_dir, filters, bibfile,
                  cslfile,
                  metafile, process_type, modified_time):
    """
    Function to process input files. Will operate in a loop on all files (process "all")
    or recently modified files (process "modified")

    :param temp_dir:  Path to directory where temporary output file should be stored.
    :param source_dir: Path to directory containing source markdown files to be processed.
    :param target_dir: Path to directory where markdown files should be written to after processing.
    :param process_images: Flag for whether images should be processed by the script
    :param img_input_dir: Directory path(s) where images linked in source markdown files are stored.
    :param img_output_dir: Directory to store images after they are extracted from source markdown files.
    :param filters: List of Pandoc LUA filters to be included when running pandoc.
    :param bibfile: Path to bibliography file.
    :param cslfile: Path to Citation Language Style file.
    :param metafile: Path to YAML file containing optional additional metadata.
    :param process_type: Flag to process all or only modified files.
    :param modified_time: Time window for finding recently modified files.
    :return: Number of files processed.
    """
    count = 0

    if process_type == 'all':
        logging.info('Start processing all markdown files with .md extension in {}'.format(source_dir))
        for count, file in enumerate(pathlib.Path(source_dir).glob('*.md'), start=1):
            # We will not use iterdir() here since that will descend into sub-directories which may have
            # unexpected side-effects
            tempfile = run_pandoc(file, process_images, img_input_dir, img_output_dir, filters, bibfile, cslfile,
                                  metafile, temp_dir, target_dir)
            modified_text = modify_links(tempfile)
            write_file(modified_text, file, target_dir)
    elif process_type == 'modified':
        logging.info('Start processing recently modified markdown files with .md extension in {}'.format(source_dir))
        for count, file in enumerate(pathlib.Path(source_dir).glob('*.md'), start=1):
            if pathlib.Path(file).stat().st_mtime > time.time() - modified_time * 60:
                tempfile = run_pandoc(file, process_images, img_input_dir, img_output_dir, filters, bibfile, cslfile,
                                      metafile, temp_dir, target_dir)
                modified_text = modify_links(tempfile)
                write_file(modified_text, file, target_dir)
    logging.info('Finished processing all files in {}'.format(source_dir))

    return count


def main():
    start_time = time.perf_counter()
    parameters = parse_config()
    temp_dir = check_dirs(source_dir=str(parameters[1]), target_dir=str(parameters[2]),
                          process_images=str(parameters[3]),
                          img_input_dir=parameters[4], img_output_dir=str(parameters[5]))
    check_files(filters=parameters[6], bibfile=str(parameters[8]), cslfile=str(parameters[9]),
                metafile=parameters[10])
    count = process_files(temp_dir, source_dir=str(parameters[1]), target_dir=str(parameters[2]),
                          process_images=str(parameters[3]),
                          img_input_dir=parameters[4], img_output_dir=parameters[5], filters=parameters[6],
                          bibfile=str(parameters[8]), cslfile=str(parameters[9]), metafile=parameters[10],
                          process_type=str(parameters[12]), modified_time=parameters[13])
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    print('Script took {:02}:{:02}:{:02} (H:M:S)'.format(int(hours), int(minutes), int(seconds)), 'to process {0} files'
          .format(count))


if __name__ == '__main__':
    main()
