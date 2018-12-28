"""
Usage:
  squabble [options] [PATHS...]
  squabble (-h | --help)

Arguments:
  PATHS                Files or directories to lint. If given a directory, will
                       recursively traverse the path and lint all files ending
                       in `.sql`

Options:
  -c --config=PATH     Path to configuration file
  -h --help            Show this screen
  -p --preset=PRESET   Start with a base preset rule configuration
  -P --list-presets    List the available preset configurations
  -r --show-rule=RULE  Show detailed information about RULE
  -R --list-rules      Print out information about all available rules
  -V --verbose         Turn on debug level logging
  -v --version         Show version information
"""

import glob
import json
import os.path
import sys
from pkg_resources import get_distribution

import colorama
import docopt
from colorama import Style

import squabble
from squabble import config, lint, logger, rule, reporter


def main():
    version = get_distribution('squabble').version
    args = docopt.docopt(__doc__, version=version)

    if args['--verbose']:
        logger.setLevel('DEBUG')

    paths = args['PATHS']
    preset = args['--preset']

    if args['--list-presets']:
        return list_presets()

    config_file = args['--config'] or config.discover_config_location()
    if config_file and not os.path.exists(config_file):
        sys.exit('%s: no such file or directory' % config_file)

    base_config = config.load_config(config_file, preset)

    # Load all of the rule classes into memory
    rule.load_rules(plugin_paths=base_config.plugins)

    if args['--list-rules']:
        return list_rules()
    elif args['--show-rule']:
        return show_rule(name=args['--show-rule'])

    files = collect_files(paths)

    issues = []
    for file_name in files:
        issues += lint_file(base_config, file_name)

    reporter.report(base_config.reporter, issues)

    # Make sure we have an error status if something went wrong.
    if issues:
        sys.exit(1)


def lint_file(base_config, file_name):
    file_config = config.apply_file_config(base_config, file_name)
    return lint.check_file(file_config, file_name)


def collect_files(paths):
    """
    Given a list of files or directories, return all named files as well as
    any files ending in `.sql` in the directories.
    """
    files = []

    for path in map(os.path.expanduser, paths):
        if not os.path.exists(path):
            sys.exit('%s: no such file or directory' % path)

        elif os.path.isdir(path):
            sql = os.path.join(path, '**/*.sql')
            files.extend(glob.iglob(sql, recursive=True))

        else:
            files.append(path)

    return files


def show_rule(name):
    """Print information about rule named ``name``."""
    color = {
        'bold': Style.BRIGHT,
        'reset': Style.RESET_ALL,
    }

    try:
        meta = rule.Registry.get_meta(name)
    except squabble.UnknownRuleException:
        sys.exit('{bold}Unknown rule:{reset} {name}'.format(**{
            'name': name,
            **color
        }))

    print('{bold}{name}{reset} - {description}\n{help}'.format(**{
        **meta,
        **color
    }))


def list_rules():
    """Print out all registered rules and brief description of what they do."""
    color = {
        'bold': Style.BRIGHT,
        'reset': Style.RESET_ALL,
    }

    all_rules = sorted(rule.Registry.all(), key=lambda r: r['name'])

    for meta in all_rules:
        print('{bold}{name: <32}{reset} {description}'.format(**{
            **color,
            **meta
        }))


def list_presets():
    """Print out all the preset configurations."""
    for name, preset in config.PRESETS.items():
        print('{bold}{name}{reset} - {description}'.format(
            name=name,
            description=preset.get('description', ''),
            bold=Style.BRIGHT,
            reset=Style.RESET_ALL
        ))

        # npm here i come
        left_pad = '    '
        cfg = json.dumps(preset['config'], indent=4)\
                  .replace('\n', '\n' + left_pad)
        print(left_pad + cfg)


if __name__ == '__main__':
    colorama.init()
    main()
