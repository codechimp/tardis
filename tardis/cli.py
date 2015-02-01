import click
from docker import Client
from docker.utils import kwargs_from_env
import json
import git
from tardis.utils import ok, error, warn
import yaml
import os
import collections


POSTGRES_DATA_MOUNT = '/var/lib/postgresql/data'
POSTGRES_USER = 'postgres'
POSTGRES_PASSWORD= 'postgres'

session_file = '.tardis.session'

docker_image = 'postgres:9.4.0'
host_data_directory = '/tmp/postgres'
docker_port = 5432

CONFIG_FILE = './tardis2.yml'


@click.group()
def cli():
    pass


def load_configuration():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'rb') as fd:
            return yaml.safe_load(fd)
    else:
        return dict()


def dump_to_session_data(data):
    with open(session_file, 'w') as f:
        json.dump(data, f)
 

def load_session_data():
  with open(session_file, 'r') as f:
        return json.load(f)


def create_docker_client():
    return  Client(base_url='unix://var/run/docker.sock')


@cli.command()
def configure():
    """
    Configure your local Postgres Docker image

    TODO
    - postgres version
    -port
    -image pull
    -data folder location
    -config name
    """

    config = load_configuration()
    travel_plan_name = click.prompt('travel plan name')

    if not config:
        config = dict()

    if not travel_plan_name in config:
        config[travel_plan_name] = dict()

    config[travel_plan_name] = dict()

    image = click.prompt('docker image', default='postgres')
    tag = click.prompt('docker image tag', default='latest')

    config[travel_plan_name]['image'] = image
    config[travel_plan_name]['tag'] = tag
    config[travel_plan_name]['db_user'] = click.prompt('DB user', default=POSTGRES_USER)
    config[travel_plan_name]['db_password'] = click.prompt('DB password', default=POSTGRES_PASSWORD)
    config[travel_plan_name]['db_port'] = click.prompt('DB port', default=5432)
    config[travel_plan_name]['data_share'] = click.prompt('data share between host and Docker container')

    click.echo('pulling  "{}:{}"...'.format(image,tag))
    docker_client = create_docker_client()
    docker_client.pull(repository=image, tag=tag)
    ok('pulled "{}:{}"'.format(image,tag))

    click.echo('saving travel plan "{}" to "{}"...'.format(travel_plan_name, CONFIG_FILE))

    with open(CONFIG_FILE, 'w') as fd:
        yaml.dump(config, fd, default_flow_style=False)
    
    ok('saved travel plan "{}" to "{}"'.format(travel_plan_name, CONFIG_FILE))


# TODO error handling
@cli.command()
@click.option('--config_path', help='path to tardis config file', default='.')
def run(config_path, recent_checkpoint = None):
    """
    Runs your local DB image according to tardis configuration
    """
    
    client = create_docker_client();

    container = client.create_container(docker_image, environment = { 'POSTGRES_USER': POSTGRES_USER, 
                                                                      'POSTGRES_PASSWORD': POSTGRES_PASSWORD })
    container_id = container.get('Id')

    dump_to_session_data({ 'container_id' :     container_id, 
                           'recent_checkpoint': recent_checkpoint })

    response = client.start(container = container_id, 
                            binds = { 
                                        host_data_directory:
                                        {
                                            'bind': POSTGRES_DATA_MOUNT,
                                            'ro': False
                                        }
                                    },
                            port_bindings = { 5432: docker_port } )

    ok('started container "{}"'.format(container_id))


def is_git_directory(dir):
    return git.repo.fun.is_git_dir(dir)


def is_dirty():
    """
    Checks if the current reposity has untracked or changed files
    """
    repo = git.repo.base.Repo(path=host_data_directory)
    return repo.is_dirty(untracked_files=True)


def init_git_repo_if_not_exists():
    if is_git_directory(host_data_directory):
        click.echo('"{}" is already a GIT repo --> utilizing this repo'.format(host_data_directory))
    else:
        git.repo.base.Repo.init(path=host_data_directory)
        ok('initialized GIT repo in "{}"'.format(host_data_directory))


@cli.command()
@click.option('--checkpoint', help='name of the checkpoint representing the current DB state')
def save(checkpoint):
    """
    Sets a checkpoint for the current DB state
    """

    init_git_repo_if_not_exists()

    if is_dirty():
        docker_client = create_docker_client()
        session_data = load_session_data()
        container_id = session_data['container_id']

        try:
            docker_client.pause(container_id)
            ok('paused container "{}"'.format(container_id))
            click.echo('repo has changed...')
            git_cmd = git.Git(host_data_directory)
            git_cmd.add('--all', host_data_directory)
            git_cmd.commit(message=checkpoint)
            git_cmd.tag('--annotate', checkpoint, message=checkpoint)

            dump_to_session_data({ 'container_id':      container_id, 
                                   'recent_checkpoint': checkpoint })
        except Exception as e:
            error(e)
        finally:
            docker_client.unpause(container_id)
            ok('unpaused container "{}"'.format(container_id))
    else:
        warn('repo has not changed... -> no checkpoint was created')


@cli.command('travel-to')
@click.option('--checkpoint', help='name of the checkpoint representing the DB state you want to switch to')
@click.pass_context
def travel_to(ctx, checkpoint):
    """
    Sets DB state back to state saved in the target checkpoint 
    """
    docker_client = create_docker_client();
    session_data = load_session_data()
    container_id = session_data['container_id']

    docker_client.stop(container_id)
    ok('stopped container "{}"'.format(container_id))

    git_cmd = git.Git(host_data_directory)
    git_cmd.checkout('--force','tags/{}'.format(checkpoint))
    ok('travelled back to "{}"'.format(checkpoint))
    
    # FIXME we need to reuse the same config path as we did in 'travis run'
    ctx.invoke(run, recent_checkpoint=checkpoint)




@cli.command('travel-back')
@click.pass_context
def travel_back(ctx):
    """
    Sets DB state back to the recent checkpoint 
    """
    session_data = load_session_data()
    ctx.invoke(travel_to, checkpoint=session_data['recent_checkpoint'])


@cli.command()
def list():
    """
    Lists all checkpoints
    """
    # TODO mark current checkpoint
    repo = git.repo.base.Repo(path=host_data_directory)
    [print(tag) for tag in repo.tags]


def main():
    cli()


if __name__ == '__main__':
    main()
