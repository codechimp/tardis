import click
from docker import Client
from docker.utils import kwargs_from_env
import json
import git
from tardis.utils import ok, error, warn


POSTGRES_DATA_MOUNT = '/var/lib/postgresql/data'
POSTGRES_USER = 'postgres'
POSTGRES_PASSWORD= 'postgres'

session_file = '.tardis.session'

docker_image = 'postgres:9.4.0'
host_data_directory = '/tmp/postgres'
docker_port = 5432


@click.group()
def cli():
    pass


def dump_to_session_data(data):
    with open(session_file, 'w') as f:
        json.dump(data, f)

 
def load_session_data():
  with open(session_file, 'r') as f:
        return json.load(f)


def create_docker_client():
    # c = Client(base_url='unix://var/run/docker.sock')
    # worakaround for boot2docker
    #kwargs = kwargs_from_env()
    #kwargs['tls'].assert_hostname = False
    #return Client(**kwargs)
    return  Client(base_url='unix://var/run/docker.sock')

@cli.command()
@click.option('--docker_image', help='path to pull postgres docker image')
def configure(docker_image):
    """
    Configure your local Postgres Docker image
    
    TODO
	- postgres version
	-port
	-image pull
	-data folder location
	-config name
    """
    print('configure')


# TODO error handling
@cli.command()
@click.option('--config_path', help='path to tardis config file', default='.')
def run(config_path):
    """
    Runs your local DB image according to tardis configuration
    """
    
    client = create_docker_client();

    container = client.create_container(docker_image, environment = { 'POSTGRES_USER': POSTGRES_USER, 
                                                                      'POSTGRES_PASSWORD': POSTGRES_PASSWORD })
    container_id = container.get('Id')
    dump_to_session_data({ 'container_id' : container_id })

    response = client.start(container = container_id, 
                            binds = { 
                                        host_data_directory:
                                        {
                                            'bind': POSTGRES_DATA_MOUNT,
                                            'ro': False
                                        }
                                    },
                            port_bindings = { 5432: docker_port } )

    ok('started container {}'.format(container_id))


def is_dirty():
    """
    There is a is_dirty function in git-python but it seems that it is does not work properly
    """
    repo = git.repo.base.Repo(path=host_data_directory)
    return repo.is_dirty(untracked_files=True)


@cli.command()
@click.option('--checkpoint', help='name of the checkpoint representing the current DB state')
def save(checkpoint):
    """
    Sets a checkpoint for the current DB state
    """
    session_data = load_session_data()
    docker_client = create_docker_client();
    container_id = session_data['container_id']
    
    git_cmd = git.Git(host_data_directory)
    
    if is_dirty():      
        try:
            docker_client.pause(container_id)
            ok('paused container {}'.format(container_id))
            click.echo('repo has changed...')
            git_cmd.add('--all', host_data_directory)
            git_cmd.commit(message=checkpoint)
            git_cmd.tag('--annotate', checkpoint, message=checkpoint)
        except Exception as e:
            error(e)
        finally:
            docker_client.unpause(container_id)
            ok("unpaused container {}".format(container_id))
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
    ok('stopped container {}'.format(container_id))

    git_cmd = git.Git(host_data_directory)
    git_cmd.checkout('--force','tags/{}'.format(checkpoint))
    ok('travelled back to {}'.format(checkpoint))
    
    # FIXME we need to reuse the same config path as we did in 'travis run'
    ctx.invoke(run)




@cli.command('travel-back')
def travel_back():
    """
    Sets DB state back to the recent checkpoint 
    """
    print('travel-back ')


@cli.command()
def list():
    """
    Lists all checkpoints
    """
    # TODO mark current checkpoint
    repo = git.repo.base.Repo(path=host_data_directory)
    [print(tag) for tag in repo.tags]




def main():
    #pid = str(os.getpid())
    # session_file = '.tardis.session.{}.pid'.format(pid)
    
    #with open(session_file, 'w') as f:
    #    f.write('start')
    #try:
    cli()
    #except e:
    #    print(e)
    #    os.unlink(session_file)



if __name__ == '__main__':
    main()
