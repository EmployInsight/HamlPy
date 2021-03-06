# haml-watcher.py
# Author: Christian Stefanescu (st.chris@gmail.com)
#
# Watch a folder for files with the given extensions and call the HamlPy
# compiler if the modified time has changed since the last check.
from time import gmtime, strftime
import argparse
import sys
import codecs
import os
import os.path
import time
import hamlpy
import nodes as hamlpynodes

try:
    str = unicode
except NameError:
    pass

class Options(object):
    CHECK_INTERVAL = 3  # in seconds
    DEBUG = False  # print file paths when a file is compiled
    VERBOSE = False
    OUTPUT_EXT = '.html'

# dict of compiled files [fullpath : timestamp]
compiled = dict()

class StoreNameValueTagPair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tags = getattr(namespace, 'tags', {})
        if tags is None:
            tags = {}
        for item in values:
            n, v = item.split(':')
            tags[n] = v

        setattr(namespace, 'tags', tags)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-v', '--verbose', help = 'Display verbose output', action = 'store_true')
arg_parser.add_argument('-i', '--input-extension', metavar = 'EXT', default = '.hamlpy', help = 'The file extensions to look for', type = str, nargs = '+')
arg_parser.add_argument('-ext', '--extension', metavar = 'EXT', default = Options.OUTPUT_EXT, help = 'The output file extension. Default is .html', type = str)
arg_parser.add_argument('-r', '--refresh', metavar = 'S', default = Options.CHECK_INTERVAL, help = 'Refresh interval for files. Default is {} seconds'.format(Options.CHECK_INTERVAL), type = int)
arg_parser.add_argument('input_dir', help = 'Folder to watch', type = str)
arg_parser.add_argument('output_dir', help = 'Destination folder', type = str, nargs = '?')
arg_parser.add_argument('--tag', help = 'Add self closing tag. eg. --tag macro:endmacro', type = str, nargs = 1, action = StoreNameValueTagPair)
arg_parser.add_argument('--attr-wrapper', dest='attr_wrapper', type=str, choices=('"', "'"), default="'", action='store', help="The character that should wrap element attributes. This defaults to ' (an apostrophe).")

def watched_extension(extension):
    """Return True if the given extension is one of the watched extensions"""
    for ext in hamlpy.VALID_EXTENSIONS:
        if extension.endswith('.' + ext):
            return True
    return False

def watch_folder():
    """Main entry point. Expects one or two arguments (the watch folder + optional destination folder)."""
    argv = sys.argv[1:] if len(sys.argv) > 1 else []
    args = arg_parser.parse_args(sys.argv[1:])
    args_dict = args.__dict__

    input_folder = os.path.realpath(args_dict.pop('input_dir'))
    output_folder = args_dict.pop('output_dir', None)
    refresh_interval = args_dict.pop('refresh')
    if not output_folder:
        output_folder = input_folder
    else:
        output_folder = os.path.realpath(output_folder )

    if args_dict.pop('verbose'):
        Options.VERBOSE = True
        print "Watching {} at refresh interval {} seconds".format(input_folder, refresh_interval)

    extension = args_dict.pop('extension')
    if extension:
        Options.OUTPUT_EXT = extension

    tags = args_dict.pop('tag')
    if tags:
        hamlpynodes.TagNode.self_closing.update(tags)

    input_extension = args_dict.pop('input_extension')
    if input_extension:
        hamlpy.VALID_EXTENSIONS += input_extension

    while True:
        try:
            _watch_folder(input_folder, output_folder, args_dict)
            time.sleep(refresh_interval)
        except KeyboardInterrupt:
            # allow graceful exit (no stacktrace output)
            sys.exit(0)

def _watch_folder(folder, destination, args_dict):
    """Compares "modified" timestamps against the "compiled" dict, calls compiler
    if necessary."""
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            # Ignore filenames starting with ".#" for Emacs compatibility
            if watched_extension(filename) and not filename.startswith('.#'):
                fullpath = os.path.join(dirpath, filename)
                subfolder = os.path.relpath(dirpath, folder)
                mtime = os.stat(fullpath).st_mtime

                # Create subfolders in target directory if they don't exist
                compiled_folder = os.path.join(destination, subfolder)
                if not os.path.exists(compiled_folder):
                    os.makedirs(compiled_folder)

                compiled_path = _compiled_path(compiled_folder, filename)
                if (not fullpath in compiled or
                    compiled[fullpath] < mtime or
                    not os.path.isfile(compiled_path)):
                    compile_file(fullpath, compiled_path, args_dict)
                    compiled[fullpath] = mtime

def _compiled_path(destination, filename):
    return os.path.join(destination, filename[:filename.rfind('.')] + Options.OUTPUT_EXT)

def compile_file(fullpath, outfile_name, args_dict):
    """Calls HamlPy compiler."""
    if Options.VERBOSE:
        print '%s %s -> %s' % (strftime("%H:%M:%S", gmtime()), fullpath, outfile_name)
    try:
        if Options.DEBUG:
            print "Compiling %s -> %s" % (fullpath, outfile_name)
        haml_lines = codecs.open(fullpath, 'r', encoding = 'utf-8').read().splitlines()
        compiler = hamlpy.Compiler(args_dict)
        output = compiler.process_lines(haml_lines)
        outfile = codecs.open(outfile_name, 'w', encoding = 'utf-8')
        outfile.write(output)
    except Exception, e:
        # import traceback
        print "Failed to compile %s -> %s\nReason:\n%s" % (fullpath, outfile_name, e)
        # print traceback.print_exc()

if __name__ == '__main__':
    watch_folder()
