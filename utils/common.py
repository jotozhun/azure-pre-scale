from datetime import datetime

def get_datetime_to_ISO_format(dt: datetime):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))