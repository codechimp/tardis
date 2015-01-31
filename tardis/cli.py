import click

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
    print('run ' + config_path)

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
