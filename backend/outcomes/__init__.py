"""Outcome method dispatch. Methods never apply scenario rules."""
from .historical import generate_historical


def generate_outcomes(method, applicants, *, method_data=None):
    if method == 'historical':
        return generate_historical(applicants, method_data)
    if method in ('llm', 'matrix', 'random_method'):
        raise NotImplementedError(f'Outcome method {method!r} is not implemented.')
    raise ValueError(f'Unknown outcome method: {method!r}')
