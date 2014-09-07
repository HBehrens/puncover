#!/usr/bin/env python
from __future__ import print_function
import os
from pprint import pprint
import click
import sys

from collector import Collector
from renderers import JSONRenderer, HTMLRenderer

@click.group()
def cli():
    pass

def build_collector(project_dir, pebble_sdk):
    c = Collector(pebble_sdk=pebble_sdk)
    # TODO: check if this is a pebble project dir
    c.parse_pebble_build_dir(os.path.join(project_dir, "build"))
    return c

@click.command()
@click.option('--project_dir', default=os.getcwd())
@click.option('--pebble_sdk')
@click.argument('output')
def json(project_dir, output, pebble_sdk=None):
    c = build_collector(project_dir, pebble_sdk)
    json_renderer = JSONRenderer(c)
    with open(output, "w") as f:
        f.writelines(json_renderer.render())

@click.command()
@click.option('--project_dir', default=os.getcwd())
@click.option('--pebble_sdk')
@click.argument('output')
def html(project_dir, output, pebble_sdk=None):
    print("using project dir: " + project_dir)
    c = build_collector(project_dir, pebble_sdk)
    html_renderer = HTMLRenderer(c)
    html_renderer.render_to_path(output)


cli.add_command(json)
cli.add_command(html)

if __name__ == "__main__":
    cli()