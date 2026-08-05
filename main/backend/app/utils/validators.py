"""
Input validation utilities.
"""


def validate_account_data(data):
    """
    Validate account creation/update data.

    Args:
        data: Dictionary with account information

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON data"

    allowed_fields = {
        'account_name',
        'api_key',
        'api_secret',
        'request_token',
    }
    unexpected = sorted(set(data) - allowed_fields)
    if unexpected:
        return False, f"Unsupported field: {unexpected[0]}"

    required_fields = {
        'account_name': (1, 100),
        'api_key': (10, 255),
        'api_secret': (10, 255),
        'request_token': (1, 2048),
    }
    for field, (minimum, maximum) in required_fields.items():
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return False, f"Missing required field: {field}"
        length = len(value.strip())
        if length < minimum or length > maximum:
            return False, (
                f"{field} must be between {minimum} and {maximum} characters"
            )

    return True, None


def validate_query_params(params, allowed_params):
    """
    Validate query parameters.

    Args:
        params: Dictionary of query parameters
        allowed_params: List of allowed parameter names

    Returns:
        Tuple of (is_valid, error_message)
    """
    for param in params:
        if param not in allowed_params:
            return False, f"Invalid query parameter: {param}"

    return True, None
