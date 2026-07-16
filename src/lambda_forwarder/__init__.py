"""AWS Lambda forwarder for GuardDuty findings to a Tines webhook."""

from __future__ import annotations

from .config import LambdaConfig
from .handler import lambda_handler

__all__ = ["LambdaConfig", "lambda_handler"]
