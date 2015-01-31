import click
from docker import Client
from docker.utils import kwargs_from_env

@click.group()
def cli():
    pass

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


@cli.command()
@click.option('--config_path', help='path to tardis config file', default='.')
def run(config_path):
    """
    Runs your local DB image according to tardis configuration
    """
    
    docker_image = 'postgres:9.4.0'
    host_data_directory = '/tmp/postgres'
    docker_port = 5432

    POSTGRES_DATA_MOUNT = '/var/lib/postgresql/data'
    POSTGRES_USER = 'postgres'
    POSTGRES_PASSWORD= 'postgres'

    # c = Client(base_url='unix://var/run/docker.sock')
    # worakaround for boot2docker
    kwargs = kwargs_from_env()
    kwargs['tls'].assert_hostname = False
    client = Client(**kwargs)

    container = client.create_container(docker_image, environment = { 'POSTGRES_USER': POSTGRES_USER, 
                                                                      'POSTGRES_PASSWORD': POSTGRES_PASSWORD })

    container_id = container.get('Id')
    click.echo('created container for image {}. continer id is {}'.format(docker_image, container_id))

    response = client.start(container = container_id, 
                            binds = { 
                                        host_data_directory:
                                        {
                                            'bind': POSTGRES_DATA_MOUNT,
                                            'ro': False
                                        }
                                    },
                            port_bindings = { 5432: docker_port } )
    click.echo('container is started')



@cli.command()
@click.option('--checkpoint', help='name of the checkpoint representing the current DB state')
def save(checkpoint):
    """
    Sets a checkpoint for the current DB state
    """
    print('save ' + checkpoint)


@cli.command('travel-to')
@click.option('--checkpoint', help='name of the checkpoint representing the DB state you want to switch to')
def travel_to(checkpoint):
    """
    Sets DB state back to state saved in the target checkpoint 
    """
    print('travel-to ' + checkpoint)


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
    print('list')


def main():
    cli()


if __name__ == '__main__':
    main()
