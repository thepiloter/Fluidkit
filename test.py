from fluidkit import integrate
from tests.sample.app import app

integrate(app, enable_fullstack=True)
