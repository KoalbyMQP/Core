# General system-level error/warning for UI display
string SEVERITY_ERROR=error
string SEVERITY_WARNING=warning
string SEVERITY_INFO=info

string source            # "auth", "instance", "wifi", "system"
string severity          # one of the SEVERITY_* constants above
string message
builtin_interfaces/Time stamp
