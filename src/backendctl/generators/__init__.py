"""Generator registry."""

from backendctl.core.config import Framework, ProjectConfig
from backendctl.generators.base import BaseGenerator


def get_generator(config: ProjectConfig) -> BaseGenerator:
    from backendctl.generators.django_gen import DjangoGenerator
    from backendctl.generators.fastapi_gen import FastAPIGenerator
    from backendctl.generators.flask_gen import FlaskGenerator

    mapping = {
        Framework.FASTAPI: FastAPIGenerator,
        Framework.FLASK: FlaskGenerator,
        Framework.DJANGO: DjangoGenerator,
    }
    return mapping[config.framework](config)
