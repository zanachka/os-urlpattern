from __future__ import print_function
import sys
import os
import argparse
import logging
import json
import time
from os_urlpattern.utils import Counter
from logging.config import dictConfig
from os_urlpattern.pattern_maker import PatternMaker
from os_urlpattern.pattern_tree import PatternPathEncoder


def _config_logging(log_level):
    dictConfig(_DEFAULT_LOGGING)
    if log_level == 'NOTSET':
        handler = logging.NullHandler()
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.root.setLevel(logging.NOTSET)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logging.root.addHandler(handler)


class Command(object):
    def __init__(self, config):
        self._config = config
        self._logger = logging.getLogger(__name__)

    def add_argument(self, parser):
        parser.add_argument('-c', '--config',
                            help='config file',
                            action='store',
                            dest='config')

        parser.add_argument('-f', '--file',
                            help='file to be processed (default: stdin)',
                            action='store',
                            dest='file')

        parser.add_argument('-L', '--loglevel',
                            help='log level (default: NOTSET)',
                            default='NOTSET',
                            action='store',
                            dest='log_level',
                            choices=['NOTSET', 'DEBUG', 'INFO',
                                     'WARN', 'ERROR', 'FATAL'],
                            type=lambda s: s.upper())

    def process_args(self, args):
        if args.config:
            if os.path.exists(args.config):
                self._config.read(args.config)
            else:
                raise ValueError, 'File not exist: %s' % args.config
        _config_logging(args.log_level)

    def run(self, args):
        raise NotImplementedError


class MakePatternCommand(Command):

    def run(self, args):
        inputs = sys.stdin
        if args.file and os.path.exists(args.file):
            if os.path.exists(args.file):
                inputs = open(args.file, 'r')
            else:
                raise ValueError, 'File not exist: %s' % args.config
        self._config.freeze()
        pattern_maker = PatternMaker(self._config)
        counter = Counter('LoadStatus', 5000)
        counter.reset()
        for url in inputs:
            url = url.strip()
            try:
                pattern_maker.load(url)
            except Exception, e:
                self._logger.warn('%s, %s' % (str(e), url))
                continue
            counter.log('LOADING')
        counter.log('LOADED', True)
        for pattern_path in pattern_maker.process_and_dump():
            print(json.dumps(pattern_path, cls=PatternPathEncoder))


class MatchPatternCommand(Command):
    pass


_DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'incremental': True,


}


def _execute(command, argv=None):
    argv = argv or sys.argv
    parser = argparse.ArgumentParser()
    command.add_argument(parser)
    args = parser.parse_args(argv[1:])
    command.process_args(args)
    command.run(args)


def _default_config():
    from os_urlpattern import config
    path = os.path.dirname(config.__file__)
    cfg = config.Config()
    cfg.read(os.path.join(path, 'default_config.cfg'))
    return cfg


def make(argv=None):
    _execute(MakePatternCommand(_default_config()), argv)


def match(argv=None):
    _execute(MatchPatternCommand(_default_config()), argv)
