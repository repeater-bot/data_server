from typing import Callable, TypeVar

POST_INIT_FUNC = Callable[[], None]

T = TypeVar("T", bound = POST_INIT_FUNC)

post_init: list[POST_INIT_FUNC] = []

def register_post_init(func: T) -> T:
    post_init.append(func)
    return func

def run_post_init():
    for func in post_init:
        func()