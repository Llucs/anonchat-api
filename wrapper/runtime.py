from typing    import Callable, Any, Optional, Type
from .logger   import Log
from functools import wraps


class Run:

    @staticmethod
    def Error(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                Run.handle_error(e)
                return None
        return wrapper

    @staticmethod
    def handle_error(exception: Exception) -> None:
        Log.Error(f"Error occurred: {exception}")
        exit(1)

class Utils:

    @staticmethod
    def between(
        main_text: Optional[str],
        value_1: Optional[str],
        value_2: Optional[str],
        ) -> Type[str]:
        return main_text.split(value_1)[1].split(value_2)[0]
