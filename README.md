# PING PARTY

This is an informal network tester. Each party sends UDP broadcast packets
and everyone listens for them. They're sent periodically with a certain
minimum frequency and if anyone doesn't receive one within that frequency,
it gets reported in the log as a warning.
