
# This file's functionality has been integrated into lambda_function.py
# for a unified Alexa skill implementation

# For testing purposes, you can import the main functions from lambda_function:
# from lambda_function import generate_gpt_response, client_gpt, system_instructions

import warnings
warnings.warn(
    "model_gpt.py functionality has been integrated into lambda_function.py. "
    "Use lambda_function.py for the main Alexa skill implementation.",
    DeprecationWarning,
    stacklevel=2
)