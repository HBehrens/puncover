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

def build_collector(pebble_sdk, project_dir=None, elf_file=None, su_dir=None):
    c = Collector(pebble_sdk=pebble_sdk)
    if project_dir:
        # TODO: check if this is a pebble project dir
        c.parse_pebble_project_dir(project_dir)
    if elf_file:
        c.parse(elf_file, su_dir)
    return c

@click.command()
@click.option('--project_dir', default=os.getcwd())
@click.option('--pebble_sdk')
@click.argument('output')
def gutter(project_dir, output, pebble_sdk=None):
    c = build_collector(pebble_sdk, project_dir)
    json_renderer = JSONRenderer(c)
    with open(output, "w") as f:
        f.writelines(json_renderer.render(os.path.dirname(os.path.abspath(output))))

@click.command()
@click.option('--project_dir', default=os.getcwd())
@click.option('--pebble_sdk')
@click.argument('output')
def html(project_dir, output, pebble_sdk=None):
    print("using project dir: " + project_dir)
    c = build_collector(pebble_sdk, project_dir)
    print("enhancing assembly")
    c.enhance_assembly()
    print("rendering HTML")
    html_renderer = HTMLRenderer(c)
    html_renderer.render_to_path(output)


@click.command()
@click.option('--project_dir', default=None)
@click.option('--elf', default=None)
@click.option('--pebble_sdk')
@click.argument('output')
def render(output, project_dir=None, elf=None, pebble_sdk=None):
    print("will collect")
    c = build_collector(pebble_sdk, project_dir, elf, os.path.dirname(elf) if elf else None)
    print("will enhance")
    c.enhance_assembly()
    print("will render")
    html_renderer = HTMLRenderer(c)
    html_renderer.render_to_path(output)


cli.add_command(gutter)
cli.add_command(html)
cli.add_command(render)

if __name__ == "__main__":
    cli()