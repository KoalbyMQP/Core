# Published on any container instance state change
string STATE_STARTING=starting
string STATE_RUNNING=running
string STATE_STOPPING=stopping
string STATE_STOPPED=stopped
string STATE_CRASHED=crashed

string instance_id
string app
string version
string image
string state             # one of the STATE_* constants above
string error             # empty if no error
builtin_interfaces/Time stamp
