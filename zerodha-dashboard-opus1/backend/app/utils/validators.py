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
    required_fields = ['account_name', 'api_key', 'api_secret']

    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate account name length
    if len(data['account_name']) > 100:
        return False, "Account name too long (max 100 characters)"

    # Validate API key format (basic check)
    if len(data['api_key']) < 10:
        return False, "Invalid API key format"

    if len(data['api_secret']) < 10:
        return False, "Invalid API secret format"

    # Require either an existing access token or a request token that can be
    # exchanged for one by the backend.
    if not data.get('access_token') and not data.get('request_token'):
        return False, "Provide either an access token or a request token"

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
