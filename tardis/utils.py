import click
"""
CREDITS
Taken from https://github.com/zalando/aws-minion/blob/master/aws_minion/console.py
"""

def ok(msg=' OK', **kwargs):
    click.secho(msg, fg='green', bold=True, **kwargs)


def warn(msg, **kwargs):
    click.secho(' {}'.format(msg), fg='yellow', bold=True, **kwargs)


def error(msg, **kwargs):
    click.secho(' {}'.format(msg), fg='red', bold=True, **kwargs)