import importlib
from cacl.settings import settings


_cached_user_model = None


def get_user_model():
    """
    Import and return the User model class specified in CACL_USER_MODEL.
    Example: "app.models.users.User"
    """
    global _cached_user_model

    if _cached_user_model:
        return _cached_user_model

    model_path = settings.CACL_USER_MODEL
    if not model_path:
        raise RuntimeError(
            "CACL_USER_MODEL is not set. "
            "Specify full dotted path in .env, e.g.: CACL_USER_MODEL=app.models.users.User"
        )

    try:
        module_path, class_name = model_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise RuntimeError(
            f"Cannot import User model '{model_path}': {e}. "
            f"Check CACL_USER_MODEL env var (format: 'module.path.ClassName')."
        )

    _cached_user_model = model_class
    return model_class
