import click
import questionary

import agent
from agent.utils import *

console = Console()
# avoid the tokenizers parallelism issue
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


class DefaultCommandGroup(click.Group):
    """allow a default command for a group"""

    def command(self, *args, **kwargs):
        """
        command: the command decorator for the group.
        """
        default_command = kwargs.pop('default_command', False)
        if default_command and not args:
            kwargs['name'] = kwargs.get('name', 'termax/t')
        decorator = super(
            DefaultCommandGroup, self).command(*args, **kwargs)

        if default_command:
            def new_decorator(f):
                cmd = decorator(f)
                self.default_command = cmd.name
                return cmd

            return new_decorator

        return decorator

    def resolve_command(self, ctx, args):
        """
        resolve_command: resolve the command.
        """
        try:
            # test if the command parses
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)
        except click.UsageError:
            # command did not parse, assume it is the default command
            args.insert(0, self.default_command)
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)


def build_config(general: bool = False):
    """
    build_config: build the configuration for Termax.
    Args:
        general: a boolean indicating whether to build the general configuration only.
    :return:
    """
    configuration = Config()
    platform = LLM_TYPE_OPENAI
    api_key = questionary.text("What is your OpenAI API key?").ask()

    general_config = {
        'platform': platform,
        'api_key': api_key,
    }

    configuration.write_section(CONFIG_SEC_GENERAL, general_config)

    if not general:
        platform_config = {
            "model": 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 2000,
            'top_p': 1.0,
            'top_k': 32,
            'stop_sequences': 'None',
            'candidate_count': 1
        }

        configuration.write_section(platform, platform_config)


@click.group(cls=DefaultCommandGroup)
@click.version_option(version=agent.__version__)
def cli():
    """
    MLE-Agent: The CLI tool to build machine learning projects.
    """
    pass


@cli.command()
@click.option('--general', '-g', is_flag=True, help="Set up the general configuration for MLE Agent.")
def config(general):
    """
    Set up the global configuration for Termax.
    """
    build_config(general)


@cli.command(default_command=True)
@click.argument('text', nargs=-1)
def ask(text):
    """
    ASK the agent a question to build an ML project.
    """

    console.log(text)


@cli.command()
def go():
    """
    go: start the working your ML project.
    """
    configuration = Config()
    console.log("Welcome to MLE-Agent! :sunglasses:")
    console.line()

    if configuration.read().get('project') is None:
        console.log("You have not set up a project yet.")
        console.log("Please create a new project first using 'mle new <project_name>' command.")
        return

    console.log("> Current project:", configuration.read()['project']['path'])
    if configuration.read()['project'].get('lang') is None:
        lang = questionary.text("What is your major language for this project?").ask()
        configuration.write_section(CONFIG_SEC_PROJECT, {'lang': lang})


@cli.command()
@click.argument('name')
def new(name: str):
    """
    new: create a new machine learning project.
    """
    configuration = Config()
    project_initial_config = {
        'name': name,
        'description': 'A new machine learning project.',  # default description
        'llm': configuration.read()['general']['platform'],
        'step': 0
    }

    project_path = create_directory(name)
    update_project_state(project_path, project_initial_config)
    configuration.write_section(CONFIG_SEC_PROJECT, {
        'path': project_path
    })


@cli.command()
@click.argument('path', nargs=-1, type=click.Path(exists=True))
def set_project(path):
    """
    project: set the current project.
    :return:
    """
    configuration = Config()
    project_path = " ".join(path)
    project_config_path = os.path.join(project_path, CONFIG_PROJECT_FILE)
    if not os.path.exists(project_config_path):
        console.log("The project path is not valid. Please check if `project.yml` exists and try again.")
        return

    configuration.write_section(CONFIG_SEC_PROJECT, {
        'path': project_path
    })

    console.log(f"> Project set to {project_path}")