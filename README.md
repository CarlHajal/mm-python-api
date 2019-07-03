# mm-python-api
MachineMotion Python API

## Version: 1.6.5

Date:  June 4 2019

### Bug Fixes:
- Fix Line Number mismatch with the help of the 'resend' message
- Fix application hang on termination 

### Improvements:
- Added the indexer and conveyot gain in the constants definitions.
-  Added more examples for each sensor port for the different control devices functions.
- Auto reconnect on connection loss
- Instead of starting a new thread each 0.1 seconds, we now start one thread at the beginning and keep it alive forever to receive messages from the server

