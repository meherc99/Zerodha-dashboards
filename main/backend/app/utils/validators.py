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

    # account_name is always required
    account_name = data.get('account_name')
    if not isinstance(account_name, str) or not account_name.strip():
        return False, "Missing required field: account_name"
    if not (1 <= len(account_name.strip()) <= 100):
        return False, "account_name must be between 1 and 100 characters"

    # Kite Connect fields are optional at creation time but validated when present
    optional_length_fields = {
        'api_key': (10, 255),
        'api_secret': (10, 255),
        'request_token': (1, 2048),
    }
    for field, (minimum, maximum) in optional_length_fields.items():
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return False, f"Invalid value for field: {field}"
        length = len(value.strip())
        if length < minimum or length > maximum:
            return False, (
                f"{field} must be between {minimum} and {maximum} characters"
            )

    # If any Kite credential is supplied, all three must be supplied together
    kite_fields = {f for f in ('api_key', 'api_secret', 'request_token') if data.get(f)}
    if kite_fields and kite_fields != {'api_key', 'api_secret', 'request_token'}:
        missing = {'api_key', 'api_secret', 'request_token'} - kite_fields
        return False, f"Must provide all Kite fields together: {', '.join(sorted(missing))}"

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
