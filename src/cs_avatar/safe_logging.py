import logging


def configure_safe_logging() -> None:
    # OpenID library diagnostics can contain signed callback parameters.
    logging.getLogger("openid").setLevel(logging.CRITICAL + 1)
