from .anthropic import *
from .deepseek import *
from .mistral import *
from .ollama import *
from .openai import *
from .gemini import *
from .vllm import *

from mle.utils import get_config


MODEL_OLLAMA = 'Ollama'
MODEL_OPENAI = 'OpenAI'
MODEL_CLAUDE = 'Claude'
MODEL_MISTRAL = 'MistralAI'
MODEL_DEEPSEEK = 'DeepSeek'
MODEL_GEMINI = 'Gemini'
MODEL_VLLM = 'vLLM'


class ObservableModel:
    """
    A class that wraps a model to make it trackable by the metric platform (e.g., Langfuse).
    """

    try:
        from mle.utils import get_langfuse_observer
        _observe = get_langfuse_observer()
    except Exception as e:
        # If importing fails, set _observe to a lambda function that does nothing.
        _observe = lambda fn: fn

    def __init__(self, model: Model):
        """
        Initialize the ObservableModel.
        Args:
            model: The model to be wrapped and made observable.
        """
        self.model = model

    @_observe
    def query(self, *args, **kwargs):
        return self.model.query(*args, **kwargs)

    @_observe
    def stream(self, *args, **kwargs):
        return self.model.query(*args, **kwargs)


def load_model(project_dir: str, model_name: str=None, observable=True):
    """
    load_model: load the model based on the configuration.
    Args:
        project_dir (str): The project directory.
        model_name (str): The model name.
        observable (boolean): Whether the model should be tracked.
    """
    config = get_config(project_dir)
    model = None

    if config['platform'] == MODEL_OLLAMA:
        # For Ollama, use base_url as host_url if available
        host_url = config.get('base_url', None)
        model = OllamaModel(model=model_name, host_url=host_url)
    if config['platform'] == MODEL_OPENAI:
        model = OpenAIModel(api_key=config['api_key'], model=model_name)
    if config['platform'] == MODEL_CLAUDE:
        model = ClaudeModel(api_key=config['api_key'], model=model_name)
    if config['platform'] == MODEL_MISTRAL:
        model = MistralModel(api_key=config['api_key'], model=model_name)
    if config['platform'] == MODEL_DEEPSEEK:
        model = DeepSeekModel(api_key=config['api_key'], model=model_name)
    if config['platform'] == MODEL_GEMINI:
        model = GeminiModel(api_key=config['api_key'], model=model_name)
    if config['platform'] == MODEL_VLLM:
        model = vLLMModel(base_url=config.get('base_url', 'http://localhost:8000/v1'), model=model_name)

    if observable:
        return ObservableModel(model)
    return model
