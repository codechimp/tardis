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
CONFIG_FILE = './tardis2.yml'

SESSION_FILE = '.{}.tardis.session'


@click.group()
def cli():
    pass


def load_configuration():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'rb') as fd:
            return yaml.safe_load(fd)
    else:
        return dict()


def dump_to_session_data(travel_plan, data):
    with open(SESSION_FILE.format(travel_plan), 'w') as f:
        json.dump(data, f)
 

def load_session_data(travel_plan):
  with open(SESSION_FILE.format(travel_plan), 'r') as f:
        return json.load(f)


def create_docker_client():
    return  Client(base_url='unix://var/run/docker.sock')


@cli.command()
def configure():
    """
    Configure your local Postgres Docker image
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
@click.option('--travel-plan', help='name of the travel plan configuration')
@click.option('--config_path', help='path to tardis config file', default='.')
def run(travel_plan, config_path, recent_checkpoint = None):
    """
    Runs your local DB image according to tardis configuration
    """

    config = load_configuration()
    travel_plan_config = config[travel_plan]
    docker_image = travel_plan_config['image'] + ':' + travel_plan_config['tag']

    client = create_docker_client();

    container = client.create_container(docker_image, environment = { 'POSTGRES_USER':     travel_plan_config['db_user'], 
                                                                      'POSTGRES_PASSWORD': travel_plan_config['db_password'] })
    container_id = container.get('Id')

    dump_to_session_data(travel_plan,
                          { 'container_id' :     container_id, 
                            'recent_checkpoint': recent_checkpoint })

    response = client.start(container = container_id, 
                            binds = { 
                                        travel_plan_config['data_share']:
                                        {
                                            'bind': POSTGRES_DATA_MOUNT,
                                            'ro': False
                                        }
                                    },
                            port_bindings = { 5432: travel_plan_config['db_port'] } )

    ok('started container "{}"'.format(container_id))


def is_git_directory(dir):
    return git.repo.fun.is_git_dir(dir)


def is_dirty(data_share):
    """
    Checks if the current reposity has untracked or changed files
    """
    repo = git.repo.base.Repo(path=data_share)
    return repo.is_dirty(untracked_files=True)


def init_git_repo_if_not_exists(path):
    if is_git_directory(path):
        click.echo('"{}" is already a GIT repo --> utilizing this repo'.format(path))
    else:
        git.repo.base.Repo.init(path=path)
        ok('initialized GIT repo in "{}"'.format(path))


@cli.command()
@click.option('--travel-plan', help='name of the travel plan configuration')
@click.option('--checkpoint', help='name of the checkpoint representing the current DB state')
def save(travel_plan, checkpoint):
    """
    Sets a checkpoint for the current DB state
    """

    config = load_configuration()
    data_share = config[travel_plan]['data_share']


    init_git_repo_if_not_exists(data_share)

    if is_dirty(data_share):
        docker_client = create_docker_client()
        session_data = load_session_data(travel_plan)
        container_id = session_data['container_id']

        try:
            docker_client.pause(container_id)
            ok('paused container "{}"'.format(container_id))
            click.echo('repo has changed...')
            git_cmd = git.Git(data_share)
            git_cmd.add('--all', data_share)
            git_cmd.commit(message=checkpoint)
            git_cmd.tag('--annotate', checkpoint, message=checkpoint)

            dump_to_session_data(travel_plan,
                                 { 'container_id':      container_id, 
                                   'recent_checkpoint': checkpoint })
        except Exception as e:
            error(e)
        finally:
            docker_client.unpause(container_id)
            ok('unpaused container "{}"'.format(container_id))
    else:
        warn('repo has not changed... -> no checkpoint was created')


@cli.command('travel-to')
@click.option('--travel-plan', help='name of the travel plan configuration')
@click.option('--checkpoint', help='name of the checkpoint representing the DB state you want to switch to')
@click.pass_context
def travel_to(ctx, travel_plan, checkpoint):
    """
    Sets DB state back to state saved in the target checkpoint 
    """
    config = load_configuration()
    data_share = config[travel_plan]['data_share']

    ctx.invoke(stop, travel_plan=travel_plan)

    git_cmd = git.Git(data_share)
    git_cmd.checkout('--force','tags/{}'.format(checkpoint))
    ok('travelled back to "{}"'.format(checkpoint))
    
    # FIXME we need to reuse the same config path as we did in 'travis run'
    ctx.invoke(run, travel_plan=travel_plan, recent_checkpoint=checkpoint)




@cli.command('travel-back')
@click.option('--travel-plan', help='name of the travel plan configuration')
@click.pass_context
def travel_back(ctx, travel_plan):
    """
    Sets DB state back to the recent checkpoint 
    """
    session_data = load_session_data(travel_plan)
    ctx.invoke(travel_to, travel_plan=travel_plan, checkpoint=session_data['recent_checkpoint'])


@cli.command()
@click.option('--travel-plan', help='name of the travel plan configuration')
def list(travel_plan):
    """
    Lists all checkpoints
    """
    config = load_configuration()
    data_share = config[travel_plan]['data_share']

    # TODO mark current checkpoint
    repo = git.repo.base.Repo(path=data_share)
    [print(tag) for tag in repo.tags]

@cli.command()
@click.option('--travel-plan', help='name of the travel plan configuration')
def stop(travel_plan):
    session_data = load_session_data(travel_plan)
    docker_client = create_docker_client()
    container_id = session_data['container_id']
    docker_client.stop(container_id)
    ok('stopped container "{}"'.format(container_id))



def main():
    cli()


if __name__ == '__main__':
    main()
