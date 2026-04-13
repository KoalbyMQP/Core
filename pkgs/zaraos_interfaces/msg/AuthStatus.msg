# Published when pairing completes, expires, or fails
string STATUS_PAIRED=paired
string STATUS_EXPIRED=expired
string STATUS_FAILED=failed

string status            # one of the STATUS_* constants above
string label             # client label on success, error message on failure
builtin_interfaces/Time stamp
