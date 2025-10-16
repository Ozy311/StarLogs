"""
StarLogs Version Information
"""

__version__ = "0.8.2"
__author__ = "Ozy311"
__organization__ = "CUBE Org"
__tagline__ = "FOR THE CUBE!"
__description__ = "Star Citizen Log Parser and Event Tracker"
__license__ = "MIT"

VERSION_INFO = {
    'version': __version__,
    'author': __author__,
    'organization': __organization__,
    'tagline': __tagline__,
    'description': __description__,
    'license': __license__
}

def get_version_string():
    """Get formatted version string."""
    return f"StarLogs v{__version__} by {__author__}"

def get_about_info():
    """Get complete about information."""
    return {
        **VERSION_INFO,
        'features': [
            'Real-time Star Citizen log monitoring',
            'PvE and PvP kill tracking (vehicle & FPS combat)',
            'FPS combat tracking with on-foot kills and deaths',
            'Player death detection',
            'Actor Stall and disconnect logging',
            'Ship/Location extraction from kill events',
            'Attack direction analysis',
            'System information extraction (CPU, GPU, RAM)',
            'Live web dashboard with SSE streaming',
            'Historical log browser and analysis',
            'HTML export for offline viewing',
            'Event filtering and search',
            'Multi-version game installation support',
            'TUI console with interactive options'
        ]
    }
